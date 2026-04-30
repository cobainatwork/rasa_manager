"""
Regression test for B3：subprocess.TimeoutExpired 後必須以 killpg 殺整個 process group，
回收子 / 孫進程，避免殭屍。
"""
from __future__ import annotations

import subprocess
import sys
import uuid
from unittest.mock import MagicMock, mock_open, patch

import pytest

from tasks import run_ingestion_sync
from tests.conftest import AGENT_ID

SYNC_LOG_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


def _make_sync_log() -> MagicMock:
    sync_log = MagicMock()
    sync_log.id = SYNC_LOG_ID
    sync_log.status = "pending"
    sync_log.started_at = None
    sync_log.stderr = None
    return sync_log


def _make_agent() -> MagicMock:
    agent = MagicMock()
    agent.id = AGENT_ID
    agent.txt_output_path = "/tmp/agent_test"
    agent.ingest_script_path = "/opt/scripts/ingest.py"
    return agent


def _make_db(sync_log: MagicMock, agent: MagicMock) -> MagicMock:
    db = MagicMock()
    faq = MagicMock()
    faq.question = "Q"
    faq.answer = "A"

    def query_se(model: object) -> MagicMock:
        q = MagicMock()
        if model.__name__ == "SyncLog":
            q.filter.return_value.first.return_value = sync_log
        elif model.__name__ == "Agent":
            q.filter.return_value.first.return_value = agent
        else:
            q.filter.return_value.all.return_value = [faq]
        return q

    db.query.side_effect = query_se
    return db


class TestB3Killpg:
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="killpg / start_new_session 為 POSIX-only；Windows 走 proc.kill() 分支",
    )
    def test_timeout_triggers_killpg(self) -> None:
        """逾時時應呼叫 os.killpg 殺整個 process group。"""
        sync_log = _make_sync_log()
        agent = _make_agent()
        db = _make_db(sync_log, agent)

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(
            cmd="python /opt/scripts/ingest.py", timeout=280
        )
        mock_proc.wait.return_value = None

        with (
            patch("api.database.session.SessionLocal", return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("subprocess.Popen", return_value=mock_proc) as mock_popen,
            patch("os.killpg") as mock_killpg,
            patch("os.getpgid", return_value=12345),
        ):
            run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])

        # 1. Popen 必須帶 start_new_session=True（POSIX 才能 killpg）
        _, kwargs = mock_popen.call_args
        assert kwargs.get("start_new_session") is True

        # 2. 逾時觸發 killpg
        assert mock_killpg.called, "TimeoutExpired 後必須呼叫 os.killpg 回收孫進程"

        # 3. proc.wait 應被呼叫以確保資源回收
        mock_proc.wait.assert_called()

    def test_uses_popen_not_run(self) -> None:
        """tasks.py 必須改用 subprocess.Popen，不可繼續用 subprocess.run。"""
        import inspect

        import tasks

        src = inspect.getsource(tasks.run_ingestion_sync)
        # 不可包含 subprocess.run( 呼叫
        assert "subprocess.run(" not in src, (
            "B3：必須改用 subprocess.Popen 以支援 start_new_session 與 killpg"
        )
        assert "subprocess.Popen(" in src
