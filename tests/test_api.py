import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

API = "/api/v1"


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def signup(c, email="a@x.com", pw="supersecret"):
    r = c.post(f"{API}/auth/register", json={"email": email, "password": pw})
    assert r.status_code == 201, r.text
    return r.json()


def tx(c, **kw):
    body = {"type": "expense", "amount_cents": 1000, "occurred_on": "2026-10-05", "note": ""} | kw
    r = c.post(f"{API}/transactions", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_auth_flow(client):
    assert client.get(f"{API}/auth/me").status_code == 401
    signup(client)
    assert client.get(f"{API}/auth/me").json()["email"] == "a@x.com"
    assert client.post(f"{API}/auth/register", json={"email": "A@x.com", "password": "supersecret"}).status_code == 409
    client.post(f"{API}/auth/logout")
    assert client.get(f"{API}/auth/me").status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": "a@x.com", "password": "wrong"}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": "a@x.com", "password": "supersecret"}).status_code == 200


def test_bearer_token(client):
    token = signup(client)["access_token"]
    client.cookies.clear()
    assert client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_transaction_crud_and_validation(client):
    signup(client)
    t = tx(client, note="Lunch")
    assert client.patch(f"{API}/transactions/{t['id']}", json={"amount_cents": 2500}).json()["amount_cents"] == 2500
    assert client.patch(f"{API}/transactions/{t['id']}", json={"amount_cents": None}).status_code == 422
    assert client.post(f"{API}/transactions", json={"type": "expense", "amount_cents": 0, "occurred_on": "2026-10-05"}).status_code == 422
    assert client.post(f"{API}/transactions", json={"type": "expense", "amount_cents": 5, "occurred_on": "2026-10-05", "category_id": 999}).status_code == 422
    page = client.get(f"{API}/transactions", params={"q": "lunch"}).json()
    assert page["total"] == 1
    assert client.delete(f"{API}/transactions/{t['id']}").status_code == 204
    assert client.get(f"{API}/transactions/{t['id']}").status_code == 404


def test_users_are_isolated(client):
    signup(client)
    t = tx(client)
    with TestClient(app) as other:
        signup(other, "b@x.com")
        assert other.get(f"{API}/transactions/{t['id']}").status_code == 404
        assert other.delete(f"{API}/transactions/{t['id']}").status_code == 404
        assert other.get(f"{API}/transactions").json()["total"] == 0


def test_reports(client):
    signup(client)
    food = next(c for c in client.get(f"{API}/categories").json() if c["name"] == "Food")
    tx(client, type="income", amount_cents=500000)
    tx(client, amount_cents=80000, category_id=food["id"])
    tx(client, amount_cents=20000)
    s = client.get(f"{API}/reports/summary", params={"month": "2026-10"}).json()
    assert (s["income_cents"], s["expense_cents"], s["net_cents"]) == (500000, 100000, 400000)
    assert s["savings_rate"] == 0.8 and s["balance_cents"] == 400000
    cats = client.get(f"{API}/reports/by-category", params={"month": "2026-10"}).json()
    assert [c["name"] for c in cats] == ["Food", "Uncategorized"] and cats[0]["share"] == 0.8
    flow = client.get(f"{API}/reports/cash-flow", params={"months": 3}).json()
    assert len(flow) == 3
    assert client.get(f"{API}/reports/summary", params={"month": "bad"}).status_code == 422


def test_csv_export_blocks_formula_injection(client):
    signup(client)
    tx(client, note="=HYPERLINK(\"http://evil\")")
    body = client.get(f"{API}/reports/export.csv").text
    assert "'=HYPERLINK" in body


def test_goals(client):
    signup(client)
    g = client.post(f"{API}/goals", json={"name": "Laptop", "target_cents": 160000}).json()
    g = client.post(f"{API}/goals/{g['id']}/contribute", json={"amount_cents": 64000}).json()
    assert g["progress"] == 0.4
