"use strict";
(function () {
  /* ================================================================
     TenantGuard — Frontend Controller
     Scroll reveal, animated counters, multi-case SSE, repo scanner
     ================================================================ */

  // ---- Phase labels for the timeline ---------------------------------
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
  var CASE_LABELS = {
    "invoicely-idor-001": "IDOR",
    "taskboard-sqli-001": "SQLi",
    "docshare-traversal-001": "Path Traversal"
  };

  // ---- DOM refs -------------------------------------------------------
  var $ = function (id) { return document.getElementById(id); };
  var statusLine = $("statusLine");
  var modeHint = $("modeHint");
  var consoleEl = $("console");
  var alarm = $("alarm");
  var timeline = $("timeline");
  var emptyRow = $("emptyRow");
  var summary = $("summary");
  var verdict = $("verdict");
  var verdictEmpty = $("verdictEmpty");
  var stamp = $("stamp");
  var kv = $("kv");
  var diffWrap = $("diffWrap");
  var diffEl = $("diff");
  var runBadge = $("runBadge");
  var es = null, idx = 0;
  var activeCaseId = "invoicely-idor-001";

  // ---- Scroll-reveal (IntersectionObserver) ---------------------------
  var revealObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("revealed");
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll("[data-reveal]").forEach(function (el) {
    revealObserver.observe(el);
  });

  // ---- Status check ---------------------------------------------------
  function setStatus(d) {
    var live = d && d.live;
    var dot = statusLine.querySelector(".status-dot");
    if (dot) dot.className = "status-dot" + (live ? "" : " replay");
    statusLine.innerHTML = '<span class="status-dot' + (live ? "" : " replay") + '"></span>' +
      (live ? "Live &middot; Claude Opus 4.6 on AWS Bedrock" : "Replay mode") +
      (d ? " &middot; " + d.daily_live_used + "/" + d.daily_live_cap + " live runs today" : "");
  }
  fetch("/api/status").then(function (r) { return r.json(); }).then(setStatus)
    .catch(function () { statusLine.textContent = "ready"; });

  // ---- Analytics refresh -----------------------------------------------
  function refreshAnalytics() {
    fetch("/api/analytics").then(function (r) { return r.json(); }).then(function (d) {
      animateCount($("kpiTotal"), d.total_runs || 0);
      var fixEl = $("kpiFixRate");
      if (fixEl) fixEl.textContent = d.total_runs ? d.fix_rate + "%" : "--";
      animateCount($("kpiRecovery"), d.recovered || 0);
      var costEl = $("kpiCost");
      if (costEl) costEl.textContent = d.avg_cost ? "$" + d.avg_cost.toFixed(4) : "--";
      var owEl = $("kpiOwasp");
      if (owEl) owEl.textContent = (d.owasp_coverage || []).length || 2;
      animateCount($("kpiScans"), d.scans || 0);
      animateCount($("kpiVisitors"), d.visits || 0);
      var uq = $("kpiUnique");
      if (uq) uq.textContent = d.unique_visitors || 0;
    }).catch(function () {});
  }
  // Record this visit, then show the fresh numbers.
  fetch("/api/track", { method: "POST" })
    .then(function () { refreshAnalytics(); })
    .catch(function () { refreshAnalytics(); });

  // ---- Animated counter -----------------------------------------------
  function animateCount(el, target) {
    if (!el) return;
    var current = parseInt(el.textContent) || 0;
    if (current === target) return;
    var step = Math.max(1, Math.ceil(Math.abs(target - current) / 20));
    var dir = target > current ? 1 : -1;
    function tick() {
      current += dir * step;
      if ((dir > 0 && current >= target) || (dir < 0 && current <= target)) {
        el.textContent = target;
        return;
      }
      el.textContent = current;
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  // ---- Case selection --------------------------------------------------
  var caseCards = document.querySelectorAll(".case-card");
  var caseButtons = document.querySelectorAll(".cc-btn");

  function selectCase(caseId) {
    activeCaseId = caseId;
    caseCards.forEach(function (c) {
      c.classList.toggle("active", c.getAttribute("data-case") === caseId);
    });
  }
  caseCards.forEach(function (card) {
    card.addEventListener("click", function (e) {
      if (e.target.tagName === "BUTTON") return;
      selectCase(card.getAttribute("data-case"));
    });
  });

  // ---- Timeline rendering -----------------------------------------------
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

    if (ev.phase === "verify" && /regressed/.test(ev.detail || "")) {
      consoleEl.classList.add("alarm");
      alarm.textContent = "The agent's own fix passed security but broke legitimate access. Reverting and retrying...";
      alarm.hidden = false;
      alarm.classList.add("show");
    } else if (ev.phase === "verify" && /fixed/.test(ev.detail || "")) {
      consoleEl.classList.remove("alarm");
      alarm.classList.remove("show");
    }
  }

  // ---- Diff rendering --------------------------------------------------
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

  // ---- Verdict display -------------------------------------------------
  function showVerdict(d) {
    consoleEl.classList.remove("alarm"); alarm.classList.remove("show");
    var ok = d.status === "fixed";
    stamp.textContent = ok ? "SEALED" : (d.status || "incomplete").toUpperCase().replace("_", " ");
    stamp.className = "verdict-stamp" + (ok ? "" : " bad");

    var vulnLabel = CASE_LABELS[d.case_id] || d.vuln_class || d.case_id;
    var msg;
    if (ok) {
      msg = "Leak closed — " + vulnLabel + " vulnerability blocked, legitimate access preserved, verified by deterministic tests"
        + ((d.attempts || 1) > 1 ? " — after catching and reverting its own bad fix" : "") + ".";
      if (d.mode === "live") msg += " Real run on Claude Opus 4.6" + (d.neatlogs ? ", traced in neatlogs" : "")
        + (d.cost_usd != null ? " for $" + Number(d.cost_usd).toFixed(4) : "") + ".";
    } else {
      msg = "Not shipped — the agent couldn't prove a safe fix for " + vulnLabel + ". Flagged for human review.";
    }
    summary.textContent = msg;
    summary.className = "verdict-summary show" + (ok ? "" : " bad");
    summary.hidden = false;

    var rows = [
      ["Vulnerability", vulnLabel],
      ["Result", d.status],
      ["Mode", d.mode === "live" ? "live / Bedrock Opus 4.6" : "scripted replay"],
      ["Attempts", d.attempts],
      ["Baseline tests", d.baseline ? (d.baseline.passed + " passed / " + d.baseline.failed + " failed") : "—"],
      ["Blocks vulnerability", d.security_pass ? "yes" : "no"],
      ["Keeps legit access", d.functionality_pass ? "yes" : "no"],
    ];
    if (d.regressions && d.regressions.length) rows.push(["Regressions caught", d.regressions.join(", ")]);
    if (d.neatlogs) rows.push(["Traced in neatlogs", "yes"]);
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

  // ---- Run management ---------------------------------------------------
  function disableButtons(disabled) {
    caseButtons.forEach(function (b) { b.disabled = disabled; });
  }
  function finish() {
    if (es) { es.close(); es = null; }
    disableButtons(false);
    refreshAnalytics();
  }

  function startRun(caseId) {
    if (es) return;
    selectCase(caseId);
    disableButtons(true);
    timeline.innerHTML = ""; emptyRow = null; idx = 0;
    consoleEl.classList.remove("alarm"); alarm.classList.remove("show"); alarm.hidden = true;
    verdict.classList.remove("show"); summary.classList.remove("show"); summary.hidden = true;
    verdictEmpty.style.display = ""; verdictEmpty.textContent = "Running...";
    runBadge.textContent = CASE_LABELS[caseId] || caseId;
    runBadge.hidden = false;

    document.getElementById("console-section").scrollIntoView({ behavior: "smooth", block: "start" });

    es = new EventSource("/api/stream?case_id=" + encodeURIComponent(caseId));
    es.addEventListener("start", function (e) {
      var d = JSON.parse(e.data);
      modeHint.textContent = d.mode === "live"
        ? "Live run on " + d.model + " — every line is real."
        : "Scripted replay of a real run (live credentials not set).";
    });
    es.addEventListener("phase", function (e) { addPhase(JSON.parse(e.data)); });
    es.addEventListener("done", function (e) { showVerdict(JSON.parse(e.data)); finish(); });
    es.addEventListener("busy", function (e) { verdictEmpty.textContent = JSON.parse(e.data).message; finish(); });
    es.addEventListener("error", function () {
      if (!verdict.classList.contains("show")) verdictEmpty.textContent = "Connection ended — try again.";
      finish();
    });
  }

  caseButtons.forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      startRun(btn.getAttribute("data-case"));
    });
  });

  // ---- Repo Scanner ----------------------------------------------------
  var scanBtn = $("scanBtn");
  var scanUrl = $("scanUrl");
  var scanResults = $("scanResults");
  var scanStats = $("scanStats");
  var scanFindings = $("scanFindings");
  var scanFindingsHead = $("scanFindingsHead");
  var scanSummary = $("scanSummary");
  var scanEvs = null;

  // Build a link to the exact file + line on the hosting provider, new tab.
  function fileUrl(repo, file, line) {
    if (!repo || !file) return null;
    var base = repo.replace(/\.git$/, "").replace(/\/+$/, "");
    var host = "";
    try { host = new URL(base).hostname.toLowerCase(); } catch (e) { return null; }
    var mid, frag = line ? "#L" + line : "";
    if (host.indexOf("gitlab") >= 0) { mid = "/-/blob/HEAD/"; }
    else if (host.indexOf("bitbucket") >= 0) { mid = "/src/HEAD/"; frag = line ? "#lines-" + line : ""; }
    else { mid = "/blob/HEAD/"; }  // github + default
    return base + mid + file.split("/").map(encodeURIComponent).join("/") + frag;
  }

  function sevLabel(s) { return (s || "").charAt(0).toUpperCase() + (s || "").slice(1); }

  function addFinding(repo, f) {
    if (scanFindingsHead) scanFindingsHead.hidden = false;
    var href = fileUrl(repo, f.file, f.line);
    var el = document.createElement(href ? "a" : "div");
    el.className = "sf-row";
    if (href) { el.href = href; el.target = "_blank"; el.rel = "noopener"; }
    el.innerHTML =
      '<span class="sf-sev ' + (f.severity || "low") + '">' + sevLabel(f.severity) + '</span>' +
      '<span class="sf-main"><span class="sf-title"></span>' +
      '<span class="sf-loc"></span></span>' +
      (href ? '<span class="sf-open">open &#8599;</span>' : '');
    el.querySelector(".sf-title").textContent = f.title || "Finding";
    el.querySelector(".sf-loc").textContent = f.file + (f.line ? ":" + f.line : "");
    scanFindings.appendChild(el);
  }

  function sevChips(by) {
    if (!by) return "";
    var order = ["critical", "high", "medium", "low"], out = "";
    order.forEach(function (s) {
      if (by[s]) out += '<span class="chip ' + s + '">' + by[s] + " " + sevLabel(s) + "</span>";
    });
    return out;
  }

  function resetScanBtn() {
    scanBtn.disabled = false;
    scanBtn.innerHTML = '<span class="sb-label">Scan repo</span>';
  }

  function runScan(url) {
    url = (url || "").trim();
    if (!url || scanEvs) return;
    // open the panel and jump to it so people see progress
    scanBtn.disabled = true;
    scanBtn.innerHTML = '<span class="sb-label">Scanning&hellip;</span>';
    scanResults.hidden = false;
    scanStats.innerHTML = '<span class="scan-run">Cloning repository (read-only)&hellip;</span>';
    scanFindings.innerHTML = ""; scanSummary.hidden = true; scanSummary.textContent = "";
    if (scanFindingsHead) scanFindingsHead.hidden = true;
    scanResults.scrollIntoView({ behavior: "smooth", block: "nearest" });

    var repo = url, count = 0;
    scanEvs = new EventSource("/api/scan?repo_url=" + encodeURIComponent(url));
    scanEvs.addEventListener("stage", function (e) {
      scanStats.innerHTML = '<span class="scan-run">' + JSON.parse(e.data).msg + '</span>';
    });
    scanEvs.addEventListener("finding", function (e) {
      count++;
      addFinding(repo, JSON.parse(e.data));
      scanStats.innerHTML = '<span class="scan-run">Scanning&hellip; ' + count + ' finding' + (count === 1 ? "" : "s") + ' so far</span>';
    });
    scanEvs.addEventListener("done", function (e) {
      var d = JSON.parse(e.data);
      var head = d.count
        ? '<b>' + d.count + '</b> finding' + (d.count === 1 ? "" : "s") + ' across <b>' + d.scanned + '</b> files'
        : '<b>No obvious issues</b> found across <b>' + d.scanned + '</b> files';
      scanStats.innerHTML = '<div class="scan-done">' + head + '</div><div class="scan-chips">' + sevChips(d.by_severity) + '</div>';
      if (d.summary) {
        scanSummary.innerHTML = '<div class="ss-head">&#129504; Claude’s fix summary</div><div class="ss-body"></div>';
        scanSummary.querySelector(".ss-body").textContent = d.summary;
        scanSummary.hidden = false;
      }
      scanEvs.close(); scanEvs = null; resetScanBtn();
    });
    scanEvs.addEventListener("busy", function (e) {
      scanStats.innerHTML = '<span class="scan-run">' + JSON.parse(e.data).message + '</span>';
      scanEvs.close(); scanEvs = null; resetScanBtn();
    });
    scanEvs.addEventListener("error", function () {
      if (!count) scanStats.innerHTML = '<span class="scan-run">Scan ended &mdash; check the URL is a public repo and try again.</span>';
      scanEvs.close(); scanEvs = null; resetScanBtn();
    });
  }

  if (scanBtn) scanBtn.addEventListener("click", function () { runScan(scanUrl.value); });
  if (scanUrl) scanUrl.addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); runScan(scanUrl.value); }
  });
  document.querySelectorAll(".scan-ex").forEach(function (b) {
    b.addEventListener("click", function () {
      var r = b.getAttribute("data-repo");
      if (scanUrl) scanUrl.value = r;
      runScan(r);
    });
  });

})();
