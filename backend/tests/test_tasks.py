"""
Celery 任務測試：Mock DB 驗證 txt 格式、sync_logs 狀態、保留字符替換。

SessionLocal 在 tasks.py 中是函式內 lazy import，
patch 路徑必須指向 api.database.session.SessionLocal。
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, mock_open, patch


from tests.conftest import AGENT_ID


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
        from tasks import run_ingestion_sync

        sync_log = self._make_sync_log()
        agent = self._make_agent()
        faq = self._make_faq_item()
        db = self._make_db(sync_log, agent, [faq])

        with (
            patch(self.SESSION_PATCH, return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("os.path.exists", return_value=True),
            patch("shutil.copy2"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])

        assert sync_log.status == "completed"

    def test_sync_log_failed_when_agent_not_found(self) -> None:
        from tasks import run_ingestion_sync

        sync_log = self._make_sync_log()
        db = self._make_db(sync_log, None, [])

        with patch(self.SESSION_PATCH, return_value=db):
            run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])

        assert sync_log.status == "failed"

    def test_items_status_updated_to_synced(self) -> None:
        from tasks import run_ingestion_sync

        sync_log = self._make_sync_log()
        agent = self._make_agent()
        faq = self._make_faq_item()
        db = self._make_db(sync_log, agent, [faq])

        with (
            patch(self.SESSION_PATCH, return_value=db),
            patch("builtins.open", mock_open()),
            patch("os.makedirs"),
            patch("os.path.exists", return_value=True),
            patch("shutil.copy2"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            run_ingestion_sync.apply(args=[str(AGENT_ID), str(sync_log.id)])

        assert faq.status == "synced"
