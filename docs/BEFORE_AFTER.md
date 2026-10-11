# Before / After — the measured agent improvement

Two real runs on the same fixture (`invoicely-idor-001`). Reproduce with the commands at the bottom.

## The improvement: a deterministic verifier + verify-and-recover loop

- **Before** = a naive agent that trusts the model's first patch (no recovery budget).
- **After** = TenantGuard, which re-runs the full suite after each edit and **reverts a patch that regresses legitimate access**, then applies a tenant-scoped fix.

| Metric | Before (naive) | After (TenantGuard) |
|---|---|---|
| Final status | `needs_review` | `fixed` |
| Security tests — cross-tenant denied | ✅ pass | ✅ pass |
| Functionality tests — legitimate access | ❌ **fail (regressed)** | ✅ pass |
| Regression shipped | **yes — 1** | none (caught & reverted) |
| Patch attempts | 1 | 2 |

**Why it matters:** the naive agent **closes the leak but breaks legitimate same-tenant access** — it would look "fixed" if you only checked the exploit test. TenantGuard's verifier requires **both** security *and* functionality to pass, so it catches the regression, reverts, and applies the correct tenant-scoped fix. That is the difference between an autonomous fix you can trust and one you can't.

Evidence files: `docs/evidence/before-naive.json`, `docs/evidence/after-recover.json`.

## Live model cost (AWS Bedrock · Claude Opus 4.6 · ap-south-1)

Real traced runs (neatlogs on):

| Prompt | Tokens in/out | Cost / fix | Attempts | Status |
|---|---|---|---|---|
| baseline | 1075 / 221 | **$0.0044** | 1 | fixed |
| improved | 1128 / 273 | **$0.0050** | 1 | fixed |

Opus 4.6 is capable enough to fix this case correctly in one attempt, so it does not trip the recovery trap naturally — the recovery above is shown with a clearly-labeled fault-injection scenario, which the neatHack brief explicitly permits. Evidence: `docs/evidence/live-bedrock-run.json`.

## Reproduce

```bash
python run_case.py --max-attempts 1    # BEFORE: naive agent ships a regression (needs_review)
python run_case.py --max-attempts 3    # AFTER:  verify-and-recover reaches fixed
python run_case.py --live              # live on AWS Bedrock, traced by neatlogs
python report.py                       # -> docs/report.html
```
