# Evidence index — claim → artifact → how judges verify

Fill the `LINK` placeholders as you capture evidence. Keep every link; never claim a private link is judge-accessible without checking.

| # | Required evidence | Artifact / where | How to verify |
|---|---|---|---|
| 1 | **Agent completes a substantial task** | `tenantguard_agent/` + demo video | Run `python run_case.py` → status `fixed`; watch the phase timeline |
| 2 | **Before/after improvement** (two neatlogs traces, numbers compared) | `python run_case.py --live --quality baseline` then `--quality improved`; `docs/report.html`; neatlogs | Compare attempts / tokens / cost-per-fix across the two traces · baseline LINK · improved LINK |
| 3 | **neatlogs use** (trace links/screenshots) | neatlogs dashboard project; `docs/evidence/` screenshots | Open the workflow traces; sanitized screenshots in repo if private · LINK |
| 4 | **Entire use** (checkpoints / entire-graph) | checkpoints over the coding sessions; `docs/ENTIRE.md` | `entire checkpoint list` + `entire checkpoint explain HEAD`; checkpoint link + ID · LINK |
| 5 | **cfo.ai use** (business plan) | `BUSINESS_PLAN.md` + cfo.ai export in `docs/evidence/` | Open the cfo.ai plan with measured cost-per-fix · LINK |
| 6 | **Recovery** (a failed action + what it did next) | `docs/report.html` timeline; `artifacts/<run>/report.json` (`verify: regressed` → `classify_failure` → `verify: fixed`) | Watch the naive fix regress, revert, and the tenant-scoped fix pass · demo timestamp LINK |
| 7 | **Public repo, event-dated commits** | GitHub repo | Commits dated 2026-10-10..12 · **https://github.com/JMadhan1/tenantguard** |
| 8 | **Demo video (≤3 min)** | `docs/DEMO_SCRIPT.md` → recording | LINK |
| 9 | **Building in public (#neatHack)** | `docs/BUILD_IN_PUBLIC.md` → posts | 4–6 posts with real artifacts · LINKs |

## Honesty notes
- The offline run uses a scripted brain (clearly labeled); **live-model evidence** for #1–#3 must come from a genuine `--live` run.
- The deterministic verifier owns "fixed": security **and** functionality tests must pass; the tool never claims success on the exploit test alone.
- No secrets in code, traces, checkpoints, or screenshots; all fixture data is synthetic.
