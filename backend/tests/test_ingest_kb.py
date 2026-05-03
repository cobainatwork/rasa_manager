"""
ingest_kb.py 解析器單元測試。

只測 parse_kb 與全形保留字還原邏輯，不依賴 OpenAI / Qdrant。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ingest_kb.py 位於專案根目錄
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))

# 缺少 openai/qdrant_client/tqdm/dotenv 任一套件時，整個模組無法載入；
# 若本機環境未安裝（例如 ruff/mypy 容器），整個檔案 skip。
ingest_kb = pytest.importorskip("ingest_kb")


class TestParseKb:
    def test_single_block(self, tmp_path: Path) -> None:
        f = tmp_path / "kb.txt"
        f.write_text("[Question]\n什麼是 AI？\n\n[Answer]\n人工智慧。", encoding="utf-8")

        records = ingest_kb.parse_kb(f)
        assert len(records) == 1
        assert records[0]["question"] == "什麼是 AI？"
        assert records[0]["answer"] == "人工智慧。"
        assert records[0]["text"] == "問題：什麼是 AI？\n答案：人工智慧。"

    def test_multiple_blocks(self, tmp_path: Path) -> None:
        f = tmp_path / "kb.txt"
        content = (
            "[Question]\nQ1\n\n[Answer]\nA1"
            "\n\n"
            "[Question]\nQ2\n\n[Answer]\nA2"
        )
        f.write_text(content, encoding="utf-8")

        records = ingest_kb.parse_kb(f)
        assert len(records) == 2
        assert records[0]["question"] == "Q1"
        assert records[0]["answer"] == "A1"
        assert records[1]["question"] == "Q2"
        assert records[1]["answer"] == "A2"

    def test_fullwidth_reserved_chars_restored(self, tmp_path: Path) -> None:
        """匯出時 [Question]→【Question】，解析時要還原回來。"""
        f = tmp_path / "kb.txt"
        # 模擬 backend/tasks.py 匯出邏輯：內含保留字會被改寫
        f.write_text(
            "[Question]\n關於【Question】這個標題\n\n[Answer]\n內含【Answer】說明",
            encoding="utf-8",
        )

        records = ingest_kb.parse_kb(f)
        assert len(records) == 1
        assert records[0]["question"] == "關於[Question]這個標題"
        assert records[0]["answer"] == "內含[Answer]說明"

    def test_legacy_q_a_format_backward_compat(self, tmp_path: Path) -> None:
        f = tmp_path / "kb.txt"
        f.write_text("Q:舊格式問題\nA:舊格式答案\nQ:第二題\nA:第二答", encoding="utf-8")

        records = ingest_kb.parse_kb(f)
        assert len(records) == 2
        assert records[0]["question"] == "舊格式問題"
        assert records[0]["answer"] == "舊格式答案"

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "kb.txt"
        f.write_text("", encoding="utf-8")
        assert ingest_kb.parse_kb(f) == []


class TestGenerateQaId:
    def test_deterministic(self) -> None:
        a = ingest_kb.generate_qa_id("src.txt", "Q", "A")
        b = ingest_kb.generate_qa_id("src.txt", "Q", "A")
        assert a == b

    def test_different_question_different_id(self) -> None:
        a = ingest_kb.generate_qa_id("src.txt", "Q1", "A")
        b = ingest_kb.generate_qa_id("src.txt", "Q2", "A")
        assert a != b
