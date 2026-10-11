"""Path-traversal test suite for DocShare.

With the planted vulnerability, directory-traversal sequences in the path
query parameter can escape the user's folder and read secrets or other users'
files. A naive fix (os.path.basename — strips to filename only) blocks
traversal but also breaks access to legitimate subdirectory files — the
regression canary.
"""

from fastapi.testclient import TestClient
from docshare.app import create_app


def client():
    return TestClient(create_app(), raise_server_exceptions=False)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---- legitimate functionality (must PASS before and after fix) ---------------

def test_user_reads_own_file():
    r = client().get("/files?path=readme.txt", headers=auth("tok-alice"))
    assert r.status_code == 200
    assert "Alice" in r.text


def test_user_reads_file_in_subdirectory():
    """REGRESSION CANARY: a naive basename-only fix strips the subdirectory,
    turning 'reports/q1.txt' into 'q1.txt', which doesn't exist."""
    r = client().get("/files?path=reports/q1.txt", headers=auth("tok-alice"))
    assert r.status_code == 200
    assert "Q1" in r.text


def test_bob_reads_own_file():
    r = client().get("/files?path=readme.txt", headers=auth("tok-bob"))
    assert r.status_code == 200
    assert "Bob" in r.text


def test_nonexistent_file_not_found():
    r = client().get("/files?path=nope.txt", headers=auth("tok-alice"))
    assert r.status_code == 404


# ---- security (must FAIL until fixed) ----------------------------------------

def test_traversal_to_secrets_blocked():
    """Classic ../../ traversal to read server secrets."""
    r = client().get("/files?path=../secrets/admin.txt", headers=auth("tok-alice"))
    assert r.status_code in (403, 404), (
        f"path traversal succeeded with status {r.status_code}: {r.text[:100]}"
    )


def test_traversal_to_other_user_blocked():
    """Cross-user traversal via ../bob/."""
    r = client().get("/files?path=../bob/readme.txt", headers=auth("tok-alice"))
    assert r.status_code in (403, 404), (
        f"cross-user traversal succeeded with status {r.status_code}: {r.text[:100]}"
    )


# ---- auth hygiene (must PASS) ------------------------------------------------

def test_unauthenticated_denied():
    r = client().get("/files?path=readme.txt")
    assert r.status_code == 401


def test_invalid_token_denied():
    r = client().get("/files?path=readme.txt", headers=auth("tok-nope"))
    assert r.status_code == 401
