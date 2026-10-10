"""Render an animated, self-contained HTML dashboard from a TenantGuard run.

    python report.py                # newest run in artifacts/
    python report.py run-1234abcd   # a specific run

Writes docs/report.html — no server, no build step, works offline. Editorial
"incident resolved" treatment with meaningful motion (reduced-motion safe).
"""

import glob
import html
import json
import os
import sys

PHASE_LABEL = {
    "intake": "Intake", "baseline_tests": "Baseline tests", "inspect_code": "Inspect code",
    "propose_patch": "Propose patch", "apply_in_worktree": "Apply in worktree",
    "apply_failed": "Apply failed", "verify": "Verify", "classify_failure": "Classify + revert",
    "export_report": "Export report", "human_review": "Human review",
}


def pick_report(arg):
    if arg:
        return os.path.join("artifacts", arg, "report.json")
    reports = glob.glob("artifacts/*/report.json")
    if not reports:
        sys.exit("no runs in artifacts/. Run: python run_case.py")
    return max(reports, key=os.path.getmtime)


def timeline_rows(events):
    rows = []
    for i, e in enumerate(events):
        ph, dt = e["phase"], e.get("detail", "")
        label = PHASE_LABEL.get(ph, ph)
        kind, note = "step", html.escape(dt)
        if ph == "classify_failure":
            kind, note = "recover", "Reverted the regressing patch — recovery"
        elif ph == "verify" and "regressed" in dt:
            kind, note = "fail", "Regression: a passing test broke (functionality=False)"
        elif ph == "verify" and "fixed" in dt:
            kind, note = "pass", "Security and functionality both pass"
        elif ph == "export_report":
            kind = "pass"
        elif ph in ("apply_failed", "human_review"):
            kind = "fail"
        rows.append(
            f'<li class="tl-row {kind}" style="--i:{i}">'
            f'<span class="tl-dot"></span>'
            f'<span class="tl-label">{html.escape(label)}</span>'
            f'<span class="tl-note">{note}</span></li>'
        )
    return "\n".join(rows)


def verdict_matrix(v):
    sec_fixed = set(v.get("security_fixed", []))
    still = set(v.get("still_failing", []))
    cats = [
        ("Security — access denied", [
            "test_cross_tenant_read_blocked_carol_to_t1",
            "test_cross_tenant_read_blocked_alice_to_t2",
            "test_unauthenticated_denied", "test_invalid_token_denied"]),
        ("Functionality — access preserved", [
            "test_owner_reads_own_invoice", "test_same_tenant_other_user_allowed",
            "test_carol_reads_own_invoice", "test_unknown_invoice_not_found"]),
    ]
    out = []
    for title, tests in cats:
        items = []
        for t in tests:
            ok = t not in still
            tag = "closed the leak" if t in sec_fixed else ("pass" if ok else "fail")
            tagcls = "closed" if t in sec_fixed else ("ok" if ok else "bad")
            nice = t.replace("test_", "").replace("_", " ")
            check = "✓" if ok else "✕"
            licls = "ok" if ok else "bad"
            items.append(
                f'<li class="{licls}"><span class="vm-check">{check}</span>'
                f'<span class="vm-name">{html.escape(nice)}</span>'
                f'<span class="vm-tag {tagcls}">{tag}</span></li>')
        out.append(f'<div class="vm-group"><h4>{html.escape(title)}</h4><ul>{"".join(items)}</ul></div>')
    return "".join(out)


def fmt_diff(diff):
    if not diff:
        return "(no diff)"
    out = []
    for ln in diff.splitlines():
        esc = html.escape(ln) or "&nbsp;"
        cls = ""
        if ln.startswith("+") and not ln.startswith("+++"):
            cls = "ins"
        elif ln.startswith("-") and not ln.startswith("---"):
            cls = "del"
        elif ln.startswith("@@"):
            cls = "hunk"
        out.append(f'<span class="dl {cls}">{esc}</span>')
    return "\n".join(out)


def kpi(label, value, tone, sub, count=None):
    data = f' data-count="{count}"' if count is not None else ""
    return (f'<div class="kpi {tone}"><div class="kpi-label">{html.escape(label)}</div>'
            f'<div class="kpi-value"{data}>{value}</div>'
            f'<div class="kpi-sub">{html.escape(sub)}</div></div>')


