# Setup — step by step (Windows)

Steps marked **(you)** need your login/payment/recording; the rest are one command.

## 0. Install deps
```bash
pip install -r requirements.txt
```

## 1. Offline demo (works now, no keys)
```bash
python run_case.py            # reproduce → regression → recover → fixed
python report.py              # → docs/report.html
python -m pytest tests/ -q    # offline agent tests
```

## 2. Anthropic key **(you)**
1. console.anthropic.com → API keys → create.
2. `cp .env.example .env`, paste into `ANTHROPIC_API_KEY`.
3. Confirm the model/spend cap with the team, then:
   ```bash
   python run_case.py --live --model claude-haiku-5-5   # cheap validation first
   ```

## 3. neatlogs **(you + one command)**
1. app.neatlogs.com → sign in → create org + project.
2. Settings → API keys → paste into `.env` as `NEATLOGS_API_KEY`.
3. `python run_case.py --live` and confirm the trace appears under **Traces**.
4. Before/after:
   ```bash
   python run_case.py --live --quality baseline
   python run_case.py --live --quality improved
   ```
   Save both trace links; screenshot the recovery (regression → revert) span.

## 4. Entire **(you + commands)** — see `docs/ENTIRE.md`
```powershell
# Windows / Scoop
scoop bucket add entire https://github.com/entireio/scoop-bucket.git
scoop install entire/cli
entire version
```
```bash
entire enable -y --agent claude-code
# ...do a coding session that implements/fixes the agent, then:
git add -A && git commit -m "TenantGuard: implement remediation agent"
entire checkpoint list
entire checkpoint explain HEAD
entire status
```
Save an accessible checkpoint link + ID. **Review captured prompts/transcripts for secrets before making them public.**

## 5. cfo.ai **(you)** — **do NOT enter a card**
Ask the neatHack organizers in Discord for the credit/access route first. Once you have access, enter the `BUSINESS_PLAN.md` numbers (using measured cost-per-fix from `artifacts/*/report.json`), and export the plan into `docs/evidence/`.

## 6. Public repo + demo + posts **(you)**
- Push to a public GitHub repo (commits dated during the event).
- Record the ≤3-min demo (`docs/DEMO_SCRIPT.md`).
- Publish the #neatHack posts (`docs/BUILD_IN_PUBLIC.md`).
- Submit by quote-posting the official neatlogs post **Mon 7:00–11:55 PM IST**; verify it actually posted.
