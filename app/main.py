import datetime

from fastapi import Depends, FastAPI, HTTPException

from app.auth import require_token
from app.homework import fetch_homework
from app.models import HomeworkResponse

app = FastAPI()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/v1/homework", dependencies=[Depends(require_token)])
async def get_homework(date: str) -> HomeworkResponse:
    try:
        requested = datetime.date.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    try:
        return await fetch_homework(requested)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))