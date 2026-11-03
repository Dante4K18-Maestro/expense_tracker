from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401  (register tables)
from .config import CORS_ORIGINS
from .database import Base, engine
from .routers import auth, categories, goals, reports, transactions


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)  # use Alembic migrations for production schema changes
    yield


app = FastAPI(title="LEDGR API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])

for r in (auth, categories, transactions, goals, reports):
    app.include_router(r.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}


# Keep the root-level `uvicorn app.main:app` entry point fully integrated with
# the UI served by the nested application package.
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent / "ledgr-api" / "static", html=True), name="web")
