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
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchAny,
    PointStruct,
    VectorParams,
)
from tqdm import tqdm

load_dotenv()

# -------------------------
# 常數
# -------------------------
BATCH_SIZE = 200
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def make_openai_client(
    provider: str, base_url: str | None, api_key: str | None
) -> OpenAI:
    """根據 provider 決定 OpenAI client 連線目標。

    - openai：用 OpenAI 官方端點 + OPENAI_API_KEY
    - local ：用使用者指定的 base_url + api_key（OpenAI-compatible 介面）
    """
    p = (provider or "openai").lower()
    if p == "local":
        if not base_url:
            raise RuntimeError(
                "provider=local 但未提供 --base-url / LOCAL_EMBEDDING_BASE_URL"
            )
        # 多數地端 server（LM Studio / Ollama / TEI）不檢查 api_key，但 OpenAI SDK
        # 要求非空字串，因此預設 'any' 作為 placeholder。
        return OpenAI(base_url=base_url, api_key=api_key or "any")
    if p != "openai":
        raise RuntimeError(f"未支援的 embedding provider：{provider!r}（限 openai|local）")
    return OpenAI()  # 走 OPENAI_API_KEY env


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
_CAT_BLOCK_RE = re.compile(
    r"\[Category\]\s*\n(.*?)\n\s*\n\[Question\]\s*\n(.*?)\n\s*\n\[Answer\]\s*\n(.*)",
    re.S,
)


def _restore_reserved(text: str) -> str:
    """還原全形保留字回半形。"""
    return text.replace("【Question】", "[Question]").replace("【Answer】", "[Answer]")


def parse_kb(path: str | Path) -> list[dict]:
    """
    解析匯出 .txt。
    優先嘗試含 [Category] 的新格式，其次 [Question]/[Answer] 舊格式，
    最後退回舊版 Q:/A: 格式。
    回傳 records，每筆含 question / answer / text，新格式另含 category_path。
    """
    text = Path(path).read_text(encoding="utf-8")
    records: list[dict] = []

    # ── 優先：含 [Category] 的新格式 ──────────────────────────────────
    if "[Category]" in text:
        parts = text.split("\n\n[Category]")
        blocks: list[str] = []
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            if i == 0:
                if not part.startswith("[Category]"):
                    blocks = []
                    break
                blocks.append(part)
            else:
                blocks.append("[Category]\n" + part.lstrip("\n"))

        for block in blocks:
            m = _CAT_BLOCK_RE.match(block)
            if not m:
                continue
            category_path = m.group(1).strip()
            q = _restore_reserved(m.group(2).strip())
            a = _restore_reserved(m.group(3).strip())
            records.append(
                {
                    "question": q,
                    "answer": a,
                    "text": f"問題：{q}\n答案：{a}",
                    "category_path": category_path,
                }
            )
        if records:
            return records

    # ── 次選：[Question]/[Answer] 無 [Category]（全局同步格式）──────────
    parts = text.split("\n\n[Question]")
    blocks = []
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        if i == 0:
            if not part.startswith("[Question]"):
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
        records.append({"question": q, "answer": a, "text": f"問題：{q}\n答案：{a}"})

    if records:
        return records

    # ── 向後相容：Q:/A: 格式 ─────────────────────────────────────────────
    for q, a in _LEGACY_RE.findall(text):
        q = q.strip()
        a = a.strip()
        records.append({"question": q, "answer": a, "text": f"問題：{q}\n答案：{a}"})
    return records


# -------------------------
# Embedding
# -------------------------
def embed(client: OpenAI, model: str, texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]


def get_embedding_dim(client: OpenAI, model: str) -> int:
    return len(embed(client, model, ["dimension check"])[0])


