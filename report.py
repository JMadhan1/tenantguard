"""Render an animated, self-contained HTML dashboard from a TenantGuard run.

    python report.py                # newest run in artifacts/
    python report.py run-1234abcd   # a specific run

Writes docs/report.html — no server, no build step, works offline. A single
light "incident dossier" treatment with meaningful motion (reduced-motion safe).
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
        num = f"{i + 1:02d}"
        rows.append(
            f'<li class="tl-row {kind}" style="--i:{i}">'
            f'<span class="tl-num">{num}</span><span class="tl-dot"></span>'
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
        "{{STATUS_WORD}}": "SEALED" if fixed else d["status"].upper(),
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


# Single deliberate light "incident dossier" world: paper ground + blueprint grid,
# serif display headline, forensic mono labels, a SEALED rubber-stamp.
TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>TenantGuard Dossier</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,900&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root{
  --paper:#f3f4f9; --panel:#ffffff; --ink:#15192a; --muted:#5c6579;
  --line:#e3e6f1; --rule:#c7cde0; --accent:#2f49d8;
  --breach:#d12338; --secure:#0e9b67; --warn:#b4690e;
  --serif:'Fraunces',Georgia,'Times New Roman',serif;
  --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
  --sans:'IBM Plex Sans',system-ui,-apple-system,Segoe UI,sans-serif;
  color-scheme:light;
}
*{box-sizing:border-box}
body{margin:0;color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5;
  -webkit-font-smoothing:antialiased;
  background-color:var(--paper);
  background-image:linear-gradient(var(--line) 1px,transparent 1px),
    linear-gradient(90deg,var(--line) 1px,transparent 1px);
  background-size:28px 28px;background-position:-1px -1px}
.wrap{max-width:1020px;margin:0 auto;padding-block:26px;padding-inline:16px}

/* dossier header strip */
.strip{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;
  font-family:var(--mono);font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted);border-bottom:2px solid var(--ink);padding-bottom:10px;margin-bottom:0}
.strip b{color:var(--ink)}
.strip .file{color:var(--accent)}

/* hero */
.hero{position:relative;background:var(--panel);border:1px solid var(--line);
  border-top:none;border-radius:0 0 18px 18px;padding:30px 26px 26px;overflow:hidden}
.hero h1{font-family:var(--serif);font-weight:900;font-size:clamp(34px,6.5vw,62px);line-height:.98;
  letter-spacing:-.015em;margin:4px 0 14px;max-width:15ch;text-wrap:balance}
.hero p{color:var(--muted);margin:0;max-width:58ch;font-size:15.5px}
.status{display:inline-flex;align-items:center;gap:11px;margin-top:18px;font-family:var(--mono);font-size:13px;
  background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:8px 13px}
.b-old{color:var(--breach);text-decoration:line-through;animation:fade 1.1s ease-out 1}
.b-new{color:var(--secure);font-weight:600}
.b-new .lock{display:inline-block;animation:popIn .5s cubic-bezier(.2,1.5,.3,1) .55s both}
.arrow{color:var(--rule)}
@keyframes fade{0%,55%{opacity:1}100%{opacity:.55}}
@keyframes popIn{from{transform:scale(.3);opacity:0}to{transform:scale(1);opacity:1}}

/* SEALED rubber stamp */
.stamp{position:absolute;top:22px;right:22px;font-family:var(--mono);font-weight:600;
  color:var(--secure);border:3px double var(--secure);border-radius:8px;
  padding:7px 14px 5px;font-size:15px;letter-spacing:.22em;text-transform:uppercase;
  transform:rotate(-9deg);opacity:.92;animation:stamp .5s cubic-bezier(.2,1.3,.3,1) .9s both;
  box-shadow:0 0 0 2px color-mix(in srgb,var(--secure) 12%,transparent) inset}
.stamp small{display:block;font-size:8.5px;letter-spacing:.14em;color:var(--muted);text-align:center;margin-top:2px}
@keyframes stamp{0%{transform:rotate(-9deg) scale(2.1);opacity:0}
  65%{transform:rotate(-9deg) scale(.9);opacity:.92}100%{transform:rotate(-9deg) scale(1);opacity:.92}}

/* kpi ledger */
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin-top:14px;
  background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden}
@media(max-width:760px){.kpis{grid-template-columns:repeat(2,1fr)}}
.kpi{padding:16px 17px;border-right:1px solid var(--line);position:relative;
  opacity:0;transform:translateY(9px);animation:rise .55s ease-out forwards}
.kpi:last-child{border-right:0}
@media(max-width:760px){.kpi:nth-child(2n){border-right:0}.kpi:nth-child(-n+2){border-bottom:1px solid var(--line)}}
.kpi:nth-child(1){animation-delay:.12s}.kpi:nth-child(2){animation-delay:.2s}
.kpi:nth-child(3){animation-delay:.28s}.kpi:nth-child(4){animation-delay:.36s}
.kpi-label{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.11em;color:var(--muted)}
.kpi-value{font-family:var(--serif);font-weight:900;font-size:32px;line-height:1.05;margin:7px 0 3px;
  font-variant-numeric:tabular-nums}
.kpi.good .kpi-value{color:var(--secure)}.kpi.crit .kpi-value{color:var(--breach)}
.kpi.warn .kpi-value{color:var(--warn)}.kpi.accent .kpi-value{color:var(--accent)}
.kpi-sub{font-size:12px;color:var(--muted)}
@keyframes rise{to{opacity:1;transform:none}}

.grid{display:grid;grid-template-columns:1.2fr 1fr;gap:14px;margin-top:14px}
@media(max-width:820px){.grid{grid-template-columns:1fr}}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px 20px;min-width:0}
.panel h3{font-family:var(--serif);font-weight:900;font-size:19px;margin:0 0 3px;letter-spacing:-.01em}
.panel .hint{color:var(--muted);font-size:12.5px;margin:0 0 14px}

/* evidence log */
ul.tl{list-style:none;margin:0;padding:0;position:relative}
.tl-row{display:grid;grid-template-columns:26px 14px 134px 1fr;gap:9px;align-items:start;padding:8px 0;
  border-bottom:1px solid var(--line);opacity:0;transform:translateX(-7px);
  animation:slide .5s ease-out forwards;animation-delay:calc(.45s + var(--i)*.085s)}
.tl-row:last-child{border-bottom:0}
@keyframes slide{to{opacity:1;transform:none}}
.tl-num{font-family:var(--mono);font-size:11px;color:var(--rule);margin-top:3px}
.tl-dot{width:9px;height:9px;border-radius:50%;background:var(--muted);margin-top:6px;outline:3px solid var(--panel)}
.tl-label{font-weight:600;font-size:13.5px}
.tl-note{color:var(--muted);font-size:13px;min-width:0}
.tl-row.pass .tl-dot{background:var(--secure)}
.tl-row.fail .tl-dot{background:var(--breach)}
.tl-row.recover{background:color-mix(in srgb,var(--warn) 11%,transparent);border-radius:8px;
  padding-inline:7px;border-bottom-color:transparent;box-shadow:inset 3px 0 0 var(--warn)}
.tl-row.recover .tl-dot{background:var(--warn);animation:ping 1.5s ease-out infinite}
.tl-row.recover .tl-note{color:var(--warn);font-weight:600}
@keyframes ping{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--warn) 55%,transparent)}
  70%{box-shadow:0 0 0 7px transparent}100%{box-shadow:0 0 0 0 transparent}}

.vm-group{margin-bottom:12px}
.vm-group h4{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:0 0 7px}
.vm-group ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:5px}
.vm-group li{display:flex;align-items:center;gap:8px;font-size:13px}
.vm-check{width:17px;height:17px;flex:none;border-radius:5px;display:grid;place-items:center;font-size:11px;color:#fff;background:var(--secure)}
.vm-group li.bad .vm-check{background:var(--breach)}
.vm-name{flex:1 1 auto;min-width:0}
.vm-tag{font-family:var(--mono);font-size:10.5px;color:var(--muted);white-space:nowrap}
.vm-tag.closed{color:var(--secure);font-weight:600}

.diffwrap{margin-top:14px}
h2.sec{font-family:var(--serif);font-weight:900;font-size:21px;margin:26px 0 10px;letter-spacing:-.01em}
pre.diff{background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:15px;overflow-x:auto;
  font-family:var(--mono);font-size:12.5px;line-height:1.55;margin:0}
.dl{display:block;white-space:pre}
.dl.ins{color:var(--secure)}.dl.del{color:var(--breach)}.dl.hunk{color:var(--accent)}

.loop{margin-top:16px;display:flex;align-items:center;gap:9px;flex-wrap:wrap;font-family:var(--mono);font-size:12px;color:var(--muted);
  background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:11px 14px}
.loop b{color:var(--ink)}.loop .arrow{color:var(--accent)}
.foot{color:var(--muted);font-size:11.5px;margin-top:22px;font-family:var(--mono)}

@media (prefers-reduced-motion:reduce){
  *{animation:none!important}
  .kpi,.tl-row{opacity:1!important;transform:none!important}
  .stamp{opacity:.92!important;transform:rotate(-9deg)!important}
}
</style>
</head>
<body>
<div class="wrap">
  <div class="strip">
    <span><b>TenantGuard</b> // Incident Dossier</span>
    <span>Case <span class="file">{{CASE}}</span> &nbsp;·&nbsp; Status <b>{{STATUS_WORD}}</b></span>
  </div>
  <div class="hero">
    <div class="stamp">{{STATUS_WORD}}<small>verified by tests</small></div>
    <h1>Cross-tenant read, sealed.</h1>
    <p>An authenticated user from one tenant could read another tenant's invoice. TenantGuard
    reproduced the leak, caught its own first fix breaking legitimate same-tenant access, reverted,
    and applied a tenant-scoped fix — verified by a deterministic verifier, not by the model.</p>
    <div class="status">
      <span class="b-old">GET /invoices/inv-a1 as t2 → 200 OK</span>
      <span class="arrow">→</span>
      <span class="b-new"><span class="lock">\U0001F512</span> 403 Forbidden</span>
    </div>
  </div>

  <div class="kpis">{{KPIS}}</div>

  <div class="grid">
    <div class="panel">
      <h3>Remediation log</h3>
      <p class="hint">Every entry is real backend state · recovery: {{RECOVERED}}.</p>
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
