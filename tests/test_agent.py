"""Offline integration tests for the TenantGuard agent (no API key).

These run the real LangGraph graph with a scripted brain — real pytest, a real
regression, a real revert.
"""

import os

from tenantguard_agent.brain import BUG, NAIVE
from tenantguard_agent.runner import run_case


def _phases(final):
    return [e["phase"] for e in final["events"]]


def _verify_statuses(final):
    return [e["detail"] for e in final["events"] if e["phase"] == "verify"]


def test_recovery_reaches_fixed():
    final = run_case("invoicely-idor-001", offline=True, naive_first=True,
                     run_id="test-recovery")
    assert final["status"] == "fixed"
    assert final["attempt"] == 2
    assert final["verdict"]["success"] is True
    # a real regression was observed before the fix
    statuses = _verify_statuses(final)
    assert any("regressed" in s for s in statuses)
    assert "status=fixed" in statuses[-1]
    assert "classify_failure" in _phases(final)


def test_correct_first_one_attempt():
    final = run_case("invoicely-idor-001", offline=True, naive_first=False,
                     run_id="test-correct")
    assert final["status"] == "fixed"
    assert final["attempt"] == 1


def test_budget_exhaustion_yields_human_review():
    class AlwaysNaive:
        kind = "always-naive"
        def propose(self, *, issue, files, attempt, feedback=None):
            return {"rel": "invoicely/app.py", "old": BUG, "new": NAIVE,
                    "rationale": "x", "label": "naive"}

    final = run_case("invoicely-idor-001", brain=AlwaysNaive(), max_attempts=2,
                     run_id="test-budget")
    assert final["status"] == "needs_review"
    assert final["verdict"]["success"] is False


def test_unknown_case_rejected():
    import pytest
    with pytest.raises(KeyError):
        run_case("not-a-real-case", offline=True, run_id="test-unknown")


def test_artifacts_written():
    final = run_case("invoicely-idor-001", offline=True, run_id="test-artifacts")
    outdir = final["artifact_dir"]
    assert os.path.exists(os.path.join(outdir, "report.json"))
    assert os.path.exists(os.path.join(outdir, "patch.diff"))
