import re
import uuid
from tqdm import tqdm
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# -------------------------
# 設定
# -------------------------
COLLECTION_NAME = "rasa_demo"
EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 200
DOC_ID = "knowledgebase_v1"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
SOURCE_FILE = DATA_DIR / "Contract_Modification_POC.txt"

# -------------------------
# Client
# -------------------------
openai = OpenAI()
qdrant = QdrantClient(url="http://10.2.66.88:6333")

# -------------------------
# deterministic ID
# -------------------------
def generate_qa_id(source: str, question: str, answer: str) -> str:
    raw = f"{source}|{question}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, raw))

# -------------------------
# 解析 knowledgebase.txt
# -------------------------
def parse_kb(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    pattern = re.compile(r'Q:(.*?)\n"?A:(.*?)(?=\nQ:|\Z)', re.S)
    matches = pattern.findall(text)

    records = []
    for q, a in matches:
        q = q.strip()
        a = a.strip()
        records.append({
            "question": q,
            "answer": a,
            "text": f"問題：{q}\n答案：{a}"
        })
    return records

# -------------------------
# Embedding
# -------------------------
def embed(texts):
    resp = openai.embeddings.create(
        model=EMBED_MODEL,
        input=texts
    )
    return [d.embedding for d in resp.data]

def get_embedding_dim():
    return len(embed(["dimension check"])[0])

# -------------------------
# 建立 / 檢查 collection
# -------------------------
def init_collection():
    dim = get_embedding_dim()
    collections = [c.name for c in qdrant.get_collections().collections]

    if COLLECTION_NAME not in collections:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=dim,
                distance=Distance.COSINE
            )
        )
    else:
        info = qdrant.get_collection(COLLECTION_NAME)
        existing_dim = info.config.params.vectors.size
        if existing_dim != dim:
            raise RuntimeError(
                f"Embedding dim mismatch: collection={existing_dim}, model={dim}"
            )

# -------------------------
# 上傳（Upsert）
# -------------------------
def upload(records):
    for i in tqdm(range(0, len(records), BATCH_SIZE)):
        batch = records[i:i + BATCH_SIZE]
        vectors = embed([r["text"] for r in batch])

        points = []
        for r, v in zip(batch, vectors):
            point_id = generate_qa_id(
                source=SOURCE_FILE,
                question=r["question"],
                answer=r["answer"]
            )

            points.append(
                PointStruct(
                    id=point_id,
                    vector=v,
                    payload={
                        "page_content": r["question"],
                        "metadata": {
                            "type": "faq",
                            "doc_id": DOC_ID,
                            "source": SOURCE_FILE,
                            "answer": r["answer"]
                        }
                    }
                )
            )

        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    records = parse_kb(SOURCE_FILE)
    print(f"載入 {len(records)} 筆 Q&A")

    init_collection()
    upload(records)

    print("完成向量化並寫入 Qdrant（Upsert / 可重跑）")
