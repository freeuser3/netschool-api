import hmac

from fastapi import Header, HTTPException

from app.config import get_api_token


def require_token(authorization: str | None = Header(default=None)) -> None:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, get_api_token()):
        raise HTTPException(status_code=401, detail="Invalid token")
