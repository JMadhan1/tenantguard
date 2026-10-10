"""Tenant-isolation test suite for Invoicely.

These encode the INTENDED behavior. With the planted bug, the two cross-tenant
tests fail (the leak) while legitimate-access tests pass. A correct fix makes
all green; a naive owner-only fix breaks `test_same_tenant_other_user_allowed`
(the regression canary).
"""

from fastapi.testclient import TestClient
from invoicely.app import create_app


def client():
    return TestClient(create_app(), raise_server_exceptions=True)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---- legitimate access (must PASS before and after any fix) -----------------
def test_owner_reads_own_invoice():
    r = client().get("/invoices/inv-a1", headers=auth("tok-alice"))
    assert r.status_code == 200
    assert r.json()["id"] == "inv-a1"


def test_same_tenant_other_user_allowed():
    # alice and bob share tenant t1; tenant-scoped access means alice may read
    # bob's invoice. REGRESSION CANARY: an owner-only fix would break this.
    r = client().get("/invoices/inv-b1", headers=auth("tok-alice"))
    assert r.status_code == 200
    assert r.json()["id"] == "inv-b1"


def test_carol_reads_own_invoice():
    r = client().get("/invoices/inv-c1", headers=auth("tok-carol"))
    assert r.status_code == 200


# ---- the vulnerability (must FAIL until fixed) ------------------------------
def test_cross_tenant_read_blocked_carol_to_t1():
    r = client().get("/invoices/inv-a1", headers=auth("tok-carol"))
    assert r.status_code == 403


def test_cross_tenant_read_blocked_alice_to_t2():
    r = client().get("/invoices/inv-c1", headers=auth("tok-alice"))
    assert r.status_code == 403


# ---- auth / input hygiene (must PASS) ---------------------------------------
def test_unauthenticated_denied():
    r = client().get("/invoices/inv-a1")
    assert r.status_code == 401


def test_invalid_token_denied():
    r = client().get("/invoices/inv-a1", headers=auth("tok-nope"))
    assert r.status_code == 401


def test_unknown_invoice_not_found():
    r = client().get("/invoices/does-not-exist", headers=auth("tok-alice"))
    assert r.status_code == 404
