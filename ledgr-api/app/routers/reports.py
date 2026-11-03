import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import case, extract, func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Category, Transaction as T, User
from ..schemas import CategoryTotal, MonthFlow, SummaryOut

router = APIRouter(prefix="/reports", tags=["reports"])
MonthParam = Query(None, pattern=r"^(19|20)\d{2}-(0[1-9]|1[0-2])$", description="YYYY-MM, defaults to current month")

INCOME = func.coalesce(func.sum(case((T.type == "income", T.amount_cents), else_=0)), 0)
EXPENSE = func.coalesce(func.sum(case((T.type == "expense", T.amount_cents), else_=0)), 0)


def _bounds(month: str | None) -> tuple[str, date, date]:
    if month:
        y, m = int(month[:4]), int(month[5:])
    else:
        today = date.today()
        y, m = today.year, today.month
    end = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    return f"{y:04d}-{m:02d}", date(y, m, 1), end


@router.get("/summary", response_model=SummaryOut)
def summary(month: str | None = MonthParam, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    label, start, end = _bounds(month)
    inc, exp, count = db.execute(
        select(INCOME, EXPENSE, func.count(T.id)).where(T.user_id == user.id, T.occurred_on >= start, T.occurred_on < end)
    ).one()
    all_inc, all_exp = db.execute(select(INCOME, EXPENSE).where(T.user_id == user.id)).one()
    inc, exp = int(inc), int(exp)
    return SummaryOut(month=label, income_cents=inc, expense_cents=exp, net_cents=inc - exp,
                      savings_rate=round((inc - exp) / inc, 4) if inc else None,
                      transaction_count=count, balance_cents=int(all_inc) - int(all_exp))


@router.get("/by-category", response_model=list[CategoryTotal])
def by_category(month: str | None = MonthParam, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    _, start, end = _bounds(month)
    total = func.sum(T.amount_cents)
    rows = db.execute(
        select(Category.id, Category.name, Category.color, Category.monthly_budget_cents, total)
        .select_from(T).outerjoin(Category, T.category_id == Category.id)
        .where(T.user_id == user.id, T.type == "expense", T.occurred_on >= start, T.occurred_on < end)
        .group_by(Category.id, Category.name, Category.color, Category.monthly_budget_cents)
        .order_by(total.desc())
    ).all()
    grand = sum(int(r[4]) for r in rows) or 1
    return [CategoryTotal(category_id=r[0], name=r[1] or "Uncategorized", color=r[2], total_cents=int(r[4]),
                          share=round(int(r[4]) / grand, 4), budget_cents=r[3]) for r in rows]


@router.get("/cash-flow", response_model=list[MonthFlow])
def cash_flow(months: int = Query(6, ge=1, le=24), db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    today = date.today()
    y, m, seq = today.year, today.month, []
    for _ in range(months):
        seq.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    seq.reverse()
    yr, mo = extract("year", T.occurred_on), extract("month", T.occurred_on)
    rows = db.execute(
        select(yr.label("y"), mo.label("m"), INCOME, EXPENSE)
        .where(T.user_id == user.id, T.occurred_on >= date(*seq[0], 1)).group_by(yr, mo)
    ).all()
    found = {(int(r[0]), int(r[1])): (int(r[2]), int(r[3])) for r in rows}
    out = []
    for ym in seq:
        i, e = found.get(ym, (0, 0))
        out.append(MonthFlow(month=f"{ym[0]:04d}-{ym[1]:02d}", income_cents=i, expense_cents=e, net_cents=i - e))
    return out


def _safe(value) -> str:
    s = str(value or "")
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s  # block CSV/formula injection


@router.get("/export.csv")
def export_csv(month: str | None = MonthParam, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    stmt = (select(T.occurred_on, T.type, T.amount_cents, Category.name, T.note)
            .outerjoin(Category, T.category_id == Category.id).where(T.user_id == user.id))
    if month:
        _, start, end = _bounds(month)
        stmt = stmt.where(T.occurred_on >= start, T.occurred_on < end)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "type", "amount", "category", "note"])
    for d, t, cents, cat, note in db.execute(stmt.order_by(T.occurred_on, T.id)):
        w.writerow([d.isoformat(), t, f"{cents // 100}.{cents % 100:02d}", _safe(cat), _safe(note)])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="ledgr-export.csv"'})
