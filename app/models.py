from datetime import date, datetime, timezone

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_category_user_name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(40))
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    monthly_budget_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("type IN ('income','expense')", name="ck_tx_type"),
        CheckConstraint("amount_cents > 0", name="ck_tx_amount_positive"),
        Index("ix_tx_user_date", "user_id", "occurred_on"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(String(7))
    amount_cents: Mapped[int] = mapped_column(Integer)  # money is always integer cents
    occurred_on: Mapped[date] = mapped_column(Date)
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Goal(Base):
    __tablename__ = "goals"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    target_cents: Mapped[int] = mapped_column(Integer)
    saved_cents: Mapped[int] = mapped_column(Integer, default=0)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
