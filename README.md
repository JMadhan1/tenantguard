<div align="center">

# TenantGuard

### The AI security agent that doesn't trust itself.
*It fixes 3 classes of vulnerability, **catches its own bad fixes**, recovers automatically, and proves every fix with deterministic tests — not AI confidence.*

<br>

[![Live dashboard](https://img.shields.io/badge/Live_dashboard-0f9d58?style=for-the-badge)](https://tenantguard-xhqs.onrender.com)
[![Watch the demo](https://img.shields.io/badge/Watch_the_demo-FF4A4A?style=for-the-badge&logo=loom&logoColor=white)](https://www.loom.com/share/5a96c2f1a02e4450875d58c6affd943a)
[![Evidence](https://img.shields.io/badge/Evidence_pack-4f46e5?style=for-the-badge)](docs/EVIDENCE.md)

![neatHack 2026](https://img.shields.io/badge/neatHack-2026-6d28d9?style=flat-square)
![Python 3.11](https://img.shields.io/badge/python-3.11-3776ab?style=flat-square&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agent-1c7d4d?style=flat-square)
![tests](https://img.shields.io/badge/tests-29_passing-0f9d58?style=flat-square)
![vuln classes](https://img.shields.io/badge/vuln_classes-3-e5383b?style=flat-square)
![OWASP](https://img.shields.io/badge/OWASP-A01_·_A03-3b5bff?style=flat-square)
![cost](https://img.shields.io/badge/cost/fix-$0.005-10b981?style=flat-square)
![CSP](https://img.shields.io/badge/CSP-strict-d12338?style=flat-square)

**Powered by** Claude Opus 4.6 on AWS Bedrock · neatlogs · Entire · cfo.ai

**Team AI LONE STAR** · led by **Madhan J**

</div>

---

## The problem

Most AI code-fix tools silently ship broken patches. They pass the security test but **regress legitimate functionality** — and call it done. Nobody checks.

TenantGuard is different. It fixes the vulnerability, then **runs deterministic tests** on both security AND functionality. If its own fix breaks something, it **reverts, learns, and retries**. It never ships a fix it can't prove.

## 3 vulnerability classes, 1 self-healing loop

| Case | Vulnerability | OWASP | Naive trap fix | What it breaks | Correct fix | Tests |
|---|---|---|---|---|---|---|
| **Invoicely** | IDOR / BOLA | A01 | Owner-only check | Same-tenant access | Tenant-scoped check | 8 |
| **TaskBoard** | SQL Injection | A03 | Strip special chars | Search for "v2.0" | Parameterized query | 8 |
| **DocShare** | Path Traversal | A01 | `basename()` only | Subdirectory access | `realpath` containment | 8 |

Each case is a real vulnerable app with a planted bug, a **naive fix that causes regression** (the trap), and **8 deterministic tests** (4 security + 4 functionality). The agent must pass ALL of them.

## The moment — a real, unedited run

**IDOR (Broken Access Control)**
```
 baseline_tests     6 passed / 2 failed          <- cross-tenant read returns 200, not 403
 propose_patch      attempt 1: owner-only fix
 verify             REGRESSED  security=pass  functionality=FAIL   <- broke same-tenant access
 classify_failure   REVERTED invoicely/app.py                      <- caught itself
 propose_patch      attempt 2: tenant-scoped fix
 verify             FIXED      security=pass  functionality=pass   <- sealed
```

**SQL Injection**
```
 baseline_tests     6 passed / 2 failed          <- UNION injection leaks cross-team data
 propose_patch      attempt 1: strip non-alphanumeric
 verify             REGRESSED  security=pass  functionality=FAIL   <- "v2.0" search returns 0
 classify_failure   REVERTED taskboard/app.py                      <- caught itself
 propose_patch      attempt 2: parameterized query
 verify             FIXED      security=pass  functionality=pass   <- sealed
```

**Path Traversal**
```
 baseline_tests     6 passed / 2 failed          <- ../../secrets/admin.txt leaks credentials
 propose_patch      attempt 1: basename() strip
 verify             REGRESSED  security=fail  functionality=FAIL   <- subdirectory files lost
 classify_failure   REVERTED docshare/app.py                       <- caught itself
 propose_patch      attempt 2: realpath containment
 verify             FIXED      security=pass  functionality=pass   <- sealed
```

A naive agent ships attempt 1 and calls it done. **TenantGuard catches itself — every time.**

## How it works

```
 intake -> baseline -> inspect -> propose -> apply -> verify -> DECISION
                                    ^                             |
                                    |   regressed? revert + retry |
                                    +-----------------------------+
                         budget exhausted / ambiguous -> honest human-review report
```

The **verifier** (not the AI) decides success. It demands BOTH:
- All **security tests** pass (vulnerability is blocked)
- All **functionality tests** pass (legitimate access still works)

Passing the exploit test alone is **not** success.

## Try it in 60 seconds (no API key, no cost)

```bash
pip install -r requirements.txt

# Run all 3 vulnerability classes — watch the recovery loop fire
python run_case.py invoicely-idor-001           # IDOR: naive fix -> regression -> tenant-scoped fix
python run_case.py taskboard-sqli-001           # SQLi: strip chars -> regression -> parameterized query
python run_case.py docshare-traversal-001       # Traversal: basename -> regression -> realpath containment

# Or skip the recovery demo — correct fix on attempt 1
python run_case.py invoicely-idor-001 --correct-first
python run_case.py taskboard-sqli-001 --correct-first
python run_case.py docshare-traversal-001 --correct-first

# Run project tests
python -m pytest tests/ -q                      # 5 offline integration tests
```

## Live run (submission evidence)

```bash
cp .env.example .env              # AWS Bedrock keys + NEATLOGS_API_KEY (see docs/SETUP.md)
python scripts/smoke_bedrock.py   # one cheap call to confirm creds/region/model
python run_case.py --live         # Claude Opus 4.6 on AWS Bedrock, traced by neatlogs
```

## Live dashboard

Visit **[tenantguard-xhqs.onrender.com](https://tenantguard-xhqs.onrender.com)** to:

- **Pick a vulnerability class** (IDOR, SQLi, Path Traversal) and watch the agent fix it live
- **Real-time analytics** — total runs, fix rate, self-corrections, cost per fix
- **OWASP Top 10 coverage** — visual map of covered categories
- **Scan any public repo** — paste a GitHub URL, get a static security scan with AI summary
- **CI/CD prototype** — GitHub Action YAML for automated PR security checks

## Architecture

```
fixture/
  invoicely/              IDOR — multi-tenant invoice API (FastAPI)
  taskboard/              SQLi — task search API with SQLite
  docshare/               Path Traversal — file sharing API with filesystem
  tests/                  8 tenant-isolation tests (IDOR)
  tests_sqli/             8 SQL injection tests
  tests_traversal/        8 path traversal tests

tenantguard_agent/
  graph.py                LangGraph state machine with recovery edges
  brain.py                OfflineBrain (scripted) + LLMBrain (Claude/Bedrock)
  verifier.py             Deterministic: security AND functionality must pass
  worktree.py             Disposable sandbox, scope-guarded patches, test runner
  cases.py                3 allowlisted cases with OWASP metadata
  scanner.py              Static security scanner (secrets, configs, injection patterns)
  pricing.py              Token-to-cost calculator

server/
  app.py                  FastAPI server: SSE streaming, analytics, repo scanner
  static/                 Landing page with glassmorphism UI + live console

.github/workflows/
  tenantguard.yml         GitHub Action prototype — scan + fix + verify on PRs
```

## Three tools, one loop

> **neatlogs** measures the cost. **cfo.ai** prices it. **Entire** proves how it was built.

| Tool | Role | Evidence |
|---|---|---|
| neatlogs | Traces every model call — phases, retries, tokens, cost, failures | [`neatlogs-trace.png`](docs/evidence/neatlogs-trace.png) |
| Entire | Git-based coding provenance — checkpoints over coding sessions | [entire.io link](https://entire.io/gh/JMadhan1/tenantguard/commit/41fa5d7108dc3f1d24684a2313dd430aa84a7c6d) |
| cfo.ai | Measured cost-per-fix ($0.005) to pricing, margin, runway | [`cfo-tenantguard-plan.xlsx`](docs/evidence/cfo-tenantguard-plan.xlsx) |

## Evidence pack

| Claim | Artifact |
|---|---|
| Live remediation + cost | [`docs/evidence/live-bedrock-run.json`](docs/evidence/live-bedrock-run.json) |
| Before / after comparison | [`docs/BEFORE_AFTER.md`](docs/BEFORE_AFTER.md) |
| neatlogs API trace | [`docs/evidence/neatlogs-trace.png`](docs/evidence/neatlogs-trace.png) |
| Entire checkpoint | `01M4N1E31ZDTBN9KSD51Z1640Z` |
| cfo.ai business plan | [`docs/evidence/cfo-tenantguard-plan.xlsx`](docs/evidence/cfo-tenantguard-plan.xlsx) |
| Demo video | [loom.com/share/5a96c2f1...](https://www.loom.com/share/5a96c2f1a02e4450875d58c6affd943a) |
| Full evidence index | [`docs/EVIDENCE.md`](docs/EVIDENCE.md) |

## Safety (enforced in code, not just promised)

- **Disposable worktree only** — agent edits a temp copy, never the real repo
- **Never commits/pushes/PRs** autonomously
- **No LLM-generated shell commands** — only patch + test
- **Scope guard** — can't touch test files or out-of-scope paths
- **Bounded** — max attempts, timeouts, daily caps, rate limits
- **Honest failure** — returns `needs_review` when it can't prove a fix
- **All data synthetic** — no real customer data, no real secrets

See [`docs/SAFETY.md`](docs/SAFETY.md).

## OWASP Top 10 coverage

| Category | Status | Cases |
|---|---|---|
| **A01** Broken Access Control | Covered | IDOR + Path Traversal |
| A02 Cryptographic Failures | — | |
| **A03** Injection | Covered | SQL Injection |
| A04 Insecure Design | — | |
| A05 Security Misconfiguration | — | |
| A06 Vulnerable Components | — | |
| A07 Auth Failures | — | |
| A08 Software Integrity | — | |
| A09 Logging Failures | — | |
| A10 SSRF | — | |

Architecture is extensible — each new vulnerability class is a fixture + test file + case registration.

---

<div align="center">

**Reproduce. Fix. Catch yourself. Prove it.**

*Built for neatHack 2026 by team AI LONE STAR*

</div>
