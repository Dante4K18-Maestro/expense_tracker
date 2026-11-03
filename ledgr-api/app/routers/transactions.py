from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Category, Transaction, User
from ..schemas import TransactionIn, TransactionOut, TransactionPage, TransactionUpdate, TxType

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _check_category(db: Session, user: User, category_id: int | None):
    if category_id is None:
        return
    if not db.scalar(select(Category.id).where(Category.id == category_id, Category.user_id == user.id)):
        raise HTTPException(422, "Unknown category")


def _owned(db: Session, user: User, tx_id: int) -> Transaction:
    tx = db.scalar(select(Transaction).where(Transaction.id == tx_id, Transaction.user_id == user.id))
    if not tx:
        raise HTTPException(404, "Transaction not found")
    return tx


@router.get("", response_model=TransactionPage)
def list_transactions(
    type_: TxType | None = Query(None, alias="type"),
    category_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Transaction).where(Transaction.user_id == user.id)
    if type_:
        stmt = stmt.where(Transaction.type == type_)
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    if date_from:
        stmt = stmt.where(Transaction.occurred_on >= date_from)
    if date_to:
        stmt = stmt.where(Transaction.occurred_on <= date_to)
    if q:
        stmt = stmt.where(func.lower(Transaction.note).contains(q.lower(), autoescape=True))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Transaction.occurred_on.desc(), Transaction.id.desc())
                       .limit(limit).offset(offset)).all()
    return TransactionPage(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(body: TransactionIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _check_category(db, user, body.category_id)
    tx = Transaction(user_id=user.id, **body.model_dump())
    db.add(tx)
    db.commit()
    return tx


@router.get("/{tx_id}", response_model=TransactionOut)
def get_transaction(tx_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _owned(db, user, tx_id)


@router.patch("/{tx_id}", response_model=TransactionOut)
def update_transaction(tx_id: int, body: TransactionUpdate, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    tx = _owned(db, user, tx_id)
    data = body.model_dump(exclude_unset=True)
    for field in ("type", "amount_cents", "occurred_on", "note"):
        if field in data and data[field] is None:
            raise HTTPException(422, f"{field} cannot be null")
    if "category_id" in data:
        _check_category(db, user, data["category_id"])
    for k, v in data.items():
        setattr(tx, k, v)
    db.commit()
    return tx


@router.delete("/{tx_id}", status_code=204)
def delete_transaction(tx_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.delete(_owned(db, user, tx_id))
    db.commit()
