"""
Regression test for B1：Celery retry 與 sync_log 狀態錯亂。

修正前：subprocess 失敗時，except 立刻把 sync_log 標記 'failed' 並 commit，
然後才呼叫 self.retry()，導致重試成功時 DB 中已留下錯誤的 'failed' 終態。

修正後：retry 路徑下不寫 'failed'，僅在 MaxRetriesExceededError 時才寫入。
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, mock_open, patch

from tests.conftest import AGENT_ID


class TestCeleryRetryDoesNotPrematurelyFail:
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
        """
        模擬 subprocess 第一次失敗、celery 仍在重試（未達 max_retries）。
        sync_log 不應被立刻標記為 failed。
        """
        from tasks import run_ingestion_sync

        sync_log = self._make_sync_log()
        agent = self._make_agent()
        faq = self._make_faq()
        db = self._make_db(sync_log, agent, [faq])

        with (
            patch(self.SESSION_PATCH, return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="boom")
            # apply() 為 EAGER，不會真的 retry，但會丟 Retry exception
            # 我們用 try/except 接住，確認 sync_log 未被寫入 failed
            try:
                run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])
            except Exception:
                pass

        # 在 retry 路徑下（未達 MaxRetries），sync_log.status 不應被設為 'failed'
        # 允許的中間狀態為 'running'（前面 commit 過），但不可為 'failed'
        # 注意：apply() 在 EAGER 模式預設 throw=True，當 task 重新拋出 Retry 例外時，
        # 我們攔截後檢查最終 sync_log.status
        assert sync_log.status != "failed", (
            f"retry 路徑下 sync_log.status 不可立刻被設為 failed，"
            f"實際為 {sync_log.status!r}"
        )

    def test_max_retries_exceeded_writes_failed(self) -> None:
        """
        模擬已達 max_retries：MaxRetriesExceededError 觸發，應寫入 failed。
        以 mock self.retry 直接拋 MaxRetriesExceededError 模擬。
        """
        from celery.exceptions import MaxRetriesExceededError

        from tasks import run_ingestion_sync

        sync_log = self._make_sync_log()
        agent = self._make_agent()
        faq = self._make_faq()
        db = self._make_db(sync_log, agent, [faq])

        with (
            patch(self.SESSION_PATCH, return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("subprocess.run") as mock_run,
            patch.object(
                run_ingestion_sync,
                "retry",
                side_effect=MaxRetriesExceededError(),
            ),
        ):
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="boom")
            run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])

        assert sync_log.status == "failed"
        assert sync_log.finished_at is not None
