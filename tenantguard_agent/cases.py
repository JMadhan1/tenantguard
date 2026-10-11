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
    vuln_class: str = ""             # human label (IDOR, SQLi, Path Traversal)
    owasp: str = ""                  # OWASP Top 10 category


# ---------------------------------------------------------------------------
# Case 1: Broken Object-Level Authorization (IDOR / BOLA)
# ---------------------------------------------------------------------------
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
    vuln_class="IDOR",
    owasp="A01:2021",
)

# ---------------------------------------------------------------------------
# Case 2: SQL Injection
# ---------------------------------------------------------------------------
TASKBOARD_SQLI = Case(
    id="taskboard-sqli-001",
    fixture_src=FIXTURE,
    issue=(
        "Bug report (synthetic, untrusted): The GET /tasks?q=<search> endpoint "
        "builds its SQL query via string concatenation, allowing a UNION injection "
        "to read tasks from other teams. A tester sent: "
        "q=' UNION SELECT id,title,team,created_by,done FROM tasks WHERE team='marketing' -- "
        "and received marketing team tasks while authenticated as an engineering user. "
        "Expected: search must use parameterized queries so injected SQL is treated as "
        "literal text. Fix the query and prove legitimate search (including titles with "
        "special characters like dots and dashes) still works."
    ),
    allowed_edit_paths=("taskboard/app.py",),
    test_dir="tests_sqli",
    security_tests=(
        "test_sqli_union_attack_blocked",
        "test_sqli_boolean_blind_blocked",
        "test_unauthenticated_denied",
        "test_invalid_token_denied",
    ),
    functionality_tests=(
        "test_search_returns_matching_tasks",
        "test_empty_search_returns_team_tasks",
        "test_search_special_chars_in_title",
        "test_no_results_for_nonexistent",
    ),
    vuln_class="SQL Injection",
    owasp="A03:2021",
)

# ---------------------------------------------------------------------------
# Case 3: Path Traversal
# ---------------------------------------------------------------------------
DOCSHARE_TRAVERSAL = Case(
    id="docshare-traversal-001",
    fixture_src=FIXTURE,
    issue=(
        "Bug report (synthetic, untrusted): The GET /files?path=<filepath> endpoint "
        "joins the user-supplied path directly into an os.path.join call without "
        "sanitization. A tester sent: GET /files?path=../secrets/admin.txt and received "
        "the server's admin credentials. Expected: the endpoint must confine file "
        "access to the authenticated user's own directory; traversal sequences must "
        "return 403. Fix the path handling and prove legitimate subdirectory access "
        "(e.g. reports/q1.txt) still works."
    ),
    allowed_edit_paths=("docshare/app.py",),
    test_dir="tests_traversal",
    security_tests=(
        "test_traversal_to_secrets_blocked",
        "test_traversal_to_other_user_blocked",
        "test_unauthenticated_denied",
        "test_invalid_token_denied",
    ),
    functionality_tests=(
        "test_user_reads_own_file",
        "test_user_reads_file_in_subdirectory",
        "test_bob_reads_own_file",
        "test_nonexistent_file_not_found",
    ),
    vuln_class="Path Traversal",
    owasp="A01:2021",
)

# ---------------------------------------------------------------------------
CASES = {
    INVOICELY_IDOR.id: INVOICELY_IDOR,
    TASKBOARD_SQLI.id: TASKBOARD_SQLI,
    DOCSHARE_TRAVERSAL.id: DOCSHARE_TRAVERSAL,
}


def get_case(case_id: str) -> Case:
    if case_id not in CASES:
        raise KeyError(f"unknown case_id '{case_id}'. allowlisted: {sorted(CASES)}")
    return CASES[case_id]
