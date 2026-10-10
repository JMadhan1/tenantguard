"""Allowlisted remediation cases. Only these case_ids may be run."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

FIXTURE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fixture"))


@dataclass(frozen=True)
class Case:
    id: str
    fixture_src: str
    issue: str                       # untrusted bug report (data, not instructions)
    allowed_edit_paths: tuple        # files the agent may modify
    test_dir: str                    # relative dir under the worktree
    security_tests: tuple            # function names that must DENY access
    functionality_tests: tuple       # function names that must ALLOW/behave


INVOICELY_IDOR = Case(
    id="invoicely-idor-001",
    fixture_src=FIXTURE,
    issue=(
        "Bug report (synthetic, untrusted): A user from tenant t2 reported that by "
        "calling GET /invoices/{id} with another tenant's invoice id, they received a "
        "200 with the full invoice body. Expected: a user may only read invoices that "
        "belong to their own tenant; cross-tenant reads must return 403. Reproduce, fix "
        "the authorization check, and prove legitimate same-tenant access still works."
    ),
    allowed_edit_paths=("invoicely/app.py", "invoicely/store.py"),
    test_dir="tests",
    security_tests=(
        "test_cross_tenant_read_blocked_carol_to_t1",
        "test_cross_tenant_read_blocked_alice_to_t2",
        "test_unauthenticated_denied",
        "test_invalid_token_denied",
    ),
    functionality_tests=(
        "test_owner_reads_own_invoice",
        "test_same_tenant_other_user_allowed",
        "test_carol_reads_own_invoice",
        "test_unknown_invoice_not_found",
    ),
)

CASES = {INVOICELY_IDOR.id: INVOICELY_IDOR}


def get_case(case_id: str) -> Case:
    if case_id not in CASES:
        raise KeyError(f"unknown case_id '{case_id}'. allowlisted: {sorted(CASES)}")
    return CASES[case_id]
