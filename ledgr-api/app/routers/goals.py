from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Goal, User
from ..schemas import Contribution, GoalIn, GoalOut, GoalUpdate

router = APIRouter(prefix="/goals", tags=["goals"])


def _out(g: Goal) -> GoalOut:
    out = GoalOut.model_validate(g)
    out.progress = round(min(g.saved_cents / g.target_cents, 1.0), 4) if g.target_cents else 0.0
    return out


def _owned(db: Session, user: User, goal_id: int) -> Goal:
    g = db.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
    if not g:
        raise HTTPException(404, "Goal not found")
    return g


@router.get("", response_model=list[GoalOut])
def list_goals(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_out(g) for g in db.scalars(select(Goal).where(Goal.user_id == user.id).order_by(Goal.id))]


@router.post("", response_model=GoalOut, status_code=201)
def create_goal(body: GoalIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = Goal(user_id=user.id, saved_cents=0, **body.model_dump())
    db.add(g)
    db.commit()
    return _out(g)


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, body: GoalUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = _owned(db, user, goal_id)
    data = body.model_dump(exclude_unset=True)
    for field in ("name", "target_cents"):
        if field in data and data[field] is None:
            raise HTTPException(422, f"{field} cannot be null")
    for k, v in data.items():
        setattr(g, k, v)
    db.commit()
    return _out(g)


@router.post("/{goal_id}/contribute", response_model=GoalOut)
def contribute(goal_id: int, body: Contribution, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    g = _owned(db, user, goal_id)
    g.saved_cents += body.amount_cents
    db.commit()
    return _out(g)


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.delete(_owned(db, user, goal_id))
    db.commit()
