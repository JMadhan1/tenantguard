# Entire — coding provenance for TenantGuard

Entire captures *how and why* the agent code was written and ties it to commits. It is **not** a runtime dependency of the agent — it documents the coding sessions.

## One-time
```powershell
scoop bucket add entire https://github.com/entireio/scoop-bucket.git
scoop install entire/cli
entire version
```
Sign in at entire.io with GitHub; a GitHub org admin installs the Entire app and imports the repo (sync can take up to an hour).

## In this repo
```bash
entire enable -y --agent claude-code
```

## Capture checkpoints over real coding sessions
Do a focused coding session (e.g. implement a node, or fix a bug you found in a neatlogs trace), then commit. A checkpoint needs captured agent context **and** a commit.
```bash
git add -A
git commit -m "TenantGuard: <focused change>"
entire checkpoint list
entire checkpoint explain HEAD
entire status
```
Aim for several small, checkpoint-backed commits across the event rather than one big commit.

## For the submission
- Save an **accessible checkpoint link** and its **checkpoint ID** (from `entire checkpoint list`).
- Link format after you publish the repo: `https://entire.io/gh/OWNER/REPO/commit/FULL_SHA`.
- **Review captured prompts/transcripts for secrets before making anything public.** All fixture data here is synthetic; keep it that way in traces and checkpoints.
- Optional, only after the MVP is solid: `entire plugin install graph` + `entire graph init-agents --repo .` for an architecture map. Don't sink hours into every Entire product.