def build(d, diff):
    v = d.get("verdict") or {}
    llm = d.get("llm")
    fixed = d["status"] == "fixed"
    had_regression = any("regressed" in e.get("detail", "") for e in d["events"])

    kpis = [
        kpi("Verdict", "Fixed" if fixed else d["status"].title(),
            "good" if fixed else "crit", "security + functionality"),
        kpi("Security", "Pass" if v.get("security_pass") else "Fail",
            "good" if v.get("security_pass") else "crit", "cross-tenant reads blocked"),
        kpi("Functionality", "Pass" if v.get("functionality_pass") else "Fail",
            "good" if v.get("functionality_pass") else "crit", "legitimate access preserved"),
    ]
    if llm and llm.get("cost_usd") is not None:
        kpis.append(kpi("Cost / fix", f'${llm["cost_usd"]:.4f}', "accent",
                        f'{llm.get("model","").split(".")[-1]} on Bedrock'))
    else:
        kpis.append(kpi("Attempts", str(d["attempts"]), "warn" if had_regression else "accent",
                        "1 regression recovered" if had_regression else "clean", count=d["attempts"]))

    if llm:
        model_line = (f'{html.escape(str(llm.get("model")))} · {html.escape(str(llm.get("quality")))} prompt '
                      f'· {llm.get("input_tokens",0):,}/{llm.get("output_tokens",0):,} tok '
                      f'· neatlogs {"on" if llm.get("neatlogs") else "off"}')
    else:
        model_line = "offline scripted run (no LLM) — token &amp; cost come from a live run"

    tmpl = TEMPLATE
    repl = {
        "{{CASE}}": html.escape(d["case_id"]),
        "{{STATUS_WORD}}": "SECURED" if fixed else d["status"].upper(),
        "{{KPIS}}": "".join(kpis),
        "{{TIMELINE}}": timeline_rows(d["events"]),
        "{{VERDICT}}": verdict_matrix(v),
        "{{DIFF}}": fmt_diff(diff),
        "{{MODEL}}": model_line,
        "{{RUNID}}": html.escape(d["run_id"]),
        "{{WALL}}": str(d.get("wall_seconds")),
        "{{RECOVERED}}": "yes — caught &amp; reverted" if had_regression else "not needed",
    }
    for k, val in repl.items():
        tmpl = tmpl.replace(k, val)
    return tmpl


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>TenantGuard Console</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800;900&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
/* dark-first "incident resolved" security console: hero seal, KPI band, timeline | verdict, patch */
:root{
  --bg:#0a0e17; --bg2:#0d1220; --surface:#121829; --surface-2:#0f1524; --fg:#eaeef8;
  --muted:#8894ad; --line:#232c42; --accent:#5b8cff;
  --breach:#ff4d61; --secure:#27d49f; --warn:#f6b34b;
  --display:'Archivo',system-ui,-apple-system,Segoe UI,sans-serif;
  --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
  color-scheme:dark;
}
@media (prefers-color-scheme:light){:root:not([data-theme="dark"]){
  --bg:#f4f6fb; --bg2:#eef1f8; --surface:#ffffff; --surface-2:#f7f9fd; --fg:#141a28;
  --muted:#5b6578; --line:#e3e7f0; --accent:#3a63d8;
  --breach:#d7263d; --secure:#0fa37f; --warn:#c2820a; color-scheme:light;
}}
:root[data-theme="light"]{
  --bg:#f4f6fb; --bg2:#eef1f8; --surface:#ffffff; --surface-2:#f7f9fd; --fg:#141a28;
  --muted:#5b6578; --line:#e3e7f0; --accent:#3a63d8;
  --breach:#d7263d; --secure:#0fa37f; --warn:#c2820a; color-scheme:light;
}
*{box-sizing:border-box}
body{margin:0;background:
  radial-gradient(1200px 600px at 80% -10%, color-mix(in srgb,var(--accent) 12%,transparent), transparent 60%),
  var(--bg);
  color:var(--fg);font-family:var(--display);font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding-block:26px;padding-inline:16px}

/* hero */
.hero{position:relative;background:linear-gradient(180deg,var(--bg2),var(--surface));
  border:1px solid var(--line);border-radius:20px;padding:26px 24px;overflow:hidden}
