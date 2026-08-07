import chromadb
import math
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder
import os

CHROMA_URL = os.getenv("CHROMA_URL", "http://chroma:8000")
COLLECTION_NAME = "documents"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
RERANKER_DEVICE = os.getenv("RERANKER_DEVICE", "cpu")
RERANK_THRESHOLD = 0.3  # シグモイド後（0〜1）のスコア、これ未満は除外
CANDIDATE_POOL_MULTIPLIER = 4  # 一次検索でkの何倍の候補を広めに取るか

_embedding_model = None
_reranker = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": EMBEDDING_DEVICE},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embedding_model

def get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANKER_MODEL, device=RERANKER_DEVICE)
    return _reranker

def get_vectorstore():
    host, port = CHROMA_URL.replace("http://", "").split(":")
    client = chromadb.HttpClient(host=host, port=int(port))
    return Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=get_embedding_model(),
    )

def retrieve(query: str, k: int = 5):
    """ベクトル検索で候補を広めに取得し、Cross-Encoderでリランキングして上位k件に絞る"""
    vectorstore = get_vectorstore()
    pool_size = k * CANDIDATE_POOL_MULTIPLIER

    candidates = vectorstore.similarity_search(query, k=pool_size)
    if not candidates:
        return []

    pairs = [[query, doc.page_content] for doc in candidates]
    raw_scores = get_reranker().predict(pairs)
    scores = [1 / (1 + math.exp(-s)) for s in raw_scores]  # シグモイドで0〜1に正規化

    ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)

    return [doc for doc, score in ranked[:k] if score >= RERANK_THRESHOLD]
