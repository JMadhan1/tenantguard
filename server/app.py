"""TenantGuard — the live app (FastAPI + SSE).

One place for everything: visitors click "Run" and watch the REAL agent
(Claude Opus 4.6 on AWS Bedrock, traced in neatlogs) remediate the tenant-
isolation case live, phase by phase — plus links to every piece of evidence.

Safety & cost guardrails (a public button that calls Bedrock must be bounded):
  * only allowlisted fixture cases run — never a visitor's code or repo
  * hard daily run cap + per-IP cooldown + concurrency cap
  * when the live budget is exhausted (or no server creds), it streams a
    faithful scripted replay of a real run, clearly labelled
  * strict security headers on every response; no secrets; synthetic data only
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from tenantguard_agent.brain import OfflineBrain, LLMBrain, detect_backend
from tenantguard_agent.cases import CASES
from tenantguard_agent.graph import build_graph

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")

MAX_CONCURRENCY = int(os.environ.get("TENANTGUARD_MAX_CONCURRENCY", "2"))
DAILY_CAP = int(os.environ.get("TENANTGUARD_DAILY_LIVE_CAP", "100"))   # max real Bedrock runs / day
IP_COOLDOWN = int(os.environ.get("TENANTGUARD_IP_COOLDOWN", "20"))     # seconds between runs per IP
PHASE_DELAY = float(os.environ.get("TENANTGUARD_PHASE_DELAY", "0.5"))  # scripted replay pacing

_SEM = threading.Semaphore(MAX_CONCURRENCY)
_LOCK = threading.Lock()
_ip_last: dict[str, float] = {}
_day = {"date": _dt.date.today(), "live_runs": 0}


def _live_available() -> bool:
    has_creds = bool(os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY")) \
        or bool(os.environ.get("ANTHROPIC_API_KEY"))
    with _LOCK:
        if _day["date"] != _dt.date.today():
            _day["date"] = _dt.date.today()
            _day["live_runs"] = 0
        return has_creds and _day["live_runs"] < DAILY_CAP


def _note_live_run():
    with _LOCK:
        _day["live_runs"] += 1


app = FastAPI(title="TenantGuard", docs_url=None, redoc_url=None, openapi_url=None)

CSP = (
    "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'; "
    "img-src 'self' data:; media-src 'self' https:; style-src 'self' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; "
    "frame-src https://www.loom.com; object-src 'none'; upgrade-insecure-requests"
)
SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "X-XSS-Protection": "0",
}


@app.middleware("http")
async def security_headers(request, call_next):
    resp = await call_next(request)
    for k, v in SECURITY_HEADERS.items():
        resp.headers.setdefault(k, v)
    return resp


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/api/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/status")
def status():
    live = _live_available()
    with _LOCK:
        used = _day["live_runs"]
    return {"live": live, "model": "claude-opus-4-6 (AWS Bedrock)" if live else "scripted replay",
            "daily_live_used": used, "daily_live_cap": DAILY_CAP}


@app.get("/api/stream")
def stream(request: Request, case_id: str = Query("invoicely-idor-001")):
    if case_id not in CASES:
        raise HTTPException(status_code=400, detail="unknown case_id")
    ip = (request.client.host if request.client else "?")

    def gen():
        now = time.time()
        with _LOCK:
            last = _ip_last.get(ip, 0)
        if now - last < IP_COOLDOWN:
            yield _sse("busy", {"message": f"Please wait {IP_COOLDOWN - int(now-last)}s between runs."})
            return
        if not _SEM.acquire(blocking=False):
            yield _sse("busy", {"message": "All run slots are busy — try again in a few seconds."})
            return
        with _LOCK:
            _ip_last[ip] = now

        run_id = f"run-{uuid.uuid4().hex[:8]}"
        live = _live_available()
        try:
            if live:
                _note_live_run()
                brain = LLMBrain(model=os.environ.get("TENANTGUARD_MODEL", "global.anthropic.claude-opus-4-6-v1"),
                                 quality="improved", backend=detect_backend())
                mode = "live"
            else:
                brain = OfflineBrain(naive_first=True)
                mode = "replay"
            yield _sse("start", {"run_id": run_id, "case_id": case_id, "mode": mode,
                                 "model": "Claude Opus 4.6 · AWS Bedrock" if live else "scripted replay of a real run"})

            graph = build_graph()
            initial = {"run_id": run_id, "case_id": case_id, "brain": brain,
                       "max_attempts": 3, "events": []}
            last_state = None
            emitted = 0
            for state in graph.stream(initial, stream_mode="values", config={"recursion_limit": 60}):
                last_state = state
                events = state.get("events", [])
                for ev in events[emitted:]:
                    yield _sse("phase", ev)
                    if not live:
                        time.sleep(PHASE_DELAY)
                emitted = len(events)

            wt = (last_state or {}).get("worktree")
            verdict = (last_state or {}).get("verdict") or {}
            llm = getattr(brain, "input_tokens", None)
            cost = None
            if live and hasattr(brain, "input_tokens"):
                from tenantguard_agent.pricing import cost_usd
                cost = cost_usd(brain.model, brain.input_tokens, brain.output_tokens)
            final = {
                "run_id": run_id, "mode": mode,
                "status": (last_state or {}).get("status"),
                "attempts": (last_state or {}).get("attempt"),
                "baseline": {"passed": len((last_state or {}).get("baseline_passed", [])),
                             "failed": len((last_state or {}).get("baseline_failed", []))},
                "security_pass": verdict.get("security_pass"),
                "functionality_pass": verdict.get("functionality_pass"),
                "cost_usd": round(cost, 6) if cost is not None else None,
                "neatlogs": getattr(brain, "neatlogs_enabled", False),
                "diff": wt.diff() if wt else "",
            }
            yield _sse("done", final)
            if wt:
                wt.cleanup()
            if live:
                try:
                    import neatlogs
                    neatlogs.flush()
                except Exception:
                    pass
        except Exception as e:  # pragma: no cover
            yield _sse("error", {"message": f"run failed: {type(e).__name__}: {e}"})
        finally:
            _SEM.release()

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/", StaticFiles(directory=STATIC), name="static")
