# Demo video script (≤ 3:00)

> ✅ **Recorded:** https://www.loom.com/share/5a96c2f1a02e4450875d58c6affd943a


Record 1080p: terminal + the `docs/report.html` dashboard + neatlogs/Entire/cfo.ai tabs. Show architecture, use, reasoning, and result for each required tool.

**0:00–0:15 — Problem + promise.** "TenantGuard — a security agent you can trust to run unattended. Tenant A can read Tenant B's invoice. Watch it fix that, and catch its own mistake." Run `python -m pytest fixture/ -q` → `2 failed, 6 passed` (the leak).

**0:15–0:35 — Architecture + boundaries.** One line on the LangGraph phase machine; stress: the agent edits a disposable worktree, never auto-merges, and a deterministic verifier (not the model) decides success. Distinguish the runtime agent from the coding assistant (Entire).

**0:35–1:25 — One live run + the recovery (the star).** `python run_case.py --live`. Narrate the timeline: reproduce → propose → apply → **verify: regressed** (its fix broke legitimate same-tenant access) → **revert** → tenant-scoped fix → **fixed**. Open `docs/report.html` on the recovery row. This is real observed state, not a staged success.

**1:25–1:55 — neatlogs before/after.** Show the two traces: `--quality baseline` vs `--quality improved`. On screen: attempts, tokens, cost-per-fix dropping; point at the failed span in the baseline trace and the specific code fix.

**1:55–2:20 — Entire.** `entire checkpoint list`, a commit with its Entire-Checkpoint trailer, and `entire checkpoint explain HEAD` — the captured coding context that proves *how* the fix was built. (Entire is provenance, not a runtime dependency.)

**2:20–2:45 — cfo.ai.** The business plan: pricing, measured cost-per-fix (from neatlogs), and a scenario where high retries make the unit economics unattractive — and how the attempt budget protects margin.

**2:45–3:00 — Result + honesty.** All green, repo + evidence index, and honest limitations (one defect family, synthetic fixture). "Reproduce, fix, catch yourself, prove it."
