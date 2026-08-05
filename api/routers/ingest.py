from fastapi import APIRouter, UploadFile, File, HTTPException
import redis
import json
import uuid
import os
import shutil

router = APIRouter()
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/uploads")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

def get_redis():
    return redis.from_url(REDIS_URL)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls"}

@router.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"非対応のファイル形式です: {ext}")

    job_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{job_id}{ext}")

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    job = {
        "job_id": job_id,
        "filename": file.filename,
        "filepath": save_path,
        "status": "queued",
    }
    r = get_redis()
    r.rpush("ingest_queue", json.dumps(job))
    r.set(f"job:{job_id}", json.dumps(job))

    return {"job_id": job_id, "status": "queued", "filename": file.filename}

@router.get("/status/{job_id}")
def status(job_id: str):
    r = get_redis()
    raw = r.get(f"job:{job_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    return json.loads(raw)
