from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
MAX_CENTS = 10**12


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth
class RegisterIn(BaseModel):
    email: str = Field(pattern=EMAIL_RE, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _lower(cls, v):
        return v.lower()


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class UserOut(ORM):
    id: int
    email: str


class AuthOut(BaseModel):
    user: UserOut
    access_token: str
    token_type: str = "bearer"


# ---- categories
class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    monthly_budget_cents: int | None = Field(None, ge=0, le=MAX_CENTS)


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=40)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    monthly_budget_cents: int | None = Field(None, ge=0, le=MAX_CENTS)


class CategoryOut(ORM, CategoryIn):
    id: int


# ---- transactions
TxType = Literal["income", "expense"]


class TransactionIn(BaseModel):
    type: TxType
    amount_cents: int = Field(gt=0, le=MAX_CENTS)
    occurred_on: date
    category_id: int | None = None
    note: str = Field("", max_length=200)


class TransactionUpdate(BaseModel):
    type: TxType | None = None
    amount_cents: int | None = Field(None, gt=0, le=MAX_CENTS)
    occurred_on: date | None = None
    category_id: int | None = None
    note: str | None = Field(None, max_length=200)


class TransactionOut(ORM):
    id: int
    type: TxType
    amount_cents: int
    occurred_on: date
    category_id: int | None
    note: str
    created_at: datetime


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    limit: int
    offset: int


# ---- goals
class GoalIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    target_cents: int = Field(gt=0, le=MAX_CENTS)
    deadline: date | None = None


class GoalUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=60)
    target_cents: int | None = Field(None, gt=0, le=MAX_CENTS)
    deadline: date | None = None


class Contribution(BaseModel):
    amount_cents: int = Field(gt=0, le=MAX_CENTS)


class GoalOut(ORM):
    id: int
    name: str
    target_cents: int
    saved_cents: int
    deadline: date | None
    progress: float = 0.0


# ---- reports
class SummaryOut(BaseModel):
    month: str
    income_cents: int
    expense_cents: int
    net_cents: int
    savings_rate: float | None
    transaction_count: int
    balance_cents: int  # all-time income minus expenses


class CategoryTotal(BaseModel):
    category_id: int | None
    name: str
    color: str | None
    total_cents: int
    share: float
    budget_cents: int | None


class MonthFlow(BaseModel):
    month: str
    income_cents: int
    expense_cents: int
    net_cents: int
