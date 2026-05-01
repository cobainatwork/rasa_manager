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

import structlog
from celery import Celery

logger = structlog.get_logger()

REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("tasks", broker=REDIS_URL)
celery_app.conf.update(
    task_ignore_result=True,
    task_soft_time_limit=300,
    task_acks_late=True,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def run_ingestion_sync(self, agent_id: str, sync_log_id: str) -> None:  # type: ignore[misc]
    """
    1. 取出 approved/synced 的 FAQ
    2. 寫入 {txt_output_path}/faq_export.txt（[Question]/[Answer] 格式）
    3. 執行 /opt/scripts/{ingest_script_path}
    4. 更新 sync_logs 狀態與輸出
    5. 標記所有已同步項目為 synced
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
            question = (
                item.question.replace("[Question]", "【Question】")
                .replace("[Answer]", "【Answer】")
            )
            answer = (
                item.answer.replace("[Question]", "【Question】")
                .replace("[Answer]", "【Answer】")
            )
            blocks.append(f"[Question]\n{question}\n\n[Answer]\n{answer}")

        txt_content = "\n\n".join(blocks)
        output_path = str(agent.txt_output_path).rstrip("/") + "/faq_export.txt"
        sync_log.output_file = output_path

        # 寫入 .txt
        import os as _os  # noqa: PLC0415

        _os.makedirs(_os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(txt_content)

        # 執行 ingest script（若有設定）
        stdout_data = ""
        stderr_data = ""

        if agent.ingest_script_path:
            script_path = str(agent.ingest_script_path)
            # 防止路徑穿越攻擊，允許完整絕對路徑（如 /opt/rasa_integration/ingest_kb.py）
            if ".." in script_path:
                raise RuntimeError(
                    f"ingest_script_path 包含不允許的上級目錄引用：{script_path}"
                )

            # 從環境變數讀 Qdrant URL（與 OpenAI key 一樣由 docker-compose 注入）
            qdrant_url = os.environ.get("QDRANT_URL")
            if not qdrant_url:
                raise RuntimeError("QDRANT_URL 未設定，無法執行 ingest")

            agent_id_str = str(agent.id)
            # 安全性：禁止 shell=True，使用列表形式（避免空格路徑切割問題）
            cmd = [
                "python",
                script_path,
                "--source", output_path,
                "--qdrant-url", qdrant_url,
                "--collection", f"agent_{agent_id_str}",
                "--doc-id", f"agent_{agent_id_str}_v1",
            ]
            # 使用 Popen + start_new_session=True，逾時時可透過 killpg 一併回收孫進程
            popen_kwargs: dict = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
            }
            if sys.platform != "win32":
                popen_kwargs["start_new_session"] = True
            proc = subprocess.Popen(cmd, **popen_kwargs)  # noqa: S603
            try:
                stdout_data, stderr_data = proc.communicate(timeout=280)
                returncode = proc.returncode
                if returncode != 0:
                    raise RuntimeError(
                        f"Ingestion script 退出碼 {returncode}"
                    )
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
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                raise RuntimeError("Ingestion script 執行逾時（280 秒）")

        # 標記所有項目為 synced
        for item in items:
            item.status = "synced"

        finished_at = datetime.now(timezone.utc)
        started_at = sync_log.started_at
        if started_at and started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        sync_log.status = "completed"
        sync_log.items_count = len(items)
        sync_log.stdout = stdout_data
        sync_log.stderr = stderr_data
        sync_log.finished_at = finished_at
        sync_log.duration_sec = (
            int((finished_at - started_at).total_seconds()) if started_at else None
        )
        db.commit()

    except (RuntimeError, OSError, subprocess.SubprocessError, IOError) as exc:
        logger.exception(
            "sync_task_failed",
            agent_id=agent_id,
            sync_log_id=sync_log_id,
            error=str(exc),
        )
        # 在 retry 前不可寫入 'failed'：retry 成功的下一次執行會將狀態改回 running/completed，
        # 但中間若觀測 DB 仍會看到錯誤的最終狀態。
        # 僅在達到最大 retry 次數後才把 sync_log 標記為 failed（最終狀態）。
        try:
            countdown = 10 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        except self.MaxRetriesExceededError:
            if sync_log:
                sync_log.status = "failed"
                # 截斷至 1000 字元防 DB 欄位爆量；保留具體錯誤類型與訊息
                sync_log.stderr = str(exc)[:1000]
                sync_log.finished_at = datetime.now(timezone.utc)
                db.commit()
    finally:
        db.close()
