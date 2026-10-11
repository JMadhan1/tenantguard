# Evidence index — claim → artifact → how judges verify

Fill the `LINK` placeholders as you capture evidence. Keep every link; never claim a private link is judge-accessible without checking.

| # | Required evidence | Artifact / where | How to verify |
|---|---|---|---|
| 1 | **Agent completes a substantial task** | `tenantguard_agent/` + demo video | Run `python run_case.py` → status `fixed`; watch the phase timeline |
| ✓ | **Live run on AWS Bedrock (committed)** | `docs/evidence/live-bedrock-run.json` + `docs/evidence/live-bedrock-patch.diff` + `docs/report-live.html` | Claude **Opus 4.6** on Bedrock (`ap-south-1`), status `fixed`, **neatlogs: true**, $0.0050/fix — checkable in the repo |
| 2 | **Before/after improvement** (numbers compared) | **`docs/BEFORE_AFTER.md`** + `docs/evidence/before-naive.json` (`needs_review`, shipped a regression) vs `docs/evidence/after-recover.json` (`fixed`) | Naive agent ships a regression (breaks legitimate access); TenantGuard's verify-and-recover catches it and reaches green. Plus live Bedrock cost/fix ($0.0044 vs $0.0050). neatlogs trace: `docs/evidence/neatlogs-trace.png` |
| 3 | **neatlogs use** (trace screenshot) | **`docs/evidence/neatlogs-trace.png`** — neatlogs Traces dashboard showing the TenantGuard remediation run (status ✓, input "You are a security remediation…", output "Rel: invoicely/app.py…") | Confirms neatlogs captured the live Bedrock run |
| 4 | **Entire use** (checkpoint) | commit `41fa5d7` on `main` carries `Entire-Checkpoint: 01M4N1E31ZDTBN9KSD51Z1640Z` (synced to origin) | **ID `01M4N1E31ZDTBN9KSD51Z1640Z`** · link **https://entire.io/gh/JMadhan1/tenantguard/commit/41fa5d7108dc3f1d24684a2313dd430aa84a7c6d** · verify: `entire checkpoint explain HEAD` |
| 5 | **cfo.ai use** (business plan) | **cfo.ai exports in `docs/evidence/`: `cfo-tenantguard-plan.xlsx`, `cfo-tenantguard-revenue.xlsx`, `cfo-tenantguard-cash.xlsx`** + `BUSINESS_PLAN.md` | cfo.ai-built model: inputs ARPA $650, token $0.005/attempt, compute $0.030/fix, $50K/mo burn, $900K launch cash, 1% churn; 36-month cash reconciliation; low/base/high scenarios + top-risk flag. cfo.ai share link: LINK · add a UI screenshot to `docs/evidence/` to prove cfo.ai use |
| 6 | **Recovery** (a failed action + what it did next) | `docs/report.html` timeline; `artifacts/<run>/report.json` (`verify: regressed` → `classify_failure` → `verify: fixed`) | Watch the naive fix regress, revert, and the tenant-scoped fix pass · demo timestamp LINK |
| 7 | **Public repo, event-dated commits** | GitHub repo | Commits dated 2026-10-10..12 · **https://github.com/JMadhan1/tenantguard** |
| 8 | **Demo video (≤3 min)** | Loom recording | **https://www.loom.com/share/5a96c2f1a02e4450875d58c6affd943a** |
| ✓ | **Live hosted dashboard (hardened)** | `site/` on Vercel | **https://tenantguard.jmadhan.me** — strict CSP (no inline JS/CSS), HSTS preload, X-Frame-Options DENY, locked Permissions-Policy, `/.well-known/security.txt` |
| 9 | **Building in public (#neatHack)** | `docs/BUILD_IN_PUBLIC.md` → posts | 4–6 posts with real artifacts · LINKs |

## Honesty notes
- The offline run uses a scripted brain (clearly labeled); **live-model evidence** for #1–#3 must come from a genuine `--live` run.
- The deterministic verifier owns "fixed": security **and** functionality tests must pass; the tool never claims success on the exploit test alone.
- No secrets in code, traces, checkpoints, or screenshots; all fixture data is synthetic.
