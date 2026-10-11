# Building in public — #neatHack (15% + Community prize)

Post from your own account with real artifacts (screenshots/clips). Tag **#neatHack** and **@neatlogs @entire** and the cfo.ai handle. Reply to other neatHack posts. **Bought engagement disqualifies** — keep it genuine. Save every link for the submission.

**1 — Kickoff.**
> Day 1 of #neatHack, team AI LONE STAR. Building **TenantGuard**: a security agent you can trust to run unattended. Give it a repo where Tenant A can read Tenant B's invoice — it reproduces the leak, fixes it, and catches its own mistakes. 🧵

**2 — The leak (failures are good content).**
> Baseline: `2 failed, 6 passed`. The 2 failures are a real IDOR — a cross-tenant read returns 200 instead of 403. Encoded the *intended* behavior as tests first. [screenshot] #neatHack

**3 — The recovery (money shot).**
> This is the part I love. TenantGuard's first fix closes the leak but **breaks legitimate same-tenant access**. It notices, reverts, and applies a tenant-scoped fix instead. Unattended. [15–30s clip of the timeline] #neatHack

**4 — before/after (the real improvement).**
> Ran TenantGuard two ways. A naive agent "fixes" the IDOR but silently **breaks legitimate same-tenant access** — a false fix (`needs_review`). TenantGuard's verifier demands security AND functionality both pass, so it catches the regression, reverts, and fixes it right (`fixed`). Traced in @neatlogs. #neatHack

**5 — Entire.**
> Every fix is backed by an @entire checkpoint — the captured coding session that shows *how* and *why* the change was made, tied to the commit. [checkpoint link] #neatHack

**6 — cfo.ai + hosting.**
> Modeled TenantGuard in cfo.ai: measured cost-per-fix (~$0.005 on Bedrock Opus 4.6) → pricing → margin → runway, incl. the scenario where runaway retries kill the economics.
> Live, hardened dashboard: https://tenantguard.jmadhan.me #neatHack

**7 — Submission (quote-post the official neatlogs post).**
> 🛡️ Submitting **TenantGuard** for #neatHack — a security agent that fixes tenant-isolation (IDOR) bugs and **recovers from its own mistakes**, verified by tests not vibes.
> Live: https://tenantguard.jmadhan.me
> Code: https://github.com/JMadhan1/tenantguard
> Demo: [video link]
> Team AI LONE STAR · @neatlogs @entire

Cadence (today = Oct 11): post 1–5 through today, 6 + the **submission quote-post on Oct 12, 7:00 PM IST** (first 50 quote tweets get sponsor engagement — submit early in the window).
