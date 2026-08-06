import redis
import json
import uuid
import os
import time
import logging

import chromadb
from langchain_community.embeddings import HuggingFaceEmbeddings
from parsers.pdf import parse_pdf
from parsers.word import parse_word
from parsers.excel import parse_excel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
CHROMA_URL = os.getenv("CHROMA_URL", "http://chroma:8000")
COLLECTION_NAME = "documents"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")

def get_embedding_model():
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": EMBEDDING_DEVICE},
        encode_kwargs={"normalize_embeddings": True},
    )

def get_chroma_collection():
    host, port = CHROMA_URL.replace("http://", "").split(":")
    client = chromadb.HttpClient(host=host, port=int(port))
    return client.get_or_create_collection(COLLECTION_NAME)

def parse_file(filepath: str, filename: str) -> list[dict]:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return parse_pdf(filepath, filename)
    elif ext == ".docx":
        return parse_word(filepath, filename)
    elif ext in (".xlsx", ".xls"):
        return parse_excel(filepath, filename)
    return []

def process_job(job: dict, embedding_model, collection):
    job_id = job["job_id"]
    filename = job["filename"]
    filepath = job["filepath"]

    log.info(f"処理開始: {filename} (job_id={job_id})")

    chunks = parse_file(filepath, filename)
    if not chunks:
        log.warning(f"チャンクが0件: {filename}")
        return

    texts = [c["text"] for c in chunks]
    embeddings = embedding_model.embed_documents(texts)

    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [
        {
            "chunk_id": ids[i],
            "filename": c["filename"],
            "page": str(c["page"]) if c["page"] else "",
            "section": c["section"] or "",
        }
        for i, c in enumerate(chunks)
    ]

    # 同名ファイルが既に登録されていれば旧チャンクを削除（改定版で上書き）
    existing = collection.get(where={"filename": filename})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        log.info(f"旧版を削除: {filename} → {len(existing['ids'])}チャンク")

    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    log.info(f"完了: {filename} → {len(chunks)}チャンク追加")

def main():
    log.info("Workerを起動しています...")
    r = redis.from_url(REDIS_URL)
    embedding_model = get_embedding_model()
    collection = get_chroma_collection()
    log.info("Worker起動完了。キューを監視中...")

    while True:
        # FIFOブロッキング読み取り（タイムアウト5秒）
        item = r.blpop("ingest_queue", timeout=5)
        if item is None:
            continue

        _, raw = item
        job = json.loads(raw)
        job_id = job["job_id"]

        try:
            job["status"] = "processing"
            r.set(f"job:{job_id}", json.dumps(job))

            process_job(job, embedding_model, collection)

            job["status"] = "done"
        except Exception as e:
            log.error(f"エラー: {e}")
            job["status"] = "error"
            job["error"] = str(e)
        finally:
            r.set(f"job:{job_id}", json.dumps(job))

if __name__ == "__main__":
    main()
