"""
Celery 任務定義：一鍵同步（匯出 .txt + 執行 ingest script）。

重試策略：3 次，指數退避（10s / 20s / 40s）
逾時：300 秒（soft_time_limit）
並發：由 docker-compose command --concurrency=2 控制
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from celery import Celery

logger = structlog.get_logger()

REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# ── Tunable constants ────────────────────────────────────────────────────────
# Celery 層
TASK_SOFT_TIME_LIMIT_SEC = 300        # Celery soft time limit
TASK_MAX_RETRIES = 3                  # 重試次數上限
TASK_RETRY_DELAY_SEC = 10             # 第一次重試延遲（後續指數退避）
RETRY_BACKOFF_BASE_SEC = TASK_RETRY_DELAY_SEC  # 手動 countdown 基數，刻意與 default_retry_delay 保持一致

# Ingest subprocess 層
# 比 task_soft_time_limit 早 20 秒，留餘裕讓我們自行 kill 並寫 sync_log
INGEST_SUBPROCESS_TIMEOUT_SEC = 280
INGEST_KILL_GRACE_SEC = 5             # SIGKILL 後等待子程序回收的寬限

# 寫 sync_log.stderr 的長度上限（避免 DB 欄位爆量）
STDERR_MAX_CHARS = 1000


def _build_embedding_args_from_env(agent_provider: str, agent_model: str) -> list[str]:
    """組成 ingest_kb.py 的 embedding CLI args（會讀環境變數，名字明示副作用）。

    - openai：不附 --base-url / --api-key，由 OpenAI SDK 自行讀 OPENAI_API_KEY env
    - local ：讀 LOCAL_EMBEDDING_BASE_URL（**必填**）與 LOCAL_EMBEDDING_API_KEY（預設 'any'）

    Raises:
        RuntimeError: provider=local 但 LOCAL_EMBEDDING_BASE_URL env 未設定。
    """
    args = ["--provider", agent_provider, "--model", agent_model]
    if agent_provider.lower() == "local":
        base_url = os.environ.get("LOCAL_EMBEDDING_BASE_URL")
        if not base_url:
            raise RuntimeError(
                "Agent embedding_provider=local 但 LOCAL_EMBEDDING_BASE_URL 未設定"
            )
        api_key = os.environ.get("LOCAL_EMBEDDING_API_KEY", "any")
        args.extend(["--base-url", base_url, "--api-key", api_key])
    return args


def _run_ingest_subprocess(
    cmd: list[str], timeout_seconds: int
) -> tuple[int, str, str]:
    """以 subprocess.Popen 執行 ingest 指令，封裝 timeout 強制終止邏輯。

    安全性：禁止 shell=True，cmd 必須為列表形式。
    POSIX：start_new_session=True，逾時時透過 killpg 一併回收孫進程。
    Windows：走 proc.kill() 路徑（無 killpg）。

    Returns:
        (exit_code, stdout, stderr)

    Raises:
        subprocess.TimeoutExpired: 子程序逾時且已強制終止（不吞例外，由 caller 轉換）。
        OSError / subprocess.SubprocessError: Popen 自身錯誤原樣冒出。
    """
    popen_kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
    }
    if sys.platform != "win32":
        popen_kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **popen_kwargs)  # noqa: S603
    try:
        stdout_data, stderr_data = proc.communicate(timeout=timeout_seconds)
        return proc.returncode, stdout_data, stderr_data
    except subprocess.TimeoutExpired:
        # 強制終止整個 process group，回收子 / 孫進程，避免殭屍
        if sys.platform != "win32":
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
        else:
            proc.kill()
        try:
            proc.wait(timeout=INGEST_KILL_GRACE_SEC)
        except subprocess.TimeoutExpired:
            pass
        raise


def _snapshot_embedding_to_sync_log(sync_log: Any, agent: Any) -> None:
    """將 agent 當下的 embedding 設定凍結拷貝至 sync_log。

    在「找到 agent 之後、改 status=running 之前」呼叫，與 started_at 同一個
    transaction 一起 commit。日後 agent 切 model，歷史紀錄不會「歪掉」。

    不寫 base_url / api_key（敏感資訊，且 base_url 可在 Agent 詳情頁查）。
    """
    sync_log.embedding_provider = (
        str(agent.embedding_provider) if agent.embedding_provider is not None else None
    )
    sync_log.embedding_model = (
        str(agent.embedding_model) if agent.embedding_model is not None else None
    )


def _finalize_sync_log_failed(
    db: Any, sync_log: Any, error_message: str
) -> None:
    """將 sync_log 標記為 failed 終態並 commit。

    用於 retry 已用盡或外部前置錯誤時的統一收尾。
    """
    sync_log.status = "failed"
    sync_log.stderr = error_message[:STDERR_MAX_CHARS]
    sync_log.finished_at = datetime.now(timezone.utc)
    db.commit()


def _finalize_sync_log_completed(
    db: Any,
    sync_log: Any,
    *,
    items_count: int,
    stdout_data: str,
    stderr_data: str,
) -> None:
    """將 sync_log 標記為 completed 終態並計算 duration_sec、commit。

    started_at 可能無 tzinfo（SQLite 場景），補上 UTC 後再算秒差。
    """
    finished_at = datetime.now(timezone.utc)
    started_at = sync_log.started_at
    if started_at and started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    sync_log.status = "completed"
    sync_log.items_count = items_count
    sync_log.stdout = stdout_data
    sync_log.stderr = stderr_data
    sync_log.finished_at = finished_at
    sync_log.duration_sec = (
        int((finished_at - started_at).total_seconds()) if started_at else None
    )
    db.commit()


def _execute_ingest_with_subprocess(
    cmd: list[str], sync_log: Any
) -> tuple[str, str]:
    """執行 ingest 子程序並處理 non-zero exit / timeout 的錯誤轉換。

    成功時回傳 (stdout, stderr)；失敗時 raise RuntimeError（讓上層 narrow except 統一處理）。
    """
    try:
        returncode, stdout_data, stderr_data = _run_ingest_subprocess(
            cmd, INGEST_SUBPROCESS_TIMEOUT_SEC
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"Ingestion script 執行逾時（{INGEST_SUBPROCESS_TIMEOUT_SEC} 秒）"
        )

    if returncode != 0:
        # 先把 stdout/stderr 寫入 sync_log，確保運維可透過 /sync-logs 查詢原因
        sync_log.stdout = stdout_data
        sync_log.stderr = stderr_data[:STDERR_MAX_CHARS]
        # 在錯誤訊息中附帶 stderr 摘要，方便直接從 Celery log 診斷
        stderr_snippet = (stderr_data.strip() or stdout_data.strip())[:300]
        detail = f"\nstderr: {stderr_snippet}" if stderr_snippet else ""
        raise RuntimeError(f"Ingestion script 退出碼 {returncode}{detail}")

    return stdout_data, stderr_data


def _validate_ingest_script_path(script_path: str) -> None:
    """檢查 ingest_script_path 路徑安全與檔案存在性。"""
    # 防止路徑穿越攻擊，允許完整絕對路徑（如 /opt/rasa_integration/ingest_kb.py）
    if ".." in script_path:
        raise RuntimeError(
            f"ingest_script_path 包含不允許的上級目錄引用：{script_path}"
        )
    # 早期診斷：腳本檔案不存在時立即報錯，避免 subprocess 回傳曖昧的 exit 2
    if not os.path.isfile(script_path):
        raise RuntimeError(
            f"Ingestion script 不存在或無法存取：{script_path}"
        )


def _write_export_txt(output_path: str, txt_content: str, txt_output_path: str) -> None:
    """寫入匯出 .txt 並驗證父目錄非空。"""
    parent_dir = os.path.dirname(output_path)
    if not parent_dir:
        raise RuntimeError(
            f"txt_output_path 設定無效（dirname 為空）：{txt_output_path!r}"
        )
    os.makedirs(parent_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(txt_content)


def _escape_reserved_keywords(text: str) -> str:
    """將 [Question] / [Answer] 保留字串改寫為全形，避免污染匯出格式。"""
    return text.replace("[Question]", "【Question】").replace("[Answer]", "【Answer】")


celery_app = Celery("tasks", broker=REDIS_URL)
celery_app.conf.update(
    task_ignore_result=True,
    task_soft_time_limit=TASK_SOFT_TIME_LIMIT_SEC,
    task_acks_late=True,
)


@celery_app.task(bind=True, max_retries=TASK_MAX_RETRIES, default_retry_delay=TASK_RETRY_DELAY_SEC)
def run_ingestion_sync(self, agent_id: str, sync_log_id: str) -> None:  # type: ignore[misc]
    """
    1. 取出 approved/synced 的 FAQ
    2. 寫入 {txt_output_path}/faq_export.txt（[Question]/[Answer] 格式）
    3. 透過 _run_ingest_subprocess（內部呼叫 subprocess.Popen(cmd, ...)）執行 ingest 腳本
    4. 更新 sync_logs 狀態與輸出
    5. 標記所有已同步項目為 synced

    例外控制：narrow except 限定 (RuntimeError, OSError, subprocess.SubprocessError, IOError)，
    KeyboardInterrupt 等 BaseException 必須原樣冒出。
    """
    from api.database.models import Agent, KnowledgeItem, SyncLog  # noqa: PLC0415
    from api.database.session import SessionLocal  # noqa: PLC0415

    db = SessionLocal()
    sync_log = None

    try:
        sync_log = db.query(SyncLog).filter(
            SyncLog.id == uuid.UUID(sync_log_id)
        ).first()
        if not sync_log:
            return

        agent = db.query(Agent).filter(Agent.id == uuid.UUID(agent_id)).first()
        if not agent:
            sync_log.status = "failed"
            sync_log.stderr = "Agent 不存在"
            db.commit()
            return

        # 凍結 embedding 快照（必須在改 status=running 之前，與 started_at 一同 commit）
        _snapshot_embedding_to_sync_log(sync_log, agent)
        sync_log.status = "running"
        sync_log.started_at = datetime.now(timezone.utc)
        db.commit()

        # 取出 approved 及 synced 的 FAQ
        items = (
            db.query(KnowledgeItem)
            .filter(
                KnowledgeItem.agent_id == uuid.UUID(agent_id),
                KnowledgeItem.status.in_(["approved", "synced"]),
            )
            .all()
        )

        # 組合 .txt 內容（防保留字符污染）
        blocks: list[str] = []
        for item in items:
            question = _escape_reserved_keywords(item.question)
            answer = _escape_reserved_keywords(item.answer)
            blocks.append(f"[Question]\n{question}\n\n[Answer]\n{answer}")

        # ── 無資料提前結束（避免以空 txt 清空 Qdrant collection）──────────────
        if not blocks:
            finished_at = datetime.now(timezone.utc)
            started_at = sync_log.started_at
            if started_at and started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            sync_log.status = "completed"
            sync_log.items_count = 0
            sync_log.stdout = (
                "此 Agent 目前無 approved 或 synced 狀態的 FAQ，略過同步。"
                "請先將 FAQ 審核通過後再執行同步。"
            )
            sync_log.finished_at = finished_at
            sync_log.duration_sec = (
                int((finished_at - started_at).total_seconds()) if started_at else None
            )
            db.commit()
            return

        txt_content = "\n\n".join(blocks)
        output_path = str(agent.txt_output_path).rstrip("/") + "/faq_export.txt"
        sync_log.output_file = output_path

        _write_export_txt(output_path, txt_content, str(agent.txt_output_path))

        # 執行 ingest script（若有設定）
        stdout_data = ""
        stderr_data = ""

        if agent.ingest_script_path:
            script_path = str(agent.ingest_script_path)
            _validate_ingest_script_path(script_path)

            # 從環境變數讀 Qdrant URL（與 OpenAI key 一樣由 docker-compose 注入）
            qdrant_url = os.environ.get("QDRANT_URL")
            if not qdrant_url:
                raise RuntimeError("QDRANT_URL 未設定，無法執行 ingest")

            collection_name = str(agent.qdrant_collection)
            cmd = [
                "python",
                script_path,
                "--source", output_path,
                "--qdrant-url", qdrant_url,
                "--collection", collection_name,
                "--doc-id", f"{collection_name}_v1",
                "--clear",  # 同步前清空 collection，確保已刪除 FAQ 的舊向量不殘留
                *_build_embedding_args_from_env(
                    str(agent.embedding_provider), str(agent.embedding_model)
                ),
            ]
            stdout_data, stderr_data = _execute_ingest_with_subprocess(cmd, sync_log)

        # 標記所有項目為 synced
        for item in items:
            item.status = "synced"

        _finalize_sync_log_completed(
            db, sync_log,
            items_count=len(items),
            stdout_data=stdout_data,
            stderr_data=stderr_data,
        )

    except (RuntimeError, OSError, subprocess.SubprocessError, IOError) as exc:
        logger.exception(
            "sync_task_failed",
            agent_id=agent_id,
            sync_log_id=sync_log_id,
            error=str(exc),
        )
        # 先判斷 retry 是否已用盡，再決定是否標 failed。
        # self.retry(exc=...) 用盡 max_retries 時會「重拋原本 exc」，不是 MaxRetriesExceededError，
        # 所以不能單靠 try/except MaxRetriesExceededError 攔截。
        max_retries = self.max_retries if self.max_retries is not None else TASK_MAX_RETRIES
        if self.request.retries >= max_retries:
            # 已是最後一次失敗，寫入終態
            if sync_log:
                _finalize_sync_log_failed(db, sync_log, str(exc))
            raise  # 讓 Celery 也標記任務為 FAILURE
        # 仍有 retry 額度，排程重試（中間狀態維持 running）
        countdown = RETRY_BACKOFF_BASE_SEC * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=TASK_MAX_RETRIES, default_retry_delay=TASK_RETRY_DELAY_SEC)
def run_category_sync(self, agent_id: str, category_id: str, sync_log_id: str) -> None:  # type: ignore[misc]
    """
    分類同步：針對指定分類（含子孫分類）的 FAQ 進行向量化同步。
    1. 收集分類樹（目標 + 所有子孫）
    2. 取出 approved/synced 的 FAQ
    3. 寫入含 [Category] 區塊的 txt
    4. 透過 _run_ingest_subprocess（內部使用 subprocess.Popen）執行 ingest_script_path
       （不帶 --clear，帶 --delete-category-paths）
    5. 標記同步項目為 synced
    6. 更新 sync_logs

    例外控制：narrow except 限定 (RuntimeError, OSError, subprocess.SubprocessError, IOError)。
    """
    from api.database.models import Agent, Category, KnowledgeItem, SyncLog  # noqa: PLC0415
    from api.database.session import SessionLocal  # noqa: PLC0415
    from api.utils.category_path import build_category_path, collect_category_subtree  # noqa: PLC0415

    db = SessionLocal()
    sync_log = None

    try:
        sync_log = db.query(SyncLog).filter(
            SyncLog.id == uuid.UUID(sync_log_id)
        ).first()
        if not sync_log:
            return

        agent = db.query(Agent).filter(Agent.id == uuid.UUID(agent_id)).first()
        if not agent:
            sync_log.status = "failed"
            sync_log.stderr = "Agent 不存在"
            db.commit()
            return

        target_cat = db.query(Category).filter(
            Category.id == uuid.UUID(category_id),
            Category.agent_id == uuid.UUID(agent_id),
        ).first()
        if not target_cat:
            sync_log.status = "failed"
            sync_log.stderr = "分類不存在"
            db.commit()
            return

        # 凍結 embedding 快照（必須在改 status=running 之前，與 started_at 一同 commit）
        _snapshot_embedding_to_sync_log(sync_log, agent)
        sync_log.status = "running"
        sync_log.started_at = datetime.now(timezone.utc)
        db.commit()

        # 載入此 agent 的全部分類
        all_cats = db.query(Category).filter(
            Category.agent_id == uuid.UUID(agent_id)
        ).all()
        cat_map = {c.id: c for c in all_cats}

        # 收集目標分類的子樹 ID（含自身）
        subtree_ids = collect_category_subtree(uuid.UUID(category_id), cat_map)

        # 計算子樹內每個分類的 category_path（供 --delete-category-paths 使用）
        subtree_paths = list({
            build_category_path(cid, cat_map)
            for cid in subtree_ids
            if build_category_path(cid, cat_map)
        })

        # 取出 approved/synced 的 FAQ
        items = (
            db.query(KnowledgeItem)
            .filter(
                KnowledgeItem.agent_id == uuid.UUID(agent_id),
                KnowledgeItem.category_id.in_(subtree_ids),
                KnowledgeItem.status.in_(["approved", "synced"]),
            )
            .all()
        )

        # 組合含 [Category] 區塊的 txt
        blocks: list[str] = []
        for item in items:
            cat_path = build_category_path(item.category_id, cat_map)
            question = _escape_reserved_keywords(item.question)
            answer = _escape_reserved_keywords(item.answer)
            blocks.append(
                f"[Category]\n{cat_path}\n\n[Question]\n{question}\n\n[Answer]\n{answer}"
            )

        txt_content = "\n\n".join(blocks)
        output_path = (
            str(agent.txt_output_path).rstrip("/")
            + f"/category_{category_id}_export.txt"
        )
        sync_log.output_file = output_path
        _write_export_txt(output_path, txt_content, str(agent.txt_output_path))

        stdout_data = ""
        stderr_data = ""

        if agent.ingest_script_path:
            script_path = str(agent.ingest_script_path)
            _validate_ingest_script_path(script_path)

            qdrant_url = os.environ.get("QDRANT_URL")
            if not qdrant_url:
                raise RuntimeError("QDRANT_URL 未設定，無法執行 ingest")

            collection_name = str(agent.qdrant_collection)
            cmd = [
                "python",
                script_path,
                "--source", output_path,
                "--qdrant-url", qdrant_url,
                "--collection", collection_name,
                "--doc-id", f"{collection_name}_v1",
                "--delete-category-paths", ",".join(subtree_paths),
                # 不帶 --clear：精準刪除指定 category_path 的向量
                *_build_embedding_args_from_env(
                    str(agent.embedding_provider), str(agent.embedding_model)
                ),
            ]
            stdout_data, stderr_data = _execute_ingest_with_subprocess(cmd, sync_log)

        for item in items:
            item.status = "synced"

        _finalize_sync_log_completed(
            db, sync_log,
            items_count=len(items),
            stdout_data=stdout_data,
            stderr_data=stderr_data,
        )

    except (RuntimeError, OSError, subprocess.SubprocessError, IOError) as exc:
        logger.exception(
            "category_sync_task_failed",
            agent_id=agent_id,
            category_id=category_id,
            sync_log_id=sync_log_id,
            error=str(exc),
        )
        max_retries = self.max_retries if self.max_retries is not None else TASK_MAX_RETRIES
        if self.request.retries >= max_retries:
            if sync_log:
                _finalize_sync_log_failed(db, sync_log, str(exc))
            raise
        countdown = RETRY_BACKOFF_BASE_SEC * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
    finally:
        db.close()
