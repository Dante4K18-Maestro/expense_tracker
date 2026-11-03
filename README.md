# LEDGR API

FastAPI + SQLAlchemy 2 backend for the LEDGR expense tracker: auth, categories, transactions, goals and reports.
Money is stored and transferred as **integer cents** (`amount_cents`), so there are no floating-point errors.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # then: export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload   # docs at http://localhost:8000/docs
pytest                          # run the test suite
```
SQLite is the default. For PostgreSQL set `DATABASE_URL=postgresql+psycopg://user:pass@host/ledgr` and `pip install "psycopg[binary]"`.

## Endpoints (`/api/v1`)
| Area | Routes |
|---|---|
| Auth | `POST /auth/register` · `POST /auth/login` · `POST /auth/logout` · `GET /auth/me` |
| Categories | `GET/POST /categories` · `PATCH/DELETE /categories/{id}` (optional `monthly_budget_cents`) |
| Transactions | `GET /transactions` (filters: `type, category_id, date_from, date_to, q, limit, offset`) · `POST` · `GET/PATCH/DELETE /transactions/{id}` |
| Goals | `GET/POST /goals` · `PATCH/DELETE /goals/{id}` · `POST /goals/{id}/contribute` |
| Reports | `GET /reports/summary?month=YYYY-MM` · `/reports/by-category` · `/reports/cash-flow?months=6` · `/reports/export.csv` |

Each report maps to a dashboard tile: summary → Overview tiles and Savings rate, by-category → donut and bars, cash-flow → bar/line charts.

## Security notes
- Passwords: scrypt with per-user salt. JWT (HS256) in an `httpOnly`, `SameSite=Lax` cookie; `Authorization: Bearer` also accepted.
- Every query is scoped by `user_id`; other users' records return 404.
- CSV export neutralises formula injection. Login responses are uniform to avoid revealing which emails exist.
- Before production: set a strong `SECRET_KEY`, `ENV=production`, `COOKIE_SECURE=true`, serve over HTTPS, add rate limiting on `/auth/*` (e.g. at the reverse proxy), and switch from `create_all` to Alembic migrations.
