"""
Celery 任務測試：Mock DB 驗證 txt 格式、sync_logs 狀態、保留字符替換。

SessionLocal 在 tasks.py 中是函式內 lazy import，
patch 路徑必須指向 api.database.session.SessionLocal。
"""
from __future__ import annotations

import inspect
import os
import subprocess
import sys
import uuid
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest

import tasks
from tasks import run_ingestion_sync
from tests.conftest import AGENT_ID


def _make_mock_proc(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> MagicMock:
    """Popen mock 工廠：設定 communicate 回傳值與 returncode，消除重複樣板。"""
    proc = MagicMock()
    proc.communicate.return_value = (stdout, stderr)
    proc.returncode = returncode
    return proc


# ── txt 格式產生邏輯（保留字符替換）─────────────────────────────────────────

class TestTxtFormat:
    """直接測試 txt 區塊組合邏輯，不需要執行完整 Celery task。"""

    def _build_blocks(self, items: list[dict]) -> list[str]:  # type: ignore[type-arg]
        blocks = []
        for item in items:
            q = item["question"].replace("[Question]", "【Question】").replace("[Answer]", "【Answer】")
            a = item["answer"].replace("[Question]", "【Question】").replace("[Answer]", "【Answer】")
            blocks.append(f"[Question]\n{q}\n\n[Answer]\n{a}")
        return blocks

    def test_normal_faq_format(self) -> None:
        items = [{"question": "什麼是 AI？", "answer": "人工智慧。"}]
        blocks = self._build_blocks(items)
        assert blocks[0] == "[Question]\n什麼是 AI？\n\n[Answer]\n人工智慧。"

    def test_reserved_keyword_in_question_replaced(self) -> None:
        items = [{"question": "[Question] 這是標題", "answer": "正常答案"}]
        blocks = self._build_blocks(items)
        assert "【Question】" in blocks[0]
        assert "[Question] 這是標題" not in blocks[0]

    def test_reserved_keyword_in_answer_replaced(self) -> None:
        items = [{"question": "正常問題", "answer": "包含 [Answer] 的答案"}]
        blocks = self._build_blocks(items)
        assert "【Answer】" in blocks[0]

    def test_multiple_items_joined_by_double_newline(self) -> None:
        items = [
            {"question": "Q1", "answer": "A1"},
            {"question": "Q2", "answer": "A2"},
        ]
        blocks = self._build_blocks(items)
        full_txt = "\n\n".join(blocks)
        assert full_txt.count("[Question]") == 2
        assert full_txt.count("[Answer]") == 2

    def test_empty_items_produces_empty_blocks(self) -> None:
        blocks = self._build_blocks([])
        assert blocks == []


# ── run_ingestion_sync task（Mock DB + subprocess）────────────────────────────

class TestRunIngestionSync:
    """
    SessionLocal 以 api.database.session.SessionLocal 為 patch 目標，
    因為 tasks.py 在函式內動態 import。
    """

    SESSION_PATCH = "api.database.session.SessionLocal"

    def _make_sync_log(self) -> MagicMock:
        log = MagicMock()
        log.id = uuid.UUID("00000000-0000-0000-0000-000000000099")
        log.status = "pending"
        return log

    def _make_agent(self, has_script: bool = True) -> MagicMock:
        agent = MagicMock()
        agent.id = AGENT_ID
        agent.txt_output_path = "/opt/rasa_docs/test"
        agent.ingest_script_path = "ingest.py" if has_script else None
        return agent

    def _make_faq_item(self, question: str = "Q", answer: str = "A") -> MagicMock:
        item = MagicMock()
        item.question = question
        item.answer = answer
        item.id = uuid.uuid4()
        item.status = "approved"
        return item

    def _make_db(
        self,
        sync_log: MagicMock,
        agent: MagicMock | None,
        faqs: list[MagicMock],
    ) -> MagicMock:
        db = MagicMock()
        call_index = [0]

        def query_se(model: object) -> MagicMock:
            q = MagicMock()
            idx = call_index[0]
            call_index[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = sync_log
            elif idx == 1:
                q.filter.return_value.first.return_value = agent
            else:
                # tasks.py 用 .filter(cond1, cond2).all()（單層 filter）
                q.filter.return_value.all.return_value = faqs
            return q

        db.query.side_effect = query_se
        return db

    def test_sync_log_marked_completed(self) -> None:
        sync_log = self._make_sync_log()
        agent = self._make_agent()
        faq = self._make_faq_item()
        db = self._make_db(sync_log, agent, [faq])

        with (
            patch.dict(os.environ, {"QDRANT_URL": "http://fake:6333"}),
            patch(self.SESSION_PATCH, return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("os.path.isfile", return_value=True),
            patch("shutil.copy2"),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_popen.return_value = _make_mock_proc(stdout="ok")
            run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])

        assert sync_log.status == "completed"

    def test_sync_log_failed_when_agent_not_found(self) -> None:
        sync_log = self._make_sync_log()
        db = self._make_db(sync_log, None, [])

        with patch(self.SESSION_PATCH, return_value=db):
            run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])

        assert sync_log.status == "failed"

    def test_items_status_updated_to_synced(self) -> None:
        sync_log = self._make_sync_log()
        agent = self._make_agent()
        faq = self._make_faq_item()
        db = self._make_db(sync_log, agent, [faq])

        with (
            patch.dict(os.environ, {"QDRANT_URL": "http://fake:6333"}),
            patch(self.SESSION_PATCH, return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("os.path.isfile", return_value=True),
            patch("shutil.copy2"),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_popen.return_value = _make_mock_proc()
            run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])

        assert faq.status == "synced"


