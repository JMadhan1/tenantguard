# Contributing to TenantGuard

TenantGuard is an evidence-first security-remediation agent (neatHack 2026, team AI LONE STAR).
This guide covers running it locally.

## Prerequisites
- Python 3.11
- (For live runs) AWS Bedrock access to Claude Opus 4.6 in `ap-south-1`, or an Anthropic API key

## Install
```bash
pip install -r requirements.txt
```

## Run the offline demo (no API key, no cost)
A scripted brain drives the real harness — real pytest, a real regression, a real revert:
```bash
python run_case.py            # reproduce -> naive fix -> regression -> revert -> fixed
python report.py              # -> docs/report.html
```

## Run the tests
```bash
python -m pytest tests/ -q        # offline agent integration tests (5)
python -m pytest fixture/ -q      # the vulnerable fixture's tenant-isolation suite
```

## Run live (AWS Bedrock, Claude Opus 4.6)
```bash
cp .env.example .env              # add AWS keys + NEATLOGS_API_KEY (see docs/SETUP.md)
python scripts/smoke_bedrock.py   # one cheap call to confirm creds/region/model
python run_case.py --live         # live remediation, traced by neatlogs
```

## Before/after comparison
```bash
python run_case.py --max-attempts 1    # naive agent: ships a regression (needs_review)
python run_case.py --max-attempts 3    # TenantGuard: verify-and-recover reaches fixed
```

## Safety
The agent only edits a disposable worktree of the allowlisted fixture, never commits/pushes
on its own, and a deterministic verifier (security AND functionality tests) decides success.
See [`docs/SAFETY.md`](docs/SAFETY.md). All fixture data is synthetic — never commit real secrets.

## Project layout
See the table in [`README.md`](README.md). Build log: [`hackathon.md`](hackathon.md).
