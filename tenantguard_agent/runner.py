"""Build state, pick a brain, run the graph, return the final state."""

from __future__ import annotations

import os
import uuid

from .brain import LLMBrain, OfflineBrain
from .graph import build_graph


def run_case(case_id: str, *, offline: bool = True, model: str | None = None,
             quality: str = "improved", naive_first: bool = True, max_attempts: int = 3,
             run_id: str | None = None, brain=None) -> dict:
    if brain is None:
        brain = OfflineBrain(naive_first=naive_first) if offline else LLMBrain(
            model=model or os.environ.get("TENANTGUARD_MODEL", "claude-sonnet-5-5"),
            quality=quality)
    graph = build_graph()
    run_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
    initial = {
        "run_id": run_id,
        "case_id": case_id,
        "brain": brain,
        "max_attempts": max_attempts,
        "events": [],
    }
    final = graph.invoke(initial, config={"recursion_limit": 60})
    wt = final.get("worktree")
    if wt is not None:
        final["_diff"] = wt.diff()
        wt.cleanup()
    if getattr(brain, "neatlogs_enabled", False):
        try:
            import neatlogs
            neatlogs.flush()
        except Exception:
            pass
    return final
