"""The TenantGuard remediation graph (LangGraph).

intake → baseline → inspect → propose → apply → verify → (router)
router: fixed→export · regressed/incomplete & budget left→revise→apply… · else→human
"""

from __future__ import annotations

import time
from dataclasses import asdict

from langgraph.graph import END, StateGraph

from .cases import get_case
from .state import RunState
from .verifier import evaluate
from .worktree import Worktree


def _ev(phase, detail=""):
    return {"phase": phase, "detail": detail, "ts": round(time.time(), 3)}


def intake(state: RunState) -> dict:
    case = get_case(state["case_id"])          # raises on non-allowlisted case
    wt = Worktree(case)
    return {
        "worktree": wt,
        "issue": case.issue,
        "attempt": 0,
        "max_attempts": state.get("max_attempts", 3),
        "status": "running",
        "started_at": time.time(),
        "events": [_ev("intake", f"case={case.id}")],
    }


def baseline(state: RunState) -> dict:
    wt = state["worktree"]
    res = wt.run_tests()
    return {
        "baseline_passed": res.passed,
        "baseline_failed": res.failed,
        "events": [_ev("baseline_tests", f"{len(res.passed)} passed / {len(res.failed)} failed")],
    }


def inspect(state: RunState) -> dict:
    wt = state["worktree"]
    files = {rel: wt.read_file(rel) for rel in wt.case.allowed_edit_paths}
    return {"files": files, "events": [_ev("inspect_code", f"read {list(files)}")]}


def propose(state: RunState) -> dict:
    attempt = state.get("attempt", 0) + 1
    patch = state["brain"].propose(
        issue=state["issue"], files=state["files"],
        attempt=attempt, feedback=state.get("feedback"),
    )
    return {
        "attempt": attempt,
        "current_patch": patch,
        "events": [_ev("propose_patch", f"attempt {attempt}: {patch.get('label','')}")],
    }


def apply(state: RunState) -> dict:
    wt = state["worktree"]
    p = state["current_patch"]
    try:
        wt.apply_patch(p["rel"], p["old"], p["new"])
        return {"apply_error": False, "events": [_ev("apply_in_worktree", p["rel"])]}
    except Exception as e:
        return {
            "apply_error": True,
            "feedback": f"apply failed: {e}",
            "events": [_ev("apply_failed", str(e))],
        }


def verify(state: RunState) -> dict:
    wt = state["worktree"]
    case = wt.case
    res = wt.run_tests()
    from .worktree import TestOutcome
    baseline_outcome = TestOutcome(state["baseline_passed"], state["baseline_failed"], "")
    v = evaluate(case, baseline_outcome, res, wt.tests_untampered())
    return {
        "verdict": asdict(v),
        "feedback": v.message + ("\n" + res.digest if res.digest else ""),
        "events": [_ev("verify", f"status={v.status} security={v.security_pass} functionality={v.functionality_pass}")],
    }


def revise(state: RunState) -> dict:
    # back out the previous patch so the next `old` matches baseline source
    wt = state["worktree"]
    p = state.get("current_patch")
    detail = ""
    if p and not state.get("apply_error"):
        detail = wt.revert(p["rel"])
    return {"events": [_ev("classify_failure", detail or state["verdict"]["status"])]}


def export_report(state: RunState) -> dict:
    return _finish(state, status="fixed", phase="export_report")


def human_review(state: RunState) -> dict:
    return _finish(state, status="needs_review", phase="human_review")


def _finish(state: RunState, status: str, phase: str) -> dict:
    import json
    import os

    wt = state["worktree"]
    run_id = state["run_id"]
    outdir = os.path.join("artifacts", run_id)
    os.makedirs(outdir, exist_ok=True)
    diff = wt.diff()
    with open(os.path.join(outdir, "patch.diff"), "w", encoding="utf-8", newline="\n") as f:
        f.write(diff)
    report = {
        "run_id": run_id,
        "case_id": state["case_id"],
        "status": status,
        "brain": getattr(state["brain"], "kind", "?"),
        "attempts": state.get("attempt", 0),
        "baseline": {"passed": len(state["baseline_passed"]), "failed": len(state["baseline_failed"])},
        "verdict": state.get("verdict"),
        "events": state.get("events", []) + [_ev(phase, status)],
        "wall_seconds": round(time.time() - state["started_at"], 2),
    }
    with open(os.path.join(outdir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return {
        "status": status,
        "finished_at": time.time(),
        "artifact_dir": outdir,
        "events": [_ev(phase, f"artifacts → {outdir}")],
    }


# ---- routers ----------------------------------------------------------------
def route_after_apply(state: RunState) -> str:
    if state.get("apply_error"):
        return "revise" if state["attempt"] < state["max_attempts"] else "human"
    return "verify"


def route_after_verify(state: RunState) -> str:
    v = state["verdict"]
    if v["success"]:
        return "export"
    if state["attempt"] < state["max_attempts"]:
        return "revise"
    return "human"


def build_graph():
    g = StateGraph(RunState)
    g.add_node("intake", intake)
    g.add_node("baseline", baseline)
    g.add_node("inspect", inspect)
    g.add_node("propose", propose)
    g.add_node("apply", apply)
    g.add_node("verify", verify)
    g.add_node("revise", revise)
    g.add_node("export", export_report)
    g.add_node("human", human_review)

    g.set_entry_point("intake")
    g.add_edge("intake", "baseline")
    g.add_edge("baseline", "inspect")
    g.add_edge("inspect", "propose")
    g.add_edge("propose", "apply")
    g.add_conditional_edges("apply", route_after_apply,
                            {"verify": "verify", "revise": "revise", "human": "human"})
    g.add_conditional_edges("verify", route_after_verify,
                            {"export": "export", "revise": "revise", "human": "human"})
    g.add_edge("revise", "propose")
    g.add_edge("export", END)
    g.add_edge("human", END)
    return g.compile()
