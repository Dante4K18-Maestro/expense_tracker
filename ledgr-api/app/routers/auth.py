from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import ACCESS_TOKEN_MINUTES, COOKIE_NAME, COOKIE_SECURE
from ..database import get_db
from ..deps import get_current_user
from ..models import Category, User
from ..schemas import AuthOut, LoginIn, RegisterIn, UserOut
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

_DUMMY_HASH = hash_password("not-a-real-password")  # equalises timing for unknown emails
_DEFAULTS = [("Housing", "#C8F560"), ("Food", "#F2F4EF"), ("Transport", "#8EA2FF"), ("Other", "#4A5058")]


def _issue(response: Response, user: User) -> AuthOut:
    token = create_token(user.id)
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=COOKIE_SECURE, samesite="lax",
                        max_age=ACCESS_TOKEN_MINUTES * 60, path="/")
    return AuthOut(user=UserOut.model_validate(user), access_token=token)


@router.post("/register", response_model=AuthOut, status_code=201)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already registered")
    db.add_all(Category(user_id=user.id, name=n, color=c) for n, c in _DEFAULTS)
    db.commit()
    return _issue(response, user)


@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok:
        raise HTTPException(401, "Incorrect email or password")
    return _issue(response, user)


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