# -------------------------
# 建立 / 清空 / 檢查 collection
# -------------------------
def init_collection(
    qdrant: QdrantClient,
    openai_client: OpenAI,
    collection_name: str,
    *,
    model: str,
    clear: bool = False,
) -> None:
    """
    建立或驗證 Qdrant collection。
    clear=True 時先刪除現有 collection 再重建（確保已刪除的 FAQ 向量不殘留），
    兩個操作共用同一次 get_collections() 呼叫。
    """
    dim = get_embedding_dim(openai_client, model)
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
# 精準刪除向量（分類同步用）
# -------------------------
def delete_by_category_paths(
    qdrant: QdrantClient, collection_name: str, category_paths: list[str]
) -> None:
    """
    刪除 Qdrant collection 中 metadata.category_path 符合任一指定路徑的向量。
    collection 不存在時靜默跳過。
    """
    if not category_paths:
        return
    existing = {c.name for c in qdrant.get_collections().collections}
    if collection_name not in existing:
        print(f"Qdrant collection {collection_name!r} 不存在，略過刪除。")
        return
    qdrant.delete(
        collection_name=collection_name,
        points_selector=FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(
                        key="metadata.category_path",
                        match=MatchAny(any=category_paths),
                    )
                ]
            )
        ),
    )
    print(f"已刪除 category_path 符合 {category_paths} 的向量")


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
    model: str,
) -> None:
    for i in tqdm(range(0, len(records), BATCH_SIZE)):
        batch = records[i : i + BATCH_SIZE]
        vectors = embed(openai_client, model, [r["text"] for r in batch])

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
                            **( {"category_path": r["category_path"]} if r.get("category_path") else {} ),
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
    parser.add_argument(
        "--delete-category-paths",
        default="",
        dest="delete_category_paths",
        help="逗號分隔的 category_path 清單，同步前精準刪除對應向量（分類同步用）",
    )
    # ── Embedding provider config（per-agent 從 backend 傳入；env 為 fallback） ──
    parser.add_argument(
        "--provider",
        default=os.environ.get("EMBEDDING_PROVIDER", "openai"),
        choices=["openai", "local"],
        help="embedding provider（openai 雲端 / local 地端 OpenAI-compatible）",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        help="embedding model 名稱（e.g. text-embedding-3-small / bge-m3-q8_0）",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LOCAL_EMBEDDING_BASE_URL"),
        dest="base_url",
        help="provider=local 時的 OpenAI-compatible base URL",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("LOCAL_EMBEDDING_API_KEY"),
        dest="api_key",
        help="provider=local 時的 API key（多數地端 server 不檢查，仍需非空）",
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

    openai_client = make_openai_client(args.provider, args.base_url, args.api_key)
    qdrant = QdrantClient(url=args.qdrant_url)
    print(f"Embedding provider={args.provider} model={args.model}")

    records = parse_kb(source_path)
    print(f"載入 {len(records)} 筆 Q&A（來源：{source_path}）")

    # 計算 records 中的 category_path（若有）
    unique_paths_from_records = list(
        {r["category_path"] for r in records if r.get("category_path")}
    )

    # 決定刪除策略
    explicit_paths = [
        p.strip()
        for p in args.delete_category_paths.split(",")
        if p.strip()
    ]

    if args.clear:
        # 全局同步：刪整個 collection 再重建
        init_collection(qdrant, openai_client, args.collection, model=args.model, clear=True)
    elif explicit_paths:
        # 分類同步（Celery task 明確傳入）：確保 collection 存在 + 精準刪除
        init_collection(qdrant, openai_client, args.collection, model=args.model, clear=False)
        delete_by_category_paths(qdrant, args.collection, explicit_paths)
    elif unique_paths_from_records:
        # 從 records 自動偵測（手動執行新格式 txt 時使用）
        init_collection(qdrant, openai_client, args.collection, model=args.model, clear=False)
        delete_by_category_paths(qdrant, args.collection, unique_paths_from_records)
    else:
        # 無 --clear 也無 category_path：確保 collection 存在即可
        init_collection(qdrant, openai_client, args.collection, model=args.model, clear=False)

    if records:
        upload(
            qdrant,
            openai_client,
            records,
            collection_name=args.collection,
            doc_id=args.doc_id,
            source=str(source_path),
            model=args.model,
        )
        print(f"完成向量化並寫入 Qdrant collection={args.collection}（Upsert / 可重跑）")
    else:
        print("無資料可上傳，結束。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
