"use strict";
(function () {
  // plain-language labels so a first-time visitor follows along
  var LABEL = {
    intake: "Set up a safe sandbox",
    baseline_tests: "Run the security tests",
    inspect_code: "Read the app's code",
    propose_patch: "Write a fix",
    apply_in_worktree: "Apply the fix",
    apply_failed: "Fix couldn't apply",
    verify: "Re-check every test",
    classify_failure: "Caught a mistake — undo it",
    export_report: "Done — write the report",
    human_review: "Flag for a human"
  };

  var runBtn = document.getElementById("runBtn");
  var statusLine = document.getElementById("statusLine");
  var modeHint = document.getElementById("modeHint");
  var consoleEl = document.getElementById("console");
  var alarm = document.getElementById("alarm");
  var timeline = document.getElementById("timeline");
  var emptyRow = document.getElementById("emptyRow");
  var summary = document.getElementById("summary");
  var verdict = document.getElementById("verdict");
  var verdictEmpty = document.getElementById("verdictEmpty");
  var stamp = document.getElementById("stamp");
  var kv = document.getElementById("kv");
  var diffWrap = document.getElementById("diffWrap");
  var diffEl = document.getElementById("diff");
  var es = null, idx = 0;

  function setStatus(d) {
    var live = d && d.live;
    statusLine.innerHTML = '<span class="dot' + (live ? "" : " replay") + '"></span>' +
      (live ? "Live · Claude Opus 4.6 on AWS Bedrock" : "Replay mode (operator hasn't set live credentials)") +
      (d ? "  ·  " + d.daily_live_used + "/" + d.daily_live_cap + " live runs today" : "");
  }
  fetch("/api/status").then(function (r) { return r.json(); }).then(setStatus)
    .catch(function () { statusLine.innerHTML = '<span class="dot replay"></span>ready'; });

  function rowClass(ph, detail) {
    if (ph === "classify_failure") return "recover";
    if (ph === "verify" && /regressed/.test(detail)) return "fail";
    if (ph === "verify" && /fixed/.test(detail)) return "pass";
    if (ph === "export_report") return "pass";
    if (ph === "apply_failed" || ph === "human_review") return "fail";
    return "step";
  }

  function addPhase(ev) {
    if (emptyRow) { emptyRow.remove(); emptyRow = null; }
    idx += 1;
    var li = document.createElement("li");
    li.className = "tl-row " + rowClass(ev.phase, ev.detail || "");
    li.innerHTML = '<span class="tl-idx"></span><span class="tl-dot"></span><span class="tl-label"></span><span class="tl-note"></span>';
    li.children[0].textContent = String(idx).padStart(2, "0");
    li.children[2].textContent = LABEL[ev.phase] || ev.phase;
    var note = ev.detail || "";
    if (ev.phase === "classify_failure") note = "reverting the fix that broke legitimate access";
    li.children[3].textContent = note;
    timeline.appendChild(li);

    // the signature drama: alarm on self-inflicted regression, clear on recovery
    if (ev.phase === "verify" && /regressed/.test(ev.detail || "")) {
      consoleEl.classList.add("alarm");
      alarm.textContent = "⚠ The agent's own fix blocked the leak but broke legitimate access. It will undo it and try again.";
      alarm.classList.add("show");
    } else if (ev.phase === "verify" && /fixed/.test(ev.detail || "")) {
      consoleEl.classList.remove("alarm");
      alarm.classList.remove("show");
    }
  }

  function fmtDiff(diff) {
    diffEl.textContent = "";
    if (!diff) { diffWrap.hidden = true; return; }
    diff.split("\n").forEach(function (ln) {
      var s = document.createElement("span"); s.className = "dl";
      if (ln[0] === "+" && ln.slice(0, 3) !== "+++") s.className += " ins";
      else if (ln[0] === "-" && ln.slice(0, 3) !== "---") s.className += " del";
      else if (ln.slice(0, 2) === "@@") s.className += " hunk";
      s.textContent = ln || " ";
      diffEl.appendChild(s);
    });
    diffWrap.hidden = false;
  }

  function showVerdict(d) {
    consoleEl.classList.remove("alarm"); alarm.classList.remove("show");
    var ok = d.status === "fixed";
    stamp.textContent = ok ? "SEALED" : (d.status || "incomplete").toUpperCase().replace("_", " ");
    stamp.className = "stamp" + (ok ? "" : " bad");

    var msg;
    if (ok) {
      msg = "✅ Leak closed — cross-tenant access is now blocked and legitimate access still works, confirmed by the tests"
        + ((d.attempts || 1) > 1 ? ", after the agent caught and undid a bad fix" : "") + ".";
      if (d.mode === "live") msg += " Real run on Claude Opus 4.6" + (d.neatlogs ? ", traced in neatlogs" : "")
        + (d.cost_usd != null ? ", for $" + Number(d.cost_usd).toFixed(4) : "") + ".";
    } else {
      msg = "⚠ Not shipped. The agent couldn't prove a safe fix, so it flagged it for a human instead of guessing.";
    }
    summary.textContent = msg;
    summary.className = "summary show" + (ok ? "" : " bad");

    var rows = [
      ["Result", d.status],
      ["Mode", d.mode === "live" ? "live · Bedrock Opus 4.6" : "scripted replay"],
      ["Attempts", d.attempts],
      ["Starting tests", d.baseline ? (d.baseline.passed + " passed / " + d.baseline.failed + " failed") : "—"],
      ["Blocks cross-tenant", d.security_pass ? "yes" : "no"],
      ["Keeps legit access", d.functionality_pass ? "yes" : "no"],
      ["Traced in neatlogs", d.neatlogs ? "yes" : "no"]
    ];
    if (d.cost_usd != null) rows.push(["Cost / fix", "$" + Number(d.cost_usd).toFixed(4)]);
    kv.innerHTML = "";
    rows.forEach(function (r) {
      var div = document.createElement("div"); div.className = "kv";
      div.innerHTML = "<span></span><b></b>";
      div.children[0].textContent = r[0]; div.children[1].textContent = r[1];
      kv.appendChild(div);
    });
    fmtDiff(d.diff);
    verdictEmpty.style.display = "none";
    verdict.classList.add("show");
  }

  function finish() { if (es) { es.close(); es = null; } runBtn.disabled = false; runBtn.textContent = "▶ Run it again"; }

  runBtn.addEventListener("click", function () {
    if (es) return;
    runBtn.disabled = true; runBtn.textContent = "Running…";
    timeline.innerHTML = ""; emptyRow = null; idx = 0;
    consoleEl.classList.remove("alarm"); alarm.classList.remove("show");
    verdict.classList.remove("show"); summary.classList.remove("show");
    verdictEmpty.style.display = ""; verdictEmpty.textContent = "Running…";

    es = new EventSource("/api/stream?case_id=invoicely-idor-001");
    es.addEventListener("start", function (e) {
      var d = JSON.parse(e.data);
      modeHint.textContent = d.mode === "live"
        ? "Live run on " + d.model + " — every line is real backend state."
        : "Replay of a real run — the operator hasn't enabled live credentials.";
    });
    es.addEventListener("phase", function (e) { addPhase(JSON.parse(e.data)); });
    es.addEventListener("done", function (e) { showVerdict(JSON.parse(e.data)); finish(); });
    es.addEventListener("busy", function (e) { verdictEmpty.textContent = JSON.parse(e.data).message; finish(); });
    es.addEventListener("error", function () {
      if (!verdict.classList.contains("show")) verdictEmpty.textContent = "Connection ended — please try again.";
      finish();
    });
  });
})();
