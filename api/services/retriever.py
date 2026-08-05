import chromadb
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import os

CHROMA_URL = os.getenv("CHROMA_URL", "http://chroma:8000")
COLLECTION_NAME = "documents"
SIMILARITY_THRESHOLD = 0.7  # これ以下のコサイン類似度は除外

_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embedding_model

def get_vectorstore():
    host, port = CHROMA_URL.replace("http://", "").split(":")
    client = chromadb.HttpClient(host=host, port=int(port))
    return Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=get_embedding_model(),
    )

def retrieve(query: str, k: int = 5):
    """MMR検索 + コサイン類似度フィルタリング"""
    vectorstore = get_vectorstore()

    # MMR（多様性確保）で候補を広めに取得
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": k * 3,   # MMRの候補プール
            "lambda_mult": 0.7, # 1=関連性重視 0=多様性重視
        },
    )
    docs = retriever.invoke(query)

    # コサイン類似度でフィルタリング
    docs_with_scores = vectorstore.similarity_search_with_relevance_scores(
        query, k=k * 3
    )
    high_score_ids = {
        doc.metadata.get("chunk_id")
        for doc, score in docs_with_scores
        if score >= SIMILARITY_THRESHOLD
    }

    filtered = [
        doc for doc in docs
        if doc.metadata.get("chunk_id") in high_score_ids
    ]

    return filtered if filtered else []
