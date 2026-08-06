from fastapi import FastAPI
from routers import query, ingest, documents

app = FastAPI(title="RAG API", version="1.0.0")

app.include_router(query.router)
app.include_router(ingest.router)
app.include_router(documents.router)

@app.get("/health")
def health():
    return {"status": "ok"}
