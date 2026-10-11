"""SQL-injection test suite for TaskBoard.

With the planted SQL injection, the UNION and boolean-blind tests fail (data
leaks across teams). The functionality tests — including searching for titles
with special characters like 'v2.0' — pass at baseline. A naive fix (stripping
non-alphanumeric input) blocks injection but breaks the special-char search
(the regression canary).
"""

from fastapi.testclient import TestClient
from taskboard.app import create_app


def client():
    return TestClient(create_app(), raise_server_exceptions=False)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---- legitimate functionality (must PASS before and after fix) ---------------

def test_search_returns_matching_tasks():
    r = client().get("/tasks?q=login", headers=auth("tok-alice"))
    assert r.status_code == 200
    tasks = r.json()
    assert any(t["id"] == "task-1" for t in tasks)


def test_empty_search_returns_team_tasks():
    r = client().get("/tasks?q=", headers=auth("tok-alice"))
    assert r.status_code == 200
    ids = {t["id"] for t in r.json()}
    assert "task-1" in ids and "task-2" in ids
    assert "task-3" not in ids  # marketing — should not appear


def test_search_special_chars_in_title():
    """REGRESSION CANARY: a naive input-sanitization fix will strip the dots and
    dashes from 'v2.0', turning it into 'v20', which no longer matches
    'Deploy v2.0-rc1'."""
    r = client().get("/tasks?q=v2.0", headers=auth("tok-alice"))
    assert r.status_code == 200
    tasks = r.json()
    assert any("v2.0" in t["title"] for t in tasks)


def test_no_results_for_nonexistent():
    r = client().get("/tasks?q=zzzznonexistent", headers=auth("tok-alice"))
    assert r.status_code == 200
    assert r.json() == []


# ---- security (must FAIL until fixed) ----------------------------------------

def test_sqli_union_attack_blocked():
    """UNION injection to leak tasks from another team."""
    payload = "' UNION SELECT id,title,team,created_by,done FROM tasks WHERE team='marketing' --"
    r = client().get(f"/tasks?q={payload}", headers=auth("tok-alice"))
    # A fixed endpoint returns only the caller's team data — no marketing tasks.
    assert r.status_code == 200
    teams = {t.get("team") for t in r.json()}
    assert "marketing" not in teams, "SQL injection exposed cross-team data"


def test_sqli_boolean_blind_blocked():
    """OR-based injection to bypass the team filter."""
    payload = "' OR 1=1 --"
    r = client().get(f"/tasks?q={payload}", headers=auth("tok-alice"))
    assert r.status_code == 200
    teams = {t.get("team") for t in r.json()}
    assert "marketing" not in teams, "SQL injection bypassed team filter"


# ---- auth hygiene (must PASS) ------------------------------------------------

def test_unauthenticated_denied():
    r = client().get("/tasks?q=test")
    assert r.status_code == 401


def test_invalid_token_denied():
    r = client().get("/tasks?q=test", headers=auth("tok-nope"))
    assert r.status_code == 401
