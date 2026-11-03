import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .config import COOKIE_NAME
from .database import get_db
from .models import User
from .security import decode_token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    header = request.headers.get("authorization", "")
    if not token and header.lower().startswith("bearer "):
        token = header[7:].strip()
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        user_id = int(decode_token(token)["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, "Invalid or expired token")
    return user