.hero::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:repeating-linear-gradient(90deg,transparent 0 38px,color-mix(in srgb,var(--fg) 3%,transparent) 38px 39px);
  opacity:.35;mask:linear-gradient(90deg,transparent,#000 30%,#000 70%,transparent)}
.eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
.hero h1{font-size:clamp(28px,5vw,44px);font-weight:900;letter-spacing:-.02em;line-height:1.02;margin:10px 0 8px;
  text-wrap:balance;max-width:16ch}
.hero p{color:var(--muted);margin:0;max-width:56ch}
.hero-grid{display:grid;grid-template-columns:1fr auto;gap:20px;align-items:center;position:relative;z-index:1}
@media(max-width:640px){.hero-grid{grid-template-columns:1fr}}
/* breach -> secured status line */
.status{display:inline-flex;align-items:center;gap:10px;margin-top:16px;font-family:var(--mono);
  font-size:13px;background:var(--surface-2);border:1px solid var(--line);border-radius:999px;padding:7px 13px}
.status .arrow{color:var(--muted)}
.b-old{color:var(--breach);text-decoration:line-through;opacity:.9;animation:breachPulse 1.1s ease-out 1}
.b-new{color:var(--secure);font-weight:600}
.b-new .lock{display:inline-block;animation:popIn .5s cubic-bezier(.2,1.4,.3,1) .5s both}
@keyframes breachPulse{0%,60%{opacity:1}100%{opacity:.6}}
@keyframes popIn{from{transform:scale(.4);opacity:0}to{transform:scale(1);opacity:1}}
/* seal */
.seal{width:118px;height:118px;flex:none;justify-self:end}
.seal .ring{stroke:var(--secure);stroke-width:2.5;fill:none;stroke-linecap:round;
  stroke-dasharray:300;stroke-dashoffset:300;animation:draw 1.1s ease-out .15s forwards}
.seal .body{fill:color-mix(in srgb,var(--secure) 14%,transparent)}
.seal .tick{stroke:var(--secure);stroke-width:3.4;fill:none;stroke-linecap:round;stroke-linejoin:round;
  stroke-dasharray:40;stroke-dashoffset:40;animation:draw .5s ease-out 1s forwards}
@keyframes draw{to{stroke-dashoffset:0}}

/* kpi band */
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:14px}
@media(max-width:760px){.kpis{grid-template-columns:repeat(2,1fr)}}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:15px;padding:15px;position:relative;overflow:hidden;
  opacity:0;transform:translateY(10px);animation:rise .6s ease-out forwards}
.kpi:nth-child(1){animation-delay:.15s}.kpi:nth-child(2){animation-delay:.25s}
.kpi:nth-child(3){animation-delay:.35s}.kpi:nth-child(4){animation-delay:.45s}
.kpi::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--muted)}
.kpi.good::before{background:var(--secure)}.kpi.crit::before{background:var(--breach)}
.kpi.warn::before{background:var(--warn)}.kpi.accent::before{background:var(--accent)}
.kpi-label{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted)}
.kpi-value{font-weight:800;font-size:30px;line-height:1.1;margin:6px 0 2px;font-variant-numeric:tabular-nums}
.kpi-sub{font-size:12px;color:var(--muted)}
@keyframes rise{to{opacity:1;transform:none}}

.grid{display:grid;grid-template-columns:1.2fr 1fr;gap:14px;margin-top:14px}
@media(max-width:820px){.grid{grid-template-columns:1fr}}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:17px 19px;min-width:0}
.panel h3{font-weight:800;font-size:15px;margin:0 0 3px}
.panel .hint{color:var(--muted);font-size:12.5px;margin:0 0 13px}

ul.tl{list-style:none;margin:0;padding:0}
.tl-row{display:grid;grid-template-columns:16px 138px 1fr;gap:10px;align-items:start;padding:8px 0;
  border-bottom:1px dashed var(--line);opacity:0;transform:translateX(-8px);
  animation:slidein .5s ease-out forwards;animation-delay:calc(.5s + var(--i)*.09s)}
.tl-row:last-child{border-bottom:0}
@keyframes slidein{to{opacity:1;transform:none}}
.tl-dot{width:10px;height:10px;border-radius:50%;background:var(--muted);margin-top:5px}
.tl-label{font-weight:700;font-size:13.5px}
.tl-note{color:var(--muted);font-size:13px;min-width:0}
.tl-row.pass .tl-dot{background:var(--secure)}
.tl-row.fail .tl-dot{background:var(--breach)}
.tl-row.recover{background:color-mix(in srgb,var(--warn) 13%,transparent);border-radius:9px;
  padding-inline:8px;border-bottom-color:transparent;box-shadow:inset 3px 0 0 var(--warn)}
.tl-row.recover .tl-dot{background:var(--warn);animation:ping 1.4s ease-out infinite}
.tl-row.recover .tl-note{color:var(--warn);font-weight:600}
@keyframes ping{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--warn) 60%,transparent)}
  70%{box-shadow:0 0 0 7px transparent}100%{box-shadow:0 0 0 0 transparent}}

