"""
ingest_kb.py：將匯出的 FAQ .txt 向量化並寫入 Qdrant。

支援格式（與 backend/tasks.py 匯出邏輯對齊）：

    [Question]
    問題內容

    [Answer]
    答案內容

    [Question]
    問題內容 2

    [Answer]
    答案內容 2

每筆 FAQ 之間以雙換行（\\n\\n）分隔。內容若含 [Question] / [Answer]
保留字會被改寫為全形字 【Question】 / 【Answer】（規格 §五.4），
解析時還原。

向後相容：仍接受舊版 Q:/A: 格式。

使用方式：
    python ingest_kb.py \
        --source /path/to/faq_export.txt \
        --qdrant-url http://qdrant:6333 \
        --collection agent_<uuid> \
        --doc-id agent_<uuid>_v1
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from tqdm import tqdm

load_dotenv()

# -------------------------
# 常數
# -------------------------
EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 200


# -------------------------
# deterministic ID
# -------------------------
def generate_qa_id(source: str, question: str, _answer: str) -> str:
    raw = f"{source}|{question}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, raw))


# -------------------------
# 解析 .txt
# -------------------------
_BLOCK_RE = re.compile(r"\[Question\]\s*\n(.*?)\n\s*\n\[Answer\]\s*\n(.*)", re.S)
_LEGACY_RE = re.compile(r'Q:(.*?)\n"?A:(.*?)(?=\nQ:|\Z)', re.S)


def _restore_reserved(text: str) -> str:
    """還原全形保留字回半形。"""
    return text.replace("【Question】", "[Question]").replace("【Answer】", "[Answer]")


def parse_kb(path: str | Path) -> list[dict]:
    """
    解析匯出 .txt。優先嘗試 [Question]/[Answer] 區塊格式，
    失敗則退回舊版 Q:/A: 格式。
    """
    text = Path(path).read_text(encoding="utf-8")
    records: list[dict] = []

    # 將 "\n\n[Question]" 作為 FAQ 區塊分隔點
    parts = text.split("\n\n[Question]")
    blocks: list[str] = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        if i == 0:
            # 第一塊可能已含 [Question]，也可能沒有
            if not part.startswith("[Question]"):
                # 整檔沒有 [Question] 標頭：跳到 legacy 解析
                blocks = []
                break
            blocks.append(part)
        else:
            blocks.append("[Question]\n" + part.lstrip("\n"))

    for block in blocks:
        m = _BLOCK_RE.match(block)
        if not m:
            continue
        q = _restore_reserved(m.group(1).strip())
        a = _restore_reserved(m.group(2).strip())
        records.append(
            {
                "question": q,
                "answer": a,
                "text": f"問題：{q}\n答案：{a}",
            }
        )

    if records:
        return records

    # 向後相容：Q:/A: 格式
    for q, a in _LEGACY_RE.findall(text):
        q = q.strip()
        a = a.strip()
        records.append(
            {
                "question": q,
                "answer": a,
                "text": f"問題：{q}\n答案：{a}",
            }
        )
    return records


# -------------------------
# Embedding
# -------------------------
def embed(client: OpenAI, texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def get_embedding_dim(client: OpenAI) -> int:
    return len(embed(client, ["dimension check"])[0])


# -------------------------
# 建立 / 清空 / 檢查 collection
# -------------------------
def init_collection(
    qdrant: QdrantClient, openai_client: OpenAI, collection_name: str, *, clear: bool = False
) -> None:
    """
    建立或驗證 Qdrant collection。
    clear=True 時先刪除現有 collection 再重建（確保已刪除的 FAQ 向量不殘留），
    兩個操作共用同一次 get_collections() 呼叫。
    """
    dim = get_embedding_dim(openai_client)
    existing = {c.name for c in qdrant.get_collections().collections}

    if collection_name in existing:
        if clear:
            qdrant.delete_collection(collection_name)
            print(f"已清空 Qdrant collection: {collection_name}")
        else:
            existing_dim = qdrant.get_collection(collection_name).config.params.vectors.size
            if existing_dim != dim:
                raise RuntimeError(
                    f"Embedding dim mismatch: collection={existing_dim}, model={dim}"
                )
            return

    qdrant.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )


# -------------------------
# 上傳（Upsert）
# -------------------------
def upload(
    qdrant: QdrantClient,
    openai_client: OpenAI,
    records: list[dict],
    *,
    collection_name: str,
    doc_id: str,
    source: str,
) -> None:
    for i in tqdm(range(0, len(records), BATCH_SIZE)):
        batch = records[i : i + BATCH_SIZE]
        vectors = embed(openai_client, [r["text"] for r in batch])

        points = []
        for r, v in zip(batch, vectors):
            point_id = generate_qa_id(
                source=source,
                question=r["question"],
                _answer=r["answer"],
            )
            points.append(
                PointStruct(
                    id=point_id,
                    vector=v,
                    payload={
                        "page_content": r["question"],
                        "metadata": {
                            "type": "faq",
                            "doc_id": doc_id,
                            "source": source,
                            "answer": r["answer"],
                        },
                    },
                )
            )

        qdrant.upsert(collection_name=collection_name, points=points)


# -------------------------
# CLI
# -------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="將 FAQ .txt 向量化並寫入 Qdrant。"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="匯出 .txt 路徑（[Question]/[Answer] 格式）",
    )
    parser.add_argument(
        "--qdrant-url",
        default=os.environ.get("QDRANT_URL"),
        help="Qdrant URL（預設讀環境變數 QDRANT_URL）",
    )
    parser.add_argument(
        "--collection",
        default="rasa_demo",
        help="Qdrant collection 名稱",
    )
    parser.add_argument(
        "--doc-id",
        default="knowledgebase_v1",
        help="metadata.doc_id",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        default=False,
        help="同步前清空 Qdrant collection，確保已刪除的 FAQ 向量不殘留（預設 False）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if not args.qdrant_url:
        raise RuntimeError(
            "QDRANT_URL 未設定：請以 --qdrant-url 參數或環境變數 QDRANT_URL 提供"
        )

    source_path = Path(args.source)
    if not source_path.exists():
        raise RuntimeError(f"來源檔不存在：{source_path}")

    openai_client = OpenAI()
    qdrant = QdrantClient(url=args.qdrant_url)

    records = parse_kb(source_path)
    print(f"載入 {len(records)} 筆 Q&A（來源：{source_path}）")

    if not records:
        print("無資料可上傳，結束。")
        return 0

    init_collection(qdrant, openai_client, args.collection, clear=args.clear)
    upload(
        qdrant,
        openai_client,
        records,
        collection_name=args.collection,
        doc_id=args.doc_id,
        source=str(source_path),
    )

    print(f"完成向量化並寫入 Qdrant collection={args.collection}（Upsert / 可重跑）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
