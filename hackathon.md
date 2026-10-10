# neatHack — Build Log

## Project
- **Name:** TenantGuard
- **Purpose (one sentence):** An evidence-first security-remediation agent that reproduces a tenant-isolation (IDOR) failure, writes a minimal fix, recovers when its first fix breaks legitimate access, and proves cross-tenant access is blocked while legitimate requests still work.
- **Problem it addresses:** Broken object-level authorization (tenant isolation) is a top real-world vulnerability. Fixing it safely requires reproducing the leak, patching narrowly, and proving you didn't break legitimate access — exactly the loop TenantGuard automates with checkable evidence.

## Team
- Team: **AI LONE STAR** — led by **Madhan J** (handles to be added by the builder)

## Stack
- **Fixture:** Python 3.11, FastAPI (synthetic multi-tenant invoice API, one planted IDOR bug)
- **Agent:** LangGraph state machine, deterministic tools, a deterministic verifier; Claude via a model adapter (model TBD with operator; default configurable, offline path for no-key runs)
- **neatlogs:** runtime observability of the agent (phases, tool outcomes, retries, patch attempts, latency, token/cost) + before/after improvement. _(to wire)_
- **Entire:** coding provenance — checkpoints over the sessions that implement the agent and fix the bug found via neatlogs. _(to wire)_
- **cfo.ai:** business plan (pricing, cost per fix from measured tokens, revenue, runway). _(needs organizer credit route — do NOT enter a card)_

## Build log

### 2026-10-10 — P0 scaffold + P1 vulnerable fixture (completed, tested)
- Environment check: FastAPI, httpx, pydantic, uvicorn, **LangGraph**, langchain-core, anthropic, pytest, Docker all present; `neatlogs` to install. Missing: `ANTHROPIC_API_KEY`, `NEATLOGS_API_KEY`, Entire + cfo.ai access (flagged to operator).
- Built the fixture `fixture/invoicely` (synthetic 2 tenants / 3 users / 3 invoices; fixture-only bearer tokens) with one planted defect: `GET /invoices/{id}` is missing a tenant-authorization check (IDOR / broken object-level auth).
- Wrote the tenant-isolation pytest suite (`fixture/tests`) encoding intended behavior.
- **Tests that actually ran — baseline:** `2 failed, 6 passed`. The 2 failures are the real leak (carol reads a t1 invoice; alice reads a t2 invoice → 200 instead of 403). Legitimate access, auth (401), and not-found (404) pass.
- **Recovery trap verified** (throwaway copies): the correct **tenant-scoped** fix → `8 passed`; a naive **owner-only** fix → `1 failed` (breaks `test_same_tenant_other_user_allowed`, the same-tenant canary) + 7 passed. So recovery is genuine and reachable.
- Safety boundaries written (`docs/SAFETY.md`).
- **Next (P2):** deterministic tools + verifier (both security AND functionality must pass).

## Submission (tracking)
- [ ] Agent completes the remediation start→finish
- [ ] neatlogs before/after + trace links
- [ ] Entire checkpoint link + ID
- [ ] cfo.ai business plan (needs access)
- [ ] Recovery run (failed fix → next steps) — trap verified; live trace pending
- [ ] Public repo, event-dated commits
- [ ] Demo video + #neatHack posts