# ── Regression 共用 fixture ─────────────────────────────────────────────────

@pytest.fixture
def _regression_make_agent(agent_factory):
    """共用 fixture：B2/B3 ingestion 用 Agent mock。"""
    def _make() -> MagicMock:
        return agent_factory(
            txt_output_path="/tmp/agent_test",
            ingest_script_path="/opt/scripts/ingest.py",
            rasa_rest_url=None,
        )
    return _make


_B23_SYNC_LOG_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _b23_make_sync_log() -> MagicMock:
    sync_log = MagicMock()
    sync_log.id = _B23_SYNC_LOG_ID
    sync_log.status = "pending"
    sync_log.started_at = None
    sync_log.stderr = None
    return sync_log


def _b23_make_db(sync_log: MagicMock, agent: MagicMock, items: list) -> MagicMock:
    db = MagicMock()

    def query_se(model: object) -> MagicMock:
        q = MagicMock()
        if model.__name__ == "SyncLog":
            q.filter.return_value.first.return_value = sync_log
        elif model.__name__ == "Agent":
            q.filter.return_value.first.return_value = agent
        else:
            q.filter.return_value.all.return_value = items
        return q

    db.query.side_effect = query_se
    return db


# ── Regression: B1 (Celery retry must not prematurely mark sync_log failed) ──

