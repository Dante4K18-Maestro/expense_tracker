from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import DATABASE_URL

_sqlite = DATABASE_URL.startswith("sqlite")
_kwargs = {}
if _sqlite:
    _kwargs["connect_args"] = {"check_same_thread": False}
    if DATABASE_URL in ("sqlite://", "sqlite:///:memory:"):
        _kwargs["poolclass"] = StaticPool  # one shared in-memory DB (tests)

engine = create_engine(DATABASE_URL, **_kwargs)

if _sqlite:
    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
