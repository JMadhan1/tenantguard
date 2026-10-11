"use strict";
(function () {
  var PHASE = {
    intake: "Intake", baseline_tests: "Baseline tests", inspect_code: "Inspect code",
    propose_patch: "Propose patch", apply_in_worktree: "Apply in worktree",
    apply_failed: "Apply failed", verify: "Verify", classify_failure: "Classify + revert",
    export_report: "Export report", human_review: "Human review"
  };

  var runBtn = document.getElementById("runBtn");
  var statusLine = document.getElementById("statusLine");
  var modeHint = document.getElementById("modeHint");
  var timeline = document.getElementById("timeline");
  var emptyRow = document.getElementById("emptyRow");
  var verdict = document.getElementById("verdict");
  var verdictEmpty = document.getElementById("verdictEmpty");
  var stamp = document.getElementById("stamp");
  var kv = document.getElementById("kv");
  var diffEl = document.getElementById("diff");
  var es = null;

  function setStatus(d) {
    var live = d && d.live;
    statusLine.innerHTML =
      '<span class="dot' + (live ? "" : " replay") + '"></span>' +
      (live ? "Live · Claude Opus 4.6 on AWS Bedrock" : "Replay mode (operator hasn't set live credentials)") +
      (d ? "  ·  " + d.daily_live_used + "/" + d.daily_live_cap + " live runs today" : "");
  }
  fetch("/api/status").then(function (r) { return r.json(); }).then(setStatus).catch(function () {
    statusLine.innerHTML = '<span class="dot replay"></span>ready';
  });

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
    var li = document.createElement("li");
    li.className = "tl-row " + rowClass(ev.phase, ev.detail || "");
    var note = ev.detail || "";
    if (ev.phase === "classify_failure") note = "reverted the regressing patch — recovery";
    li.innerHTML =
      '<span class="tl-dot"></span>' +
      '<span class="tl-label">' + (PHASE[ev.phase] || ev.phase) + "</span>" +
      '<span class="tl-note"></span>';
    li.querySelector(".tl-note").textContent = note;
    timeline.appendChild(li);
    timeline.scrollTop = timeline.scrollHeight;
  }

  function fmtDiff(diff) {
    diffEl.textContent = "";
    if (!diff) { diffEl.hidden = true; return; }
    diff.split("\n").forEach(function (ln) {
      var span = document.createElement("span");
      span.className = "dl";
      if (ln[0] === "+" && ln.slice(0, 3) !== "+++") span.className += " ins";
      else if (ln[0] === "-" && ln.slice(0, 3) !== "---") span.className += " del";
      else if (ln.slice(0, 2) === "@@") span.className += " hunk";
      span.textContent = ln || " ";
      diffEl.appendChild(span);
    });
    diffEl.hidden = false;
  }

  function showVerdict(d) {
    var ok = d.status === "fixed";
    stamp.textContent = ok ? "SEALED" : (d.status || "incomplete").toUpperCase();
    stamp.className = "stamp" + (ok ? "" : " bad");
    var rows = [
      ["Status", d.status],
      ["Mode", d.mode === "live" ? "live · Bedrock Opus 4.6" : "scripted replay"],
      ["Patch attempts", d.attempts],
      ["Baseline", d.baseline ? (d.baseline.passed + " passed / " + d.baseline.failed + " failed") : "—"],
      ["Security tests", d.security_pass ? "pass" : "fail"],
      ["Functionality tests", d.functionality_pass ? "pass" : "fail"],
      ["neatlogs traced", d.neatlogs ? "yes" : "no"]
    ];
    if (d.cost_usd != null) rows.push(["Cost / fix", "$" + Number(d.cost_usd).toFixed(4)]);
    kv.innerHTML = "";
    rows.forEach(function (r) {
      var div = document.createElement("div");
      div.className = "kv";
      div.innerHTML = "<span></span><b></b>";
      div.children[0].textContent = r[0];
      div.children[1].textContent = r[1];
      kv.appendChild(div);
    });
    fmtDiff(d.diff);
    verdictEmpty.style.display = "none";
    verdict.classList.add("show");
  }

  function finish() {
    if (es) { es.close(); es = null; }
    runBtn.disabled = false;
    runBtn.textContent = "▶ Run again";
  }

  runBtn.addEventListener("click", function () {
    if (es) return;
    runBtn.disabled = true;
    runBtn.textContent = "Running…";
    timeline.innerHTML = "";
    emptyRow = null;
    verdict.classList.remove("show");
    verdictEmpty.style.display = "";
    verdictEmpty.textContent = "Running…";

    es = new EventSource("/api/stream?case_id=invoicely-idor-001");
    es.addEventListener("start", function (e) {
      var d = JSON.parse(e.data);
      modeHint.textContent = d.mode === "live"
        ? "Live run on " + d.model + " — every row is real backend state."
        : "Replay of a real run (" + d.model + ") — operator hasn't enabled live credentials.";
    });
    es.addEventListener("phase", function (e) { addPhase(JSON.parse(e.data)); });
    es.addEventListener("done", function (e) { showVerdict(JSON.parse(e.data)); finish(); });
    es.addEventListener("busy", function (e) {
      verdictEmpty.textContent = JSON.parse(e.data).message; finish();
    });
    es.addEventListener("error", function (e) {
      // SSE fires 'error' on normal close too; only surface if nothing streamed
      if (!verdict.classList.contains("show")) { verdictEmpty.textContent = "Connection ended. Try again."; }
      finish();
    });
  });
})();
