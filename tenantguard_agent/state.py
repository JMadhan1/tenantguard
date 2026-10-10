"""Typed graph state. Stores concise rationale + evidence refs, not hidden
chain-of-thought."""

from __future__ import annotations

from operator import add
from typing import Annotated, Any, TypedDict


class RunState(TypedDict, total=False):
    run_id: str
    case_id: str
    issue: str
    worktree: Any            # tenantguard_agent.worktree.Worktree (in-memory)
    brain: Any               # OfflineBrain | LLMBrain
    baseline_passed: list
    baseline_failed: list
    files: dict              # rel -> contents (what the agent inspected)
    attempt: int
    max_attempts: int
    current_patch: dict
    feedback: str
    apply_error: bool
    verdict: dict            # serialized Verdict
    status: str              # fixed | needs_review | running
    started_at: float
    finished_at: float
    artifact_dir: str
    events: Annotated[list, add]   # phase transitions (append-only)
