from fastapi import APIRouter
from pydantic import BaseModel
from services.llm import query as rag_query

router = APIRouter()

class QueryRequest(BaseModel):
    question: str

@router.post("/query")
def query(req: QueryRequest):
    result = rag_query(req.question)
    return result
