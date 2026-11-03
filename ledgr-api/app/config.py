import os

ENV = os.environ.get("ENV", "development")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./ledgr.db")
ACCESS_TOKEN_MINUTES = int(os.environ.get("ACCESS_TOKEN_MINUTES", "60"))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
COOKIE_NAME = "access_token"
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

if ENV == "production" and SECRET_KEY == "dev-only-change-me":
    raise RuntimeError("Set SECRET_KEY before running with ENV=production")
