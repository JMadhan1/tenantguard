<div align="center">

# 🛡️ TenantGuard

### An evidence-first security-remediation agent you can trust to run unattended.

*It reproduces a tenant-isolation leak, fixes it, **catches its own bad fix**, recovers, and proves the leak is closed — with receipts.*

![neatHack 2026](https://img.shields.io/badge/neatHack-2026-6d28d9?style=for-the-badge)
![Python 3.11](https://img.shields.io/badge/python-3.11-3776ab?style=for-the-badge&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agent-1c7d4d?style=for-the-badge)
![tests](https://img.shields.io/badge/tests-passing-0f9d58?style=for-the-badge)

**Team AI LONE STAR** · led by **Madhan J**

</div>

---

> **Tenant A can read Tenant B's invoice.** TenantGuard reproduces the failure, locates the missing authorization check, writes a fix, **discovers its first fix breaks legitimate same-tenant access, reverts it, corrects it**, and proves cross-tenant access is blocked while legitimate requests still work — then stops and writes an evidence report. Never auto-merges.

```
 intake → baseline_tests → inspect → diagnose → propose_patch → apply(worktree) → run_tests → VERIFY
                                                         ▲                                      │
                                                         │   regression? revert + revise ◄──────┘
                                                         └──────────────────────────────────────┘
                                          budget exhausted / ambiguous → honest human-review report
```

## Why this can't be faked

A deterministic **verifier**, not the model, decides success — and it demands **two** things at once:

- 🔒 **Security:** cross-tenant reads return `403` (the leak is closed).
- ✅ **Functionality:** a user can still read a *different* user's invoice **in their own tenant** (legitimate access preserved).

Passing the exploit test alone is **not** success. And the fixture hides a trap: the *obvious* fix (owner-only check) closes the leak but **breaks** legitimate same-tenant access. A real agent must recover — which is exactly what the demo shows, on a real observed run.

## See it in 60 seconds (no API key, no cost)

A scripted brain drives the **real** LangGraph agent — real pytest, a real regression, a real revert:

```bash
pip install -r requirements.txt
python run_case.py            # reproduce → naive fix → REGRESSION → revert → tenant-scoped fix → FIXED
python report.py              # → docs/report.html  (the whole story on one page)
python -m pytest tests/ -q    # offline agent integration tests
```

Baseline fixture state (the leak): `2 failed, 6 passed` — cross-tenant reads return `200` instead of `403`.

## The real run (for submission evidence)

```bash
cp .env.example .env          # AWS Bedrock keys + NEATLOGS_API_KEY (see docs/SETUP.md)
python scripts/smoke_bedrock.py   # one cheap call to confirm creds/region/model
python run_case.py --live         # Claude Opus 4.6 on AWS Bedrock, traced by neatlogs
```

Then the **before/after** that neatHack asks for — two neatlogs-traced runs of the *same* agent, improved:

```bash
python run_case.py --live --quality baseline     # weaker prompt
python run_case.py --live --quality improved      # prompt improved from reading the baseline trace
# compare attempts / tokens / cost-per-fix across the two neatlogs traces
```

## Three required tools, one loop

```
  neatlogs            Entire                 cfo.ai
  (observe)   ──►     (prove how)      +     (price it)
  phases, retries,    checkpoints over       cost-per-fix from measured
  patch attempts,     the coding sessions    tokens → margin → runway
  tokens, cost        that built the fix
```
> *"neatlogs measures the cost, cfo.ai prices it, Entire proves how it was built."*

## Architecture

| Path | What it is |
|---|---|
| `fixture/invoicely/` | Synthetic multi-tenant FastAPI invoice API with one planted IDOR |
| `fixture/tests/` | Tenant-isolation suite (security + functionality tests) |
| `tenantguard_agent/worktree.py` | Disposable copy, **scope-guarded** patches (no test edits), sandboxed test runner |
| `tenantguard_agent/verifier.py` | Deterministic success: **security AND functionality must pass** |
| `tenantguard_agent/graph.py` | LangGraph phase machine with conditional **recovery** edges |
| `tenantguard_agent/brain.py` | `OfflineBrain` (scripted) + `LLMBrain` (Claude, neatlogs-traced) |
| `run_case.py` · `report.py` | Run a case · render the HTML report |
| `docs/SAFETY.md` | Enforced safety boundaries |

## Safety (enforced in code, not just promised)

Disposable worktree only · never commits/pushes/PRs autonomously · **no LLM-generated shell** · patch-scope guard (can't edit tests or out-of-scope files) · bounded attempts + timeouts · honest "needs_review" when it can't prove a fix · all data synthetic · repo text treated as untrusted data. See [`docs/SAFETY.md`](docs/SAFETY.md).

<div align="center">

**Built for neatHack 2026.** · *Reproduce. Fix. Catch yourself. Prove it.*

</div>
