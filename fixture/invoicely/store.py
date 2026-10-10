"""Synthetic seed data for Invoicely. All values are fake.

Two tenants, three users (two share a tenant so we can tell tenant-scoped access
apart from owner-only access), and one invoice per user.
"""

from __future__ import annotations

import copy

# token -> user_id   (fixture-only bearer tokens; NOT real secrets)
_TOKENS = {
    "tok-alice": "alice",
    "tok-bob": "bob",
    "tok-carol": "carol",
}

_USERS = {
    "alice": {"id": "alice", "tenant_id": "t1"},
    "bob": {"id": "bob", "tenant_id": "t1"},   # same tenant as alice
    "carol": {"id": "carol", "tenant_id": "t2"},
}

_INVOICES = {
    "inv-a1": {"id": "inv-a1", "tenant_id": "t1", "created_by": "alice", "amount": 120.00, "customer": "Acme"},
    "inv-b1": {"id": "inv-b1", "tenant_id": "t1", "created_by": "bob", "amount": 90.00, "customer": "Globex"},
    "inv-c1": {"id": "inv-c1", "tenant_id": "t2", "created_by": "carol", "amount": 250.00, "customer": "Initech"},
}


def seed():
    """Return a fresh deep copy so each app instance is isolated."""
    return {
        "tokens": copy.deepcopy(_TOKENS),
        "users": copy.deepcopy(_USERS),
        "invoices": copy.deepcopy(_INVOICES),
    }


def user_for_token(data, token):
    uid = data["tokens"].get(token)
    return data["users"].get(uid) if uid else None
