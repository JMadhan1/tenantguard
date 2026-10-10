# TenantGuard — Business Plan (for cfo.ai)

> Load into **cfo.ai** (via the organizer-provided neatHack access — **do not enter a card**) to model pricing, cost, revenue and runway. Replace the illustrative token/cost numbers with the measured values from your live `artifacts/*/report.json` (`llm.cost_usd`).

## 1. Customer & problem
Broken object-level authorization / tenant-isolation (IDOR) is a top real-world vulnerability class. Security teams at B2B SaaS companies (10–200 engineers) spend expensive senior time triaging, fixing, and *proving* such fixes didn't break legitimate access. TenantGuard automates the remediation loop with checkable evidence and a patch-only, never-auto-merge workflow.

## 2. Product & pricing
**TenantGuard — self-verifying security remediation.** Opens a branch, reproduces the vuln, fixes it, proves no regression, and attaches an evidence report for human review.

| Plan | Price | Included |
|---|---|---|
| Team | **$499 / mo** | 1 repo, 40 remediations/mo, Slack/PR integration |
| Business | **$1,900 / mo** | up to 8 repos, 200 remediations/mo, SSO, audit export |
| Enterprise | from **$5,000 / mo** | self-host, custom detectors, SLA |

Overage: **$12 per remediation** beyond plan.

## 3. Cost per fix — measured, not guessed
The dominant variable cost is **LLM tokens per remediation**, which TenantGuard records in each run (`report.json → llm`).

| | baseline agent | improved agent |
|---|---|---|
| Patch attempts (incl. recovery) | 3 | 2 |
| Tokens per fix (illustrative) | ~45K | ~22K |
| Model cost / fix (`claude-sonnet-5-5` @ $2/$10 per MTok) | ~$0.18 | ~$0.09 |
| Verifier/CI compute / fix | ~$0.03 | ~$0.03 |
| **COGS / fix** | **~$0.21** | **~$0.12** |

> Reading the neatlogs trace and tightening the prompt (fewer attempts, no wasted re-reads) roughly **halves cost per fix** — the same improvement that satisfies the hackathon's before/after evidence.

## 4. Unit economics (Team plan, 40 remediations)
- Revenue: $499/mo. COGS at improved agent: 40 × $0.12 = **$4.80** → **gross margin ≈ 99%** on included usage.
- Even at heavy overage (say 300 remediations), COGS ≈ $36 → margin stays >90%.
- **Where it breaks:** if average attempts balloon (e.g. a hard detector family needs 8–12 model calls per fix) COGS/fix can hit ~$1–2; at very high volume on the cheapest plan, margin compresses. The attempt-budget + verifier cap is the control that protects margin — model this as the low scenario.

## 5. Scenarios (12-mo, illustrative)
| | Low | Base | High |
|---|---|---|---|
| Customers @ M12 | 40 | 120 | 260 |
| Blended ARPA | $450 | $650 | $850 |
| MRR @ M12 | $18K | $78K | $221K |
| Avg attempts/fix | 4–6 | 2–3 | 2 |
| Gross margin | ~82% | ~94% | ~97% |

## 6. Costs & runway
- Team: 2 founders + 1 security engineer; burn ≈ **$50K/mo**.
- Seed raise **$900K** → ~18 months gross runway; base-case M6 MRR offsets most burn, extending effective runway past 24 months.
- The improved-agent COGS reduction is a direct runway extender at every revenue level.

## 7. One line for the judges
> neatlogs measures cost per fix, cfo.ai turns that into margin and runway, and Entire proves exactly how the fix was built — observability, pricing, and provenance as one loop.

*Remember: resolve cfo.ai access via the organizers in Discord; cancel immediately if a card was ever required. A locally generated spreadsheet does not count as cfo.ai evidence.*
