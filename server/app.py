"""TenantGuard — the live app (FastAPI + SSE).

Multi-case security remediation with real-time analytics. Visitors pick a
vulnerability class (IDOR, SQLi, Path Traversal) and watch the REAL agent
(Claude Opus 4.6 on AWS Bedrock, traced in neatlogs) remediate it live,
phase by phase — plus links to every piece of evidence.

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

from tenantguard_agent.brain import OfflineBrain, LLMBrain, detect_backend, build_model_client
from tenantguard_agent.cases import CASES
from tenantguard_agent.graph import build_graph
from tenantguard_agent import scanner

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

# ---- Analytics tracking (in-memory, resets on deploy) -------------------------
_ANALYTICS = {
    "total": 0, "fixed": 0, "recovered": 0, "total_cost": 0.0,
    "by_case": {},
}


def _track_run(case_id: str, status: str, attempts: int, cost: float | None):
    with _LOCK:
        _ANALYTICS["total"] += 1
        if status == "fixed":
            _ANALYTICS["fixed"] += 1
        if attempts and attempts > 1 and status == "fixed":
            _ANALYTICS["recovered"] += 1
        if cost:
            _ANALYTICS["total_cost"] += cost
        c = _ANALYTICS["by_case"].setdefault(case_id, {
            "runs": 0, "fixed": 0, "recovered": 0,
        })
        c["runs"] += 1
        if status == "fixed":
            c["fixed"] += 1
        if attempts and attempts > 1 and status == "fixed":
            c["recovered"] += 1


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
    "img-src 'self' data:; media-src 'self' https:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; connect-src 'self'; "
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


@app.get("/api/cases")
def list_cases():
    """Return metadata for all allowlisted cases."""
    out = []
    for cid, c in CASES.items():
        out.append({
            "id": c.id,
            "vuln_class": getattr(c, "vuln_class", ""),
            "owasp": getattr(c, "owasp", ""),
            "security_tests": len(c.security_tests),
            "functionality_tests": len(c.functionality_tests),
            "issue_summary": c.issue[:120] + "...",
        })
    return out


@app.get("/api/analytics")
def analytics():
    """Real-time aggregate analytics across all runs."""
    with _LOCK:
        total = _ANALYTICS["total"]
        fixed = _ANALYTICS["fixed"]
        recovered = _ANALYTICS["recovered"]
        cost = _ANALYTICS["total_cost"]
        by_case = {k: dict(v) for k, v in _ANALYTICS["by_case"].items()}
    return {
        "total_runs": total,
        "fixed": fixed,
        "recovered": recovered,
        "fix_rate": round(fixed / total * 100, 1) if total else 0,
        "recovery_rate": round(recovered / total * 100, 1) if total else 0,
        "avg_cost": round(cost / fixed, 4) if fixed else 0,
        "total_cost": round(cost, 4),
        "by_case": by_case,
        "cases_available": len(CASES),
        "owasp_coverage": sorted(set(
            getattr(c, "owasp", "") for c in CASES.values() if getattr(c, "owasp", "")
        )),
    }


@app.get("/api/stream")
def stream(request: Request, case_id: str = Query("invoicely-idor-001")):
    if case_id not in CASES:
        raise HTTPException(status_code=400, detail="unknown case_id")
    ip = (request.client.host if request.client else "?")
    case_meta = CASES[case_id]

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
                brain = OfflineBrain(naive_first=True, case_id=case_id)
                mode = "replay"
            yield _sse("start", {
                "run_id": run_id, "case_id": case_id, "mode": mode,
                "vuln_class": getattr(case_meta, "vuln_class", ""),
                "owasp": getattr(case_meta, "owasp", ""),
                "model": "Claude Opus 4.6 · AWS Bedrock" if live else "scripted replay of a real run",
            })

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
            cost = None
            if live and hasattr(brain, "input_tokens"):
                from tenantguard_agent.pricing import cost_usd
                cost = cost_usd(brain.model, brain.input_tokens, brain.output_tokens)

            run_status = (last_state or {}).get("status")
            run_attempts = (last_state or {}).get("attempt")
            _track_run(case_id, run_status or "", run_attempts or 0, cost)

            final = {
                "run_id": run_id, "mode": mode, "case_id": case_id,
                "vuln_class": getattr(case_meta, "vuln_class", ""),
                "status": run_status,
                "attempts": run_attempts,
                "baseline": {"passed": len((last_state or {}).get("baseline_passed", [])),
                             "failed": len((last_state or {}).get("baseline_failed", []))},
                "security_pass": verdict.get("security_pass"),
                "functionality_pass": verdict.get("functionality_pass"),
                "regressions": verdict.get("regressions", []),
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


def _ai_summary(target, findings):
    """One bounded Bedrock call: plain-English risk assessment + top fixes."""
    try:
        client, _ = build_model_client("tenantguard-scan", detect_backend())
        lines = "\n".join(f"- [{f['severity']}] {f['title']} — {f['file']}:{f['line']}" for f in findings[:25])
        prompt = ("You are a senior security reviewer. Below are static-scan findings from a code "
                  "repository. In 2-3 sentences give a plain-English risk assessment, then list the top 3 "
                  "things to fix first (concrete, one line each). Do not invent findings.\n\nFindings:\n" + lines)
        resp = client.messages.create(
            model=os.environ.get("TENANTGUARD_MODEL", "global.anthropic.claude-opus-4-6-v1"),
            max_tokens=500, messages=[{"role": "user", "content": prompt}])
        return "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text").strip()
    except Exception as e:  # pragma: no cover
        return None


def _counts(findings):
    c = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        c[f["severity"]] = c.get(f["severity"], 0) + 1
    return c


@app.get("/api/scan")
def scan(request: Request, repo_url: str = Query(...)):
    """Clone a PUBLIC repo and stream security findings (read-only; never executes it)."""
    if not scanner.valid_repo_url(repo_url):
        raise HTTPException(status_code=400, detail="Provide a public https GitHub/GitLab/Bitbucket repo URL.")
    ip = request.client.host if request.client else "?"

    def gen():
        now = time.time()
        with _LOCK:
            last = _ip_last.get(ip, 0)
        if now - last < IP_COOLDOWN:
            yield _sse("busy", {"message": f"Please wait {IP_COOLDOWN - int(now-last)}s between scans."}); return
        if not _SEM.acquire(blocking=False):
            yield _sse("busy", {"message": "All scan slots are busy — try again shortly."}); return
        with _LOCK:
            _ip_last[ip] = now
        tmp = None
        try:
            yield _sse("start", {"target": repo_url})
            yield _sse("stage", {"msg": "Cloning repository (read-only)..."})
            try:
                tmp = scanner.clone_repo(repo_url)
            except ValueError as e:
                yield _sse("error", {"message": str(e)}); return
            findings = []
            scanned = 0
            import os as _os
            for rel, content in scanner.iter_files(_os.path.join(tmp, "repo")):
                scanned += 1
                for f in scanner.scan_text(rel, content):
                    findings.append(f)
                    yield _sse("finding", f)
                if scanned % 40 == 0:
                    yield _sse("stage", {"msg": f"Scanned {scanned} files, {len(findings)} findings..."})
            findings.sort(key=lambda f: scanner.severity_rank(f["severity"]))
            summary = None
            if _live_available() and findings:
                _note_live_run()
                yield _sse("stage", {"msg": "Asking Claude for a risk assessment..."})
                summary = _ai_summary(repo_url, findings)
            yield _sse("done", {"scanned": scanned, "count": len(findings),
                                "by_severity": _counts(findings), "summary": summary})
        except Exception as e:  # pragma: no cover
            yield _sse("error", {"message": f"scan failed: {type(e).__name__}"})
        finally:
            if tmp:
                import shutil as _sh
                _sh.rmtree(tmp, ignore_errors=True)
            _SEM.release()

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/scan-text")
def scan_text_endpoint(payload: dict):
    """Scan pasted code / .env / config (no clone)."""
    content = (payload or {}).get("content", "")
    name = (payload or {}).get("filename", "pasted.txt")
    if not content.strip():
        raise HTTPException(status_code=400, detail="Paste some code, a .env, or a config file.")
    if len(content) > 600_000:
        raise HTTPException(status_code=400, detail="Input too large (max ~600 KB).")
    findings = scanner.scan_text(name, content)
    findings.sort(key=lambda f: scanner.severity_rank(f["severity"]))
    summary = _ai_summary(name, findings) if (_live_available() and findings) else None
    if summary:
        _note_live_run()
    return {"scanned": 1, "count": len(findings), "findings": findings,
            "by_severity": _counts(findings), "summary": summary}


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/", StaticFiles(directory=STATIC), name="static")
