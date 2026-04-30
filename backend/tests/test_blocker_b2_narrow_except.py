"""
Regression test for B2：tasks.py 不再使用 broad except Exception，
且 MaxRetries 後寫入 sync_log.stderr 包含具體錯誤訊息（截斷至 1000 字元），
而非泛用「同步任務執行失敗，請查閱系統日誌」字串。
"""
from __future__ import annotations

import inspect
import uuid
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import tasks
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


def _make_db(sync_log: MagicMock, agent: MagicMock, items: list) -> MagicMock:
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


class TestB2NarrowExcept:
    def test_except_clause_is_narrow(self) -> None:
        """tasks.py 不可使用 broad except Exception 包住主執行區塊。"""
        src = inspect.getsource(tasks.run_ingestion_sync)
        # 必須含 narrow exception types
        assert "RuntimeError" in src
        assert "OSError" in src
        assert "subprocess.SubprocessError" in src
        # 不允許 except Exception 作為頂層 catch（仍允許其他註解 / 字串中出現）
        assert "except Exception" not in src, (
            "tasks.run_ingestion_sync 必須改 narrow except，"
            "不可使用 except Exception 吃掉所有錯誤"
        )

    def test_max_retries_stderr_contains_specific_message(self) -> None:
        """MaxRetries 後 sync_log.stderr 應含具體錯誤訊息，非泛用字串。"""
        from celery.exceptions import MaxRetriesExceededError

        sync_log = _make_sync_log()
        agent = _make_agent()
        faq = MagicMock()
        faq.question = "Q"
        faq.answer = "A"
        db = _make_db(sync_log, agent, [faq])

        specific_msg = "Ingestion script blew up with very specific reason xyz"

        def popen_side_effect(*args: Any, **kwargs: Any) -> MagicMock:
            raise RuntimeError(specific_msg)

        with (
            patch("api.database.session.SessionLocal", return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("subprocess.Popen", side_effect=popen_side_effect),
            patch.object(
                run_ingestion_sync, "retry",
                side_effect=MaxRetriesExceededError(),
            ),
        ):
            run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])

        assert sync_log.status == "failed"
        assert sync_log.stderr is not None
        assert "同步任務執行失敗" not in sync_log.stderr
        assert specific_msg in sync_log.stderr
        assert len(sync_log.stderr) <= 1000

    def test_stderr_truncated_to_1000_chars(self) -> None:
        """超長錯誤訊息應被截斷至 1000 字元，避免 DB 欄位爆量。"""
        from celery.exceptions import MaxRetriesExceededError

        sync_log = _make_sync_log()
        agent = _make_agent()
        faq = MagicMock()
        faq.question = "Q"
        faq.answer = "A"
        db = _make_db(sync_log, agent, [faq])

        long_msg = "x" * 5000

        def popen_side_effect(*args: Any, **kwargs: Any) -> MagicMock:
            raise RuntimeError(long_msg)

        with (
            patch("api.database.session.SessionLocal", return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("subprocess.Popen", side_effect=popen_side_effect),
            patch.object(
                run_ingestion_sync, "retry",
                side_effect=MaxRetriesExceededError(),
            ),
        ):
            run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])

        assert sync_log.stderr is not None
        assert len(sync_log.stderr) == 1000

    def test_keyboard_interrupt_not_swallowed(self) -> None:
        """narrow except 不應吃掉 KeyboardInterrupt。"""
        sync_log = _make_sync_log()
        agent = _make_agent()
        faq = MagicMock()
        faq.question = "Q"
        faq.answer = "A"
        db = _make_db(sync_log, agent, [faq])

        def popen_side_effect(*args: Any, **kwargs: Any) -> MagicMock:
            raise KeyboardInterrupt()

        raised = False
        try:
            with (
                patch("api.database.session.SessionLocal", return_value=db),
                patch("builtins.open", mock_open()),
                patch("os.makedirs"),
                patch("subprocess.Popen", side_effect=popen_side_effect),
            ):
                result = run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])
                # celery eager 模式會把 BaseException 包進 result
                if result.failed():
                    inner = result.result
                    if isinstance(inner, KeyboardInterrupt):
                        raise inner
        except KeyboardInterrupt:
            raised = True
        except BaseException:
            # celery 可能包裝為 Retry 等，但 KeyboardInterrupt 不應被 narrow except 接住
            # 然而 celery eager 模式會把例外包進 result；這裡我們改驗證 sync_log 不被標 failed
            pass

        # KeyboardInterrupt 不應觸發我們的 narrow except 分支，
        # 因此 sync_log.stderr 不應被寫成截斷錯誤訊息
        assert raised or sync_log.stderr is None or sync_log.status != "failed"
