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

### 2026-10-10 — P2–P5 agent + neatlogs wiring + dashboard (completed, tested)
- Deterministic tools + **verifier** (success = security AND functionality tests pass), scope guard (no test edits), sandboxed pytest runner. P2 test: baseline→incomplete, correct fix→fixed, naive fix→regressed, guards block. ✅
- **LangGraph agent** (`graph.py`) with conditional recovery edges; `OfflineBrain` (scripted) + `LLMBrain` (Claude, neatlogs-wrapped, baseline/improved prompt for the before/after). `run_case.py` entrypoint.
- **Full offline run reaches `fixed` in 2 attempts after a real observed regression + revert** (no API key). 5 offline agent integration tests pass.
- neatlogs wired via `neatlogs.wrap(Anthropic())` in `LLMBrain`; usage/cost recorded per run for cost-per-fix.
- **Polished dashboard** (`report.py` → `docs/report.html`): KPI tiles, recovery-highlighted timeline, security/functionality verdict matrix, patch diff; theme-aware, responsive (verified desktop + mobile).
- Docs: README, BUSINESS_PLAN (cfo.ai), EVIDENCE index, SETUP, DEMO_SCRIPT, BUILD_IN_PUBLIC, ENTIRE.
- **Pending (needs operator):** live traced runs (ANTHROPIC + NEATLOGS keys), Entire checkpoints, cfo.ai access, demo video, #neatHack posts, public repo push.

### 2026-10-10 — LIVE run on AWS Bedrock (tested)
- Backend: AWS Bedrock, Claude **Opus 4.6** (`global.anthropic.claude-opus-4-6-v1`), region `ap-south-1`. `scripts/smoke_bedrock.py` → model replied OK.
- **Live remediation (real model), both runs reached `fixed`, security+functionality pass, 1 attempt:**
  - improved prompt: 1128 in / 273 out tokens, **$0.0050/fix**
  - baseline prompt: 1075 in / 221 out tokens, **$0.0044/fix**
- Finding: Opus 4.6 fixes correctly in 1 attempt even on the weak prompt, so it does not trip the recovery trap naturally. **Recovery is demonstrated by the offline labeled fault-injection run** (deterministic regression→revert→fix), which the brief explicitly permits.
- **neatlogs tracing was OFF** (`neatlogs: False`) because `NEATLOGS_API_KEY` is not yet set — needed for the required trace evidence.

## Submission (tracking)
- [ ] Agent completes the remediation start→finish
- [ ] neatlogs before/after + trace links
- [ ] Entire checkpoint link + ID
- [ ] cfo.ai business plan (needs access)
- [ ] Recovery run (failed fix → next steps) — trap verified; live trace pending
- [x] Public repo, event-dated commits — **https://github.com/JMadhan1/tenantguard**
- [ ] Demo video + #neatHack posts