class TestCeleryRetryRegression:
    """Regression: B1 (Celery retry must not prematurely mark sync_log failed)."""

    SESSION_PATCH = "api.database.session.SessionLocal"

    def _make_sync_log(self) -> MagicMock:
        log = MagicMock()
        log.id = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
        log.status = "pending"
        return log

    def _make_agent(self) -> MagicMock:
        agent = MagicMock()
        agent.id = AGENT_ID
        agent.txt_output_path = "/opt/rasa_docs/test"
        agent.ingest_script_path = "ingest.py"
        return agent

    def _make_faq(self) -> MagicMock:
        faq = MagicMock()
        faq.question = "Q"
        faq.answer = "A"
        faq.id = uuid.uuid4()
        faq.status = "approved"
        return faq

    def _make_db(self, sync_log: MagicMock, agent: MagicMock, faqs: list) -> MagicMock:
        db = MagicMock()
        call_index = [0]

        def query_se(model: object) -> MagicMock:
            q = MagicMock()
            idx = call_index[0]
            call_index[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = sync_log
            elif idx == 1:
                q.filter.return_value.first.return_value = agent
            else:
                q.filter.return_value.all.return_value = faqs
            return q

        db.query.side_effect = query_se
        return db

    def test_subprocess_failure_during_retry_does_not_set_failed(self) -> None:
        """retries=1（未達 max_retries=3）失敗時不可標 failed；改 mock Popen 實際觸發失敗分支。"""
        sync_log = self._make_sync_log()
        agent = self._make_agent()
        faq = self._make_faq()
        db = self._make_db(sync_log, agent, [faq])

        with (
            patch(self.SESSION_PATCH, return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("os.path.isfile", return_value=True),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_popen.return_value = _make_mock_proc(returncode=1, stderr="boom")
            # retries=1：仍有 retry 額度（max_retries=3），應走 self.retry() 路徑
            try:
                run_ingestion_sync.apply(
                    args=[str(AGENT_ID), str(sync_log.id)], retries=1,
                )
            except Exception:
                pass  # self.retry 在 EAGER 模式會冒出，忽略

        # 關鍵斷言：retry 中途 sync_log 不能被標 failed（B1 規格）
        assert sync_log.status != "failed", (
            f"retries=1（未達 max_retries）時 sync_log.status 不可被標為 failed，"
            f"實際為 {sync_log.status!r}"
        )

    def test_max_retries_exceeded_writes_failed(self) -> None:
        """retries 達上限時應標記 failed 並重拋（不可吞錯）。"""
        sync_log = self._make_sync_log()
        agent = self._make_agent()
        faq = self._make_faq()
        db = self._make_db(sync_log, agent, [faq])

        with (
            patch(self.SESSION_PATCH, return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("os.path.isfile", return_value=True),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_popen.return_value = _make_mock_proc(returncode=1, stderr="boom")
            # retries=3 模擬已用盡（max_retries=3）
            result = run_ingestion_sync.apply(
                args=[str(AGENT_ID), str(sync_log.id)],
                retries=3,
            )

        assert result.failed(), "達 max_retries 時 task 應標記為失敗"
        assert sync_log.status == "failed"
        assert sync_log.finished_at is not None


# ── Regression: B2 (subprocess except must be narrow) ────────────────────────

class TestSubprocessNarrowExceptRegression:
    """Regression: B2 (subprocess except must be narrow, errors must surface)."""

    def test_except_clause_is_narrow(self) -> None:
        """tasks.py 不可使用 broad except Exception 包住主執行區塊。"""
        src = inspect.getsource(tasks.run_ingestion_sync)
        assert "RuntimeError" in src
        assert "OSError" in src
        assert "subprocess.SubprocessError" in src
        assert "except Exception" not in src, (
            "tasks.run_ingestion_sync 必須改 narrow except，"
            "不可使用 except Exception 吃掉所有錯誤"
        )

    def test_max_retries_stderr_contains_specific_message(self, _regression_make_agent) -> None:
        sync_log = _b23_make_sync_log()
        agent = _regression_make_agent()
        faq = MagicMock()
        faq.question = "Q"
        faq.answer = "A"
        db = _b23_make_db(sync_log, agent, [faq])

        specific_msg = "Ingestion script blew up with very specific reason xyz"

        def popen_side_effect(*args: Any, **kwargs: Any) -> MagicMock:
            raise RuntimeError(specific_msg)

        with (
            patch.dict(os.environ, {"QDRANT_URL": "http://fake:6333"}),
            patch("api.database.session.SessionLocal", return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("os.path.isfile", return_value=True),
            patch("subprocess.Popen", side_effect=popen_side_effect),
        ):
            # retries=3 模擬已達 max_retries
            run_ingestion_sync.apply(
                args=[str(AGENT_ID), str(sync_log.id)], retries=3,
            )

        assert sync_log.status == "failed"
        assert sync_log.stderr is not None
        assert "同步任務執行失敗" not in sync_log.stderr
        assert specific_msg in sync_log.stderr
        assert len(sync_log.stderr) <= 1000

    def test_stderr_truncated_to_1000_chars(self, _regression_make_agent) -> None:
        sync_log = _b23_make_sync_log()
        agent = _regression_make_agent()
        faq = MagicMock()
        faq.question = "Q"
        faq.answer = "A"
        db = _b23_make_db(sync_log, agent, [faq])

        long_msg = "x" * 5000

        def popen_side_effect(*args: Any, **kwargs: Any) -> MagicMock:
            raise RuntimeError(long_msg)

        with (
            patch.dict(os.environ, {"QDRANT_URL": "http://fake:6333"}),
            patch("api.database.session.SessionLocal", return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("os.path.isfile", return_value=True),
            patch("subprocess.Popen", side_effect=popen_side_effect),
        ):
            run_ingestion_sync.apply(
                args=[str(AGENT_ID), str(sync_log.id)], retries=3,
            )

        assert sync_log.stderr is not None
        assert len(sync_log.stderr) == 1000

    def test_keyboard_interrupt_not_swallowed(self, _regression_make_agent) -> None:
        sync_log = _b23_make_sync_log()
        agent = _regression_make_agent()
        faq = MagicMock()
        faq.question = "Q"
        faq.answer = "A"
        db = _b23_make_db(sync_log, agent, [faq])

        def popen_side_effect(*args: Any, **kwargs: Any) -> MagicMock:
            raise KeyboardInterrupt()

        # narrow except 只接住 RuntimeError/OSError/SubprocessError/IOError；
        # KeyboardInterrupt 應原樣冒出，不可被吞掉。
        raised = False
        try:
            with (
                patch.dict(os.environ, {"QDRANT_URL": "http://fake:6333"}),
                patch("api.database.session.SessionLocal", return_value=db),
                patch("builtins.open", mock_open()),
                patch("os.makedirs"),
                patch("os.path.isfile", return_value=True),
                patch("subprocess.Popen", side_effect=popen_side_effect),
            ):
                result = run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])
                # Celery EAGER 模式會把 BaseException 收進 result；手動取出再 raise
                if result.failed():
                    inner = result.result
                    if isinstance(inner, KeyboardInterrupt):
                        raise inner
        except KeyboardInterrupt:
            raised = True

        # 關鍵斷言：KeyboardInterrupt 必須冒出（不可被 narrow except 吞掉）
        assert raised, "KeyboardInterrupt 必須原樣冒出，不可被 narrow except 吞掉"
        # 同時確認沒有錯把 KeyboardInterrupt 當業務錯誤寫進 sync_log
        assert sync_log.status != "failed", (
            "KeyboardInterrupt 不是業務錯誤，sync_log 不應被標 failed"
        )


# ── Regression: B3 (subprocess timeout must kill process group) ─────────────

class TestSubprocessTimeoutKillPGRegression:
    """Regression: B3 (subprocess timeout must kill process group)."""

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="killpg / start_new_session 為 POSIX-only；Windows 走 proc.kill() 分支",
    )
    def test_timeout_triggers_killpg(self, _regression_make_agent) -> None:
        sync_log = _b23_make_sync_log()
        agent = _regression_make_agent()
        faq = MagicMock()
        faq.question = "Q"
        faq.answer = "A"
        db = _b23_make_db(sync_log, agent, [faq])

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(
            cmd="python /opt/scripts/ingest.py", timeout=280
        )
        mock_proc.wait.return_value = None

        with (
            patch.dict(os.environ, {"QDRANT_URL": "http://fake:6333"}),
            patch("api.database.session.SessionLocal", return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("os.path.isfile", return_value=True),
            patch("subprocess.Popen", return_value=mock_proc) as mock_popen,
            patch("os.killpg") as mock_killpg,
            patch("os.getpgid", return_value=12345),
        ):
            run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])

        _, kwargs = mock_popen.call_args
        assert kwargs.get("start_new_session") is True

        assert mock_killpg.called, "TimeoutExpired 後必須呼叫 os.killpg 回收孫進程"

        mock_proc.wait.assert_called()

    def test_uses_popen_not_run(self) -> None:
        """tasks.py 必須改用 subprocess.Popen，不可繼續用 subprocess.run。"""
        src = inspect.getsource(tasks.run_ingestion_sync)
        assert "subprocess.run(" not in src, (
            "B3：必須改用 subprocess.Popen 以支援 start_new_session 與 killpg"
        )
        assert "subprocess.Popen(" in src

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="Windows-specific kill path（無 killpg，走 proc.kill()）",
    )
    def test_timeout_uses_kill_on_windows(self, _regression_make_agent) -> None:
        """Windows 環境下 proc.kill() 應被呼叫（不走 killpg）。"""
        sync_log = _b23_make_sync_log()
        agent = _regression_make_agent()
        faq = MagicMock()
        faq.question = "Q"
        faq.answer = "A"
        db = _b23_make_db(sync_log, agent, [faq])

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(
            cmd="python /opt/scripts/ingest.py", timeout=280
        )
        mock_proc.wait.return_value = None

        with (
            patch.dict(os.environ, {"QDRANT_URL": "http://fake:6333"}),
            patch("api.database.session.SessionLocal", return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("os.path.isfile", return_value=True),
            patch("subprocess.Popen", return_value=mock_proc) as mock_popen,
        ):
            run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])

        # Windows 不應傳 start_new_session
        _, kwargs = mock_popen.call_args
        assert kwargs.get("start_new_session") is None

        # Windows 路徑必呼叫 proc.kill()
        mock_proc.kill.assert_called()
        mock_proc.wait.assert_called()


# ── ingest script CLI 參數注入 ───────────────────────────────────────────────

class TestIngestScriptArgs:
    """驗證 subprocess.Popen 呼叫時帶有正確的 CLI 參數。"""

    SESSION_PATCH = "api.database.session.SessionLocal"

    def _make_sync_log(self) -> MagicMock:
        log = MagicMock()
        log.id = uuid.UUID("00000000-0000-0000-0000-0000000000b1")
        log.status = "pending"
        return log

    def _make_agent(self) -> MagicMock:
        agent = MagicMock()
        agent.id = AGENT_ID
        agent.qdrant_collection = f"agent_{AGENT_ID}"
        agent.txt_output_path = "/opt/rasa_docs/test"
        agent.ingest_script_path = "/opt/project/ingest_kb.py"
        return agent

    def _make_faq(self) -> MagicMock:
        faq = MagicMock()
        faq.question = "Q"
        faq.answer = "A"
        faq.id = uuid.uuid4()
        faq.status = "approved"
        return faq

    def _make_db(self, sync_log: MagicMock, agent: MagicMock, faqs: list) -> MagicMock:
        db = MagicMock()
        call_index = [0]

        def query_se(model: object) -> MagicMock:
            q = MagicMock()
            idx = call_index[0]
            call_index[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = sync_log
            elif idx == 1:
                q.filter.return_value.first.return_value = agent
            else:
                q.filter.return_value.all.return_value = faqs
            return q

        db.query.side_effect = query_se
        return db

    def test_popen_called_with_required_cli_args(self) -> None:
        sync_log = self._make_sync_log()
        agent = self._make_agent()
        faq = self._make_faq()
        db = self._make_db(sync_log, agent, [faq])

        with (
            patch.dict(os.environ, {"QDRANT_URL": "http://qdrant.test:6333"}),
            patch(self.SESSION_PATCH, return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("os.path.isfile", return_value=True),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_popen.return_value = _make_mock_proc()
            run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])

        args, _ = mock_popen.call_args
        cmd = args[0]
        assert isinstance(cmd, list), "cmd 必須以列表形式傳入，避免 shell 解析"
        assert cmd[0] == "python"
        assert cmd[1] == "/opt/project/ingest_kb.py"
        assert "--source" in cmd
        assert "--qdrant-url" in cmd
        assert "--collection" in cmd
        assert "--doc-id" in cmd
        # 參數值驗證
        assert cmd[cmd.index("--qdrant-url") + 1] == "http://qdrant.test:6333"
        assert cmd[cmd.index("--collection") + 1] == agent.qdrant_collection
        # source 應指向匯出 .txt
        source_value = cmd[cmd.index("--source") + 1]
        assert source_value.endswith("faq_export.txt")


class TestIngestScriptMissingQdrantUrl:
    """QDRANT_URL 未設定時必須拋 RuntimeError 並標記 sync_log。"""

    SESSION_PATCH = "api.database.session.SessionLocal"

    def test_missing_qdrant_url_raises_runtime_error(self) -> None:
        sync_log = MagicMock()
        sync_log.id = uuid.UUID("00000000-0000-0000-0000-0000000000c1")
        sync_log.status = "pending"
        sync_log.started_at = None

        agent = MagicMock()
        agent.id = AGENT_ID
        agent.txt_output_path = "/opt/rasa_docs/test"
        agent.ingest_script_path = "/opt/project/ingest_kb.py"

        faq = MagicMock()
        faq.question = "Q"
        faq.answer = "A"
        faq.id = uuid.uuid4()
        faq.status = "approved"

        db = MagicMock()
        call_index = [0]

        def query_se(model: object) -> MagicMock:
            q = MagicMock()
            idx = call_index[0]
            call_index[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = sync_log
            elif idx == 1:
                q.filter.return_value.first.return_value = agent
            else:
                q.filter.return_value.all.return_value = [faq]
            return q

        db.query.side_effect = query_se

        # 確保環境中沒有 QDRANT_URL
        env_no_qdrant = {k: v for k, v in os.environ.items() if k != "QDRANT_URL"}

        with (
            patch.dict(os.environ, env_no_qdrant, clear=True),
            patch(self.SESSION_PATCH, return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("os.path.isfile", return_value=True),
            patch("subprocess.Popen") as mock_popen,
        ):
            # retries=3 模擬已達 max_retries
            run_ingestion_sync.apply(
                args=[str(AGENT_ID), str(sync_log.id)], retries=3,
            )

            # Popen 不應被呼叫，因為提早拋 RuntimeError
            assert not mock_popen.called

        assert sync_log.status == "failed"
        assert sync_log.stderr is not None
        assert "QDRANT_URL" in sync_log.stderr


class TestEmbeddingCliArgs:
    """tasks._build_embedding_args_from_env：將 agent.embedding_provider/model 轉成 ingest_kb.py CLI args。"""

    def test_openai_provider_omits_base_url_and_api_key(self) -> None:
        from tasks import _build_embedding_args_from_env  # noqa: PLC0415
        args = _build_embedding_args_from_env("openai", "text-embedding-3-small")
        assert args == [
            "--provider", "openai",
            "--model", "text-embedding-3-small",
        ]

    def test_local_provider_includes_base_url_and_api_key_from_env(self) -> None:
        from tasks import _build_embedding_args_from_env  # noqa: PLC0415
        with patch.dict(os.environ, {
            "LOCAL_EMBEDDING_BASE_URL": "http://10.2.66.102/v1/embeddings",
            "LOCAL_EMBEDDING_API_KEY": "secret-key",
        }, clear=False):
            args = _build_embedding_args_from_env("local", "bge-m3-q8_0")
        assert args == [
            "--provider", "local",
            "--model", "bge-m3-q8_0",
            "--base-url", "http://10.2.66.102/v1/embeddings",
            "--api-key", "secret-key",
        ]

    def test_local_provider_defaults_api_key_when_unset(self) -> None:
        from tasks import _build_embedding_args_from_env  # noqa: PLC0415
        env = {k: v for k, v in os.environ.items() if k != "LOCAL_EMBEDDING_API_KEY"}
        env["LOCAL_EMBEDDING_BASE_URL"] = "http://local-only/v1"
        with patch.dict(os.environ, env, clear=True):
            args = _build_embedding_args_from_env("local", "bge-m3-q8_0")
        # 預設 api_key 為 'any'（多數地端 server 不檢查但 OpenAI SDK 要求非空）
        assert "--api-key" in args
        idx = args.index("--api-key")
        assert args[idx + 1] == "any"

    def test_local_provider_missing_base_url_raises(self) -> None:
        from tasks import _build_embedding_args_from_env  # noqa: PLC0415
        env = {k: v for k, v in os.environ.items() if k != "LOCAL_EMBEDDING_BASE_URL"}
        with patch.dict(os.environ, env, clear=True), pytest.raises(
            RuntimeError, match="LOCAL_EMBEDDING_BASE_URL"
        ):
            _build_embedding_args_from_env("local", "bge-m3-q8_0")


# ── Embedding snapshot 寫入 sync_log（同步歷史凍結快照）─────────────────────────

class TestEmbeddingSnapshotToSyncLog:
    """驗證 tasks._snapshot_embedding_to_sync_log 與 run_ingestion_sync / run_category_sync
    會在同步當下把 agent.embedding_provider / model 凍結至 sync_log。
    """

    SESSION_PATCH = "api.database.session.SessionLocal"

    def test_snapshot_helper_copies_provider_and_model(self) -> None:
        """helper 直接 copy provider / model 到 sync_log。"""
        from tasks import _snapshot_embedding_to_sync_log  # noqa: PLC0415

        sync_log = MagicMock()
        agent = MagicMock()
        agent.embedding_provider = "local"
        agent.embedding_model = "bge-m3-q8_0"

        _snapshot_embedding_to_sync_log(sync_log, agent)

        assert sync_log.embedding_provider == "local"
        assert sync_log.embedding_model == "bge-m3-q8_0"

    def test_snapshot_helper_handles_none_values(self) -> None:
        """agent 欄位為 None（理論上不發生，防呆）時 sync_log 也存 None，不要拋例外。"""
        from tasks import _snapshot_embedding_to_sync_log  # noqa: PLC0415

        sync_log = MagicMock()
        agent = MagicMock()
        agent.embedding_provider = None
        agent.embedding_model = None

        _snapshot_embedding_to_sync_log(sync_log, agent)

        assert sync_log.embedding_provider is None
        assert sync_log.embedding_model is None

    def test_ingestion_sync_freezes_embedding_into_sync_log(self) -> None:
        """run_ingestion_sync 完成後 sync_log 帶有 agent 當下的 embedding 快照。"""
        sync_log = MagicMock()
        sync_log.id = uuid.UUID("00000000-0000-0000-0000-0000000000c1")
        sync_log.status = "pending"
        sync_log.started_at = None
        sync_log.stderr = None

        agent = MagicMock()
        agent.id = AGENT_ID
        agent.txt_output_path = "/opt/rasa_docs/test"
        agent.ingest_script_path = "ingest.py"
        agent.qdrant_collection = "agent_test"
        agent.embedding_provider = "openai"
        agent.embedding_model = "text-embedding-3-large"

        faq = MagicMock()
        faq.question = "Q"
        faq.answer = "A"
        faq.id = uuid.uuid4()
        faq.status = "approved"

        db = MagicMock()
        call_index = [0]

        def query_se(model: object) -> MagicMock:  # noqa: ARG001
            q = MagicMock()
            idx = call_index[0]
            call_index[0] += 1
            if idx == 0:
                q.filter.return_value.first.return_value = sync_log
            elif idx == 1:
                q.filter.return_value.first.return_value = agent
            else:
                q.filter.return_value.all.return_value = [faq]
            return q

        db.query.side_effect = query_se

        with (
            patch.dict(os.environ, {"QDRANT_URL": "http://fake:6333"}),
            patch(self.SESSION_PATCH, return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("os.path.isfile", return_value=True),
            patch("subprocess.Popen") as mock_popen,
        ):
            mock_popen.return_value = _make_mock_proc(stdout="ok")
            run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])

        # 凍結快照應於完成後仍保持原 agent 設定
        assert sync_log.embedding_provider == "openai"
        assert sync_log.embedding_model == "text-embedding-3-large"
