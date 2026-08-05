from fastapi import APIRouter
import chromadb
import os

router = APIRouter()
CHROMA_URL = os.getenv("CHROMA_URL", "http://chroma:8000")

@router.get("/documents")
def list_documents():
    host, port = CHROMA_URL.replace("http://", "").split(":")
    client = chromadb.HttpClient(host=host, port=int(port))
    try:
        collection = client.get_collection("documents")
        results = collection.get(include=["metadatas"])
        filenames = list({m.get("filename") for m in results["metadatas"] if m.get("filename")})
        return {"documents": sorted(filenames)}
    except Exception:
        return {"documents": []}
