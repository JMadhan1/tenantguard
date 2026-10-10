"""Deterministic verifier — owns the definition of 'fixed'.

Success requires BOTH the security assertions AND the legitimate-access
functionality tests to pass, with the test files untampered. Passing the
exploit test alone is never success.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .cases import Case
from .worktree import TestOutcome


@dataclass
class Verdict:
    status: str                 # fixed | regressed | incomplete | tampered
    success: bool
    security_pass: bool
    functionality_pass: bool
    regressions: list           # tests passing at baseline, now failing
    security_fixed: list        # security tests failing at baseline, now passing
    still_failing: list         # any target test still failing
    message: str


def evaluate(case: Case, baseline: TestOutcome, current: TestOutcome,
             tests_untampered: bool) -> Verdict:
    cur_pass = set(current.passed)
    cur_fail = set(current.failed)
    base_pass = set(baseline.passed)

    sec = set(case.security_tests)
    fun = set(case.functionality_tests)

    security_pass = sec.issubset(cur_pass)
    functionality_pass = fun.issubset(cur_pass)
    regressions = sorted((base_pass & cur_fail))
    security_fixed = sorted(t for t in sec if t in cur_pass and t not in base_pass)
    still_failing = sorted((sec | fun) & cur_fail)

    if not tests_untampered:
        return Verdict("tampered", False, security_pass, functionality_pass,
                       regressions, security_fixed, still_failing,
                       "Test files were modified — rejecting. Fix the source, not the tests.")

    if security_pass and functionality_pass:
        return Verdict("fixed", True, True, True, regressions, security_fixed, [],
                       "All security and functionality tests pass. Cross-tenant access is "
                       "blocked and legitimate access still works.")

    if regressions:
        return Verdict("regressed", False, security_pass, functionality_pass,
                       regressions, security_fixed, still_failing,
                       f"REGRESSION: {regressions} were passing and now fail. The last patch "
                       "broke legitimate access — revert it and apply a more localized, "
                       "tenant-scoped fix (not owner-scoped).")

    return Verdict("incomplete", False, security_pass, functionality_pass,
                   regressions, security_fixed, still_failing,
                   f"Not done yet. Still failing: {still_failing}.")
