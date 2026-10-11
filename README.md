<div align="center">

# 🛡️ TenantGuard

### A security agent you can trust to run **unattended**.
*It fixes a tenant-isolation leak, **catches its own bad fix**, recovers, and proves the leak is closed — with receipts.*

<br>

[![▶ Watch the 3-min demo](https://img.shields.io/badge/▶_Watch_the_3--min_demo-FF4A4A?style=for-the-badge&logo=loom&logoColor=white)](https://www.loom.com/share/5a96c2f1a02e4450875d58c6affd943a)
[![Live dashboard](https://img.shields.io/badge/🔒_Live_dashboard-0f9d58?style=for-the-badge)](https://tenantguard.jmadhan.me)
[![Evidence](https://img.shields.io/badge/📊_Evidence_pack-4f46e5?style=for-the-badge)](docs/EVIDENCE.md)

![neatHack 2026](https://img.shields.io/badge/neatHack-2026-6d28d9?style=flat-square)
![Python 3.11](https://img.shields.io/badge/python-3.11-3776ab?style=flat-square&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agent-1c7d4d?style=flat-square)
![tests](https://img.shields.io/badge/tests-5_passing-0f9d58?style=flat-square)
![security](https://img.shields.io/badge/CSP-strict_·_no_inline-d12338?style=flat-square)

**Powered by** · Claude Opus 4.6 on AWS Bedrock · 🔎 neatlogs · 📌 Entire · 💰 cfo.ai

**Team AI LONE STAR** · led by **Madhan J**

</div>

---

> **Tenant A can read Tenant B's invoices.** TenantGuard reproduces the leak, writes a fix — then **discovers its own first fix breaks legitimate same-tenant access, reverts it, and applies a tenant-scoped fix** — proving cross-tenant access is blocked *while legitimate requests still work*. Then it stops and writes an evidence report. It **never auto-merges**.

## 🎬 The moment — a real, unedited run

```text
 baseline_tests     6 passed / 2 failed          ← the IDOR leak: cross-tenant read returns 200, not 403
 propose_patch      attempt 1 · owner-only fix
 apply_in_worktree  invoicely/app.py
 verify             status=REGRESSED   security=✅  functionality=❌   ← its own fix broke legit access
 classify_failure   reverted invoicely/app.py      ← 🔁 recovery
 propose_patch      attempt 2 · tenant-scoped fix
 apply_in_worktree  invoicely/app.py
 verify             status=FIXED       security=✅  functionality=✅   ← 🔒 sealed, verified by tests
```

A naive agent ships attempt 1 and calls it done. **TenantGuard catches itself.**

## 📊 Before / after — why the verifier matters

| | Naive agent | **TenantGuard** |
|---|:---:|:---:|
| Cross-tenant read blocked (403) | ✅ | ✅ |
| Legitimate same-tenant access | ❌ **regressed** | ✅ preserved |
| Outcome | `needs_review` (a false "fix") | **`fixed`** |
| Cost / fix (Opus 4.6 on Bedrock) | — | **~$0.005** |

The deterministic **verifier**, not the model, decides success — and it demands **both** security *and* functionality. Passing the exploit test alone is **not** success.

## 🩺 How it works

```
 intake → baseline_tests → inspect → diagnose → propose_patch → apply(worktree) → run_tests → VERIFY
                                                        ▲                                       │
                                                        │   regression? revert + revise ◄───────┘
                                                        └───────────────────────────────────────┘
                                         budget exhausted / ambiguous → honest human-review report
```

## ⚡ See it in 60 seconds (no API key, no cost)

```bash
pip install -r requirements.txt
python run_case.py            # reproduce → naive fix → REGRESSION → revert → tenant-scoped fix → FIXED
python report.py              # → docs/report.html (the whole story on one page)
python -m pytest tests/ -q    # 5 offline integration tests
```

## 🚀 The live run (submission evidence)

```bash
cp .env.example .env              # AWS Bedrock keys + NEATLOGS_API_KEY (see docs/SETUP.md)
python scripts/smoke_bedrock.py   # one cheap call to confirm creds/region/model
python run_case.py --live         # Claude Opus 4.6 on AWS Bedrock, traced by neatlogs
```

## 🔗 Three required tools, one loop

> **neatlogs** measures the cost · **cfo.ai** prices it · **Entire** proves how it was built.

```
  🔎 neatlogs            📌 Entire               💰 cfo.ai
  (observe)      ──►     (prove how)      +      (price it)
  phases, retries,       checkpoints over        cost-per-fix from measured
  tokens, cost, fails    the coding sessions      tokens → margin → runway
```

## 🧾 Evidence

| Claim | Where |
|---|---|
| Live remediation + cost | [`docs/evidence/live-bedrock-run.json`](docs/evidence/live-bedrock-run.json) |
| Before / after | [`docs/BEFORE_AFTER.md`](docs/BEFORE_AFTER.md) · `before-naive.json` vs `after-recover.json` |
| neatlogs trace | [`docs/evidence/neatlogs-trace.png`](docs/evidence/neatlogs-trace.png) |
| Entire checkpoint | `01M4N1E31ZDTBN9KSD51Z1640Z` ([link](https://entire.io/gh/JMadhan1/tenantguard/commit/41fa5d7108dc3f1d24684a2313dd430aa84a7c6d)) |
| cfo.ai business plan | [`docs/evidence/cfo-tenantguard-plan.xlsx`](docs/evidence/cfo-tenantguard-plan.xlsx) (+ revenue, cash) |
| Demo video | [loom.com/share/5a96c2f1…](https://www.loom.com/share/5a96c2f1a02e4450875d58c6affd943a) |
| Full index | [`docs/EVIDENCE.md`](docs/EVIDENCE.md) |

## 🏗️ Architecture

| Path | What it is |
|---|---|
| `fixture/invoicely/` | Synthetic multi-tenant FastAPI invoice API with one planted IDOR |
| `fixture/tests/` | Tenant-isolation suite (security + functionality) |
| `tenantguard_agent/worktree.py` | Disposable copy · **scope-guarded** patches (no test edits) · sandboxed runner |
| `tenantguard_agent/verifier.py` | Deterministic success: **security AND functionality must pass** |
| `tenantguard_agent/graph.py` | LangGraph phase machine with conditional **recovery** edges |
| `tenantguard_agent/brain.py` | `OfflineBrain` (scripted) + `LLMBrain` (Claude via Bedrock, neatlogs-traced) |
| `run_case.py` · `report.py` | Run a case · render the dashboard |

## 🔐 Safety (enforced in code, not just promised)

Disposable worktree only · never commits/pushes/PRs autonomously · **no LLM-generated shell** · patch-scope guard (can't touch tests or out-of-scope files) · bounded attempts + timeouts · honest `needs_review` when it can't prove a fix · all data synthetic · repo text treated as untrusted. See [`docs/SAFETY.md`](docs/SAFETY.md).

<div align="center">
<br>

**Reproduce. Fix. Catch yourself. Prove it.**
*Built for neatHack 2026 · team AI LONE STAR*

</div>
