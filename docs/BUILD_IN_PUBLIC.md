# Building in public — #neatHack (15% + Community prize)

Post from your own account with real artifacts (screenshots/clips). Tag **#neatHack** and **@neatlogs @entire** and the cfo.ai handle. Reply to other neatHack posts. **Bought engagement disqualifies** — keep it genuine. Save every link for the submission.

**1 — Kickoff.**
> Day 1 of #neatHack, team AI LONE STAR. Building **TenantGuard**: a security agent you can trust to run unattended. Give it a repo where Tenant A can read Tenant B's invoice — it reproduces the leak, fixes it, and catches its own mistakes. 🧵

**2 — The leak (failures are good content).**
> Baseline: `2 failed, 6 passed`. The 2 failures are a real IDOR — a cross-tenant read returns 200 instead of 403. Encoded the *intended* behavior as tests first. [screenshot] #neatHack

**3 — The recovery (money shot).**
> This is the part I love. TenantGuard's first fix closes the leak but **breaks legitimate same-tenant access**. It notices, reverts, and applies a tenant-scoped fix instead. Unattended. [15–30s clip of the timeline] #neatHack

**4 — neatlogs before/after.**
> Traced two versions of the agent in @neatlogs. baseline vs improved prompt: fewer attempts, ~half the tokens, lower cost per fix. Receipts: [trace links] #neatHack

**5 — Entire.**
> Every fix is backed by an @entire checkpoint — the captured coding session that shows *how* and *why* the change was made, tied to the commit. [checkpoint screenshot] #neatHack

**6 — cfo.ai + close.**
> Modeled TenantGuard in cfo.ai: cost-per-fix (measured in neatlogs) → pricing → margin → runway, with the scenario where runaway retries kill the economics. Repo + demo: [links] #neatHack

Cadence: Sat eve (1,2) · Sat night (3) · Sun (4,5) · Mon (6 + final submission post). Submit by quote-posting the official neatlogs post **Mon 7:00 PM IST** (first 50 quote tweets get sponsor engagement).
