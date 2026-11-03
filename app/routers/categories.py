from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Category, User
from ..schemas import CategoryIn, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


def _owned(db: Session, user: User, category_id: int) -> Category:
    cat = db.scalar(select(Category).where(Category.id == category_id, Category.user_id == user.id))
    if not cat:
        raise HTTPException(404, "Category not found")
    return cat


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(Category).where(Category.user_id == user.id).order_by(Category.name)).all()


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(body: CategoryIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cat = Category(user_id=user.id, **body.model_dump())
    db.add(cat)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Category name already exists")
    return cat


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, body: CategoryUpdate, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    cat = _owned(db, user, category_id)
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is None:
        raise HTTPException(422, "name cannot be null")
    for k, v in data.items():
        setattr(cat, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Category name already exists")
    return cat


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.delete(_owned(db, user, category_id))  # transactions keep existing, category becomes NULL
    db.commit()