.vm-group{margin-bottom:12px}
.vm-group h4{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin:0 0 7px}
.vm-group ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:5px}
.vm-group li{display:flex;align-items:center;gap:8px;font-size:13px}
.vm-check{width:17px;height:17px;flex:none;border-radius:5px;display:grid;place-items:center;font-size:11px;color:#071018;background:var(--secure)}
.vm-group li.bad .vm-check{background:var(--breach);color:#fff}
.vm-name{flex:1 1 auto;min-width:0}
.vm-tag{font-family:var(--mono);font-size:10.5px;color:var(--muted);white-space:nowrap}
.vm-tag.closed{color:var(--secure);font-weight:600}

.diffwrap{margin-top:14px}
h2.sec{font-weight:800;font-size:16px;margin:26px 0 10px}
pre.diff{background:var(--surface-2);border:1px solid var(--line);border-radius:13px;padding:15px;overflow-x:auto;
  font-family:var(--mono);font-size:12.5px;line-height:1.55;margin:0}
.dl{display:block;white-space:pre}
.dl.ins{color:var(--secure)}.dl.del{color:var(--breach)}.dl.hunk{color:var(--accent)}

.loop{margin-top:16px;display:flex;align-items:center;gap:9px;flex-wrap:wrap;font-family:var(--mono);font-size:12px;color:var(--muted)}
.loop b{color:var(--fg)}.loop .arrow{color:var(--accent)}
.foot{color:var(--muted);font-size:11.5px;margin-top:22px;font-family:var(--mono)}

@media (prefers-reduced-motion:reduce){
  *{animation:none!important}
  .kpi,.tl-row{opacity:1!important;transform:none!important}
  .seal .ring,.seal .tick{stroke-dashoffset:0!important}
}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <div class="hero-grid">
      <div>
        <div class="eyebrow">Incident · {{CASE}} · {{STATUS_WORD}}</div>
        <h1>Cross-tenant read, sealed.</h1>
        <p>An authenticated user from one tenant could read another tenant's invoice. TenantGuard
        reproduced the leak, caught its own first fix breaking legitimate same-tenant access, reverted,
        and applied a tenant-scoped fix — verified by tests, not by the model.</p>
        <div class="status">
          <span class="b-old">GET /invoices/inv-a1 as t2 → 200 OK</span>
          <span class="arrow">→</span>
          <span class="b-new"><span class="lock">\U0001F512</span> 403 Forbidden</span>
        </div>
      </div>
      <svg class="seal" viewBox="0 0 64 64" aria-hidden="true">
        <path class="body" d="M32 4l22 8v16c0 14-9.4 23-22 29C19.4 51 10 42 10 28V12l22-8z"/>
        <path class="ring" d="M32 4l22 8v16c0 14-9.4 23-22 29C19.4 51 10 42 10 28V12l22-8z"/>
        <path class="tick" d="M22 32l7 7 13-15"/>
      </svg>
    </div>
  </div>

  <div class="kpis">{{KPIS}}</div>

  <div class="grid">
    <div class="panel">
      <h3>Remediation timeline</h3>
      <p class="hint">Every row is real backend state. Recovery is highlighted · recovery: {{RECOVERED}}.</p>
      <ul class="tl">{{TIMELINE}}</ul>
    </div>
    <div class="panel">
      <h3>Verdict</h3>
      <p class="hint">Success needs <b>both</b> groups green. The deterministic verifier owns this, not the model.</p>
      {{VERDICT}}
    </div>
  </div>

  <div class="diffwrap">
    <h2 class="sec">The patch it applied</h2>
    <pre class="diff">{{DIFF}}</pre>
  </div>

  <div class="loop"><b>neatlogs</b> observes <span class="arrow">→</span> <b>Entire</b> proves how it was built
    <span class="arrow">→</span> <b>cfo.ai</b> prices the cost per fix &nbsp;·&nbsp; {{MODEL}}</div>
  <p class="foot">run {{RUNID}} · {{WALL}}s · TenantGuard · neatHack 2026 · team AI LONE STAR</p>
</div>
<script>
(function(){
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  document.querySelectorAll('.kpi-value[data-count]').forEach(function(el){
    var target = parseInt(el.getAttribute('data-count'), 10);
    if (isNaN(target)) return;
    var start = performance.now(), dur = 850;
    function step(now){
      var p = Math.min((now-start)/dur, 1);
      el.textContent = Math.round(target * (1-Math.pow(1-p,3)));
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });
})();
</script>
</body>
</html>"""


def main():
    rp = pick_report(sys.argv[1] if len(sys.argv) > 1 else None)
    d = json.load(open(rp, encoding="utf-8"))
    run_dir = os.path.dirname(rp)
    diff = ""
    dp = os.path.join(run_dir, "patch.diff")
    if os.path.exists(dp):
        diff = open(dp, encoding="utf-8").read()
    doc = build(d, diff)
    os.makedirs("docs", exist_ok=True)
    out = os.path.join("docs", "report.html")
    open(out, "w", encoding="utf-8").write(doc)
    print(f"wrote {out} (from {rp})")


if __name__ == "__main__":
    main()
