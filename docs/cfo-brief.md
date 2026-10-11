# cfo.ai — paste-ready brief for TenantGuard

Paste the block below into cfo.ai (as the business description / prompt), then let it
build the pricing, cost, revenue and runway model. The cost-per-fix numbers are **measured**
from real live runs (Claude Opus 4.6 on AWS Bedrock), not guessed.

---

**Business:** TenantGuard — "self-verifying security remediation." A bot that watches CI; when a
tenant-isolation / broken-object-level-authorization (IDOR) bug is found, it reproduces the leak,
writes a minimal fix, proves no legitimate access regressed (a deterministic verifier requires both
security AND functionality tests to pass), and opens a PR for human review. Patch-only, never
auto-merges.

**Customer:** B2B SaaS security & platform teams, 10–200 engineers (Python/JS first).

**Pricing (hybrid seat + usage):**
- Team $499/mo — 1 repo, 40 remediations/mo
- Business $1,900/mo — up to 8 repos, 200 remediations/mo, SSO, audit export
- Enterprise from $5,000/mo — self-host, custom detectors, SLA
- Overage: $12 per remediation beyond plan

**Measured cost per remediation (COGS driver = LLM tokens):**
- Live run, Claude Opus 4.6 on AWS Bedrock: ~$0.005 per fix (improved agent), ~$0.0044 (baseline agent)
- Verifier / CI compute: ~$0.03 per fix
- So COGS ≈ $0.035 per remediation today; gross margin on included usage is >95%

**Costs:** team of 3 (2 founders + 1 security engineer), fully-loaded burn ≈ $50K/mo.
**Raise:** seed $900K.

**Model these scenarios (low / base / high):**
- Customers at month 12: 40 / 120 / 260
- Blended ARPA: $450 / $650 / $850
- Avg attempts per fix: 4–6 / 2–3 / 2 (more attempts = higher token COGS; include the point where
  runaway retries make the unit economics unattractive — the attempt-budget cap is the control)

**Output wanted:** pricing recommendation, gross margin, monthly revenue ramp, and cash runway
(months) for each scenario, plus the one assumption that most threatens the business.

---

## What to do with the result
1. Export cfo.ai's plan/output (PDF or screenshot) into `docs/evidence/cfo-plan.*`.
2. Note the cfo.ai project link for the submission.
3. Full narrative version is in `../BUSINESS_PLAN.md`.
