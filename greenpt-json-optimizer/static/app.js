/* ── Utilities ───────────────────────────────────────────────────────────── */
const $ = (id) => document.getElementById(id);
const fmtJSON = (v) => { try { return JSON.stringify(v, null, 2); } catch { return String(v); } };
const now = () => new Date().toLocaleTimeString("en-GB", { hour12: false });

/* Savings convention: positive = fewer tokens than baseline (good, ↓);
   negative = more tokens than baseline (bad, ↑). */
const savingsLabel = (pct) => {
  if (pct == null || isNaN(pct)) return "—";
  const v = Number(pct);
  if (v > 0) return `↓ ${v.toFixed(1)}%`;
  if (v < 0) return `↑ ${Math.abs(v).toFixed(1)}%`;
  return "0.0%";
};

/* ══════════════════════════════════════════════════════════════════════════
   TAB ROUTING
══════════════════════════════════════════════════════════════════════════ */
let _activeTab = "playground";

function switchTab(name) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  $(`page-${name}`).classList.add("active");
  document.querySelector(`[data-tab="${name}"]`).classList.add("active");
  _activeTab = name;
  if (name === "stats")   loadStats();
  if (name === "report")  loadDataset();
}

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});


/* ══════════════════════════════════════════════════════════════════════════
   SSE — PACKETS STREAM
══════════════════════════════════════════════════════════════════════════ */
let _packetCount = 0;
let _reportPacketTarget = null;  // set when report is running

function startSSE() {
  const es = new EventSource("/api/stream");

  es.onopen = () => {
    setPacketStatus("connected");
    $("live-dot").classList.add("connected");
  };
  es.onerror = () => {
    setPacketStatus("error");
    $("live-dot").classList.remove("connected");
  };

  es.onmessage = (e) => {
    let ev;
    try { ev = JSON.parse(e.data); } catch { return; }
    if (ev.type === "ping") return;

    _packetCount++;
    $("packet-count").textContent = `${_packetCount} event${_packetCount !== 1 ? "s" : ""}`;

    const row = buildPacketRow(ev);
    appendPacketRow($("packet-log"), row, true);

    // mirror to report progress log if a report is running
    if (_reportPacketTarget) {
      appendPacketRow(_reportPacketTarget, buildPacketRow(ev), false);
    }
  };
}

function setPacketStatus(s) {
  const el = $("packet-status");
  el.className = `packet-status ${s}`;
  el.textContent = s === "connected" ? "● Live" : s === "error" ? "⚠ Disconnected" : "Connecting…";
}

function buildPacketRow(ev) {
  const div = document.createElement("div");
  div.className = "packet-row";

  const typeClass = { request: "req", response: "res", result: "result", optimize_start: "meta",
                      optimize_done: "meta", report_start: "meta", report_done: "meta" }[ev.type] || "meta";

  let typeLabel = ev.type;
  let detail = "";
  let status = "";

  if (ev.type === "request") {
    typeLabel = "→ REQ";
    detail = `${ev.method} · ${ev.model} · ${ev.user_tokens} user tokens`;
    status = "";
  } else if (ev.type === "response") {
    typeLabel = "← RES";
    detail = `${ev.method} · ${ev.model} · ${ev.response_tokens} tokens · ${ev.elapsed_s}s`;
    status = ev.status;
  } else if (ev.type === "result") {
    typeLabel = "✓ DONE";
    detail = `${ev.method} · ${savingsLabel(ev.savings_pct)} wire compression · ${ev.tokens_before}→${ev.tokens_after} tokens`;
    status = ev.status;
  } else if (ev.type === "optimize_start") {
    typeLabel = "▶ START";
    detail = `optimize · method=${ev.method} → ${ev.chosen}`;
  } else if (ev.type === "optimize_done") {
    typeLabel = "■ END";
    detail = `optimize complete · ${savingsLabel(ev.savings_pct)} vs baseline · ${ev.elapsed_s}s`;
  } else if (ev.type === "report_start") {
    typeLabel = "▶ START";
    detail = `report · ${ev.total_rows} rows × 4 methods`;
  } else if (ev.type === "report_done") {
    typeLabel = "■ END";
    detail = `report complete · ${ev.results} results written`;
  }

  div.innerHTML = `
    <span class="p-time">${now()}</span>
    <span class="p-type ${typeClass}">${typeLabel}</span>
    <span class="p-method">${ev.method || ""}</span>
    <span class="p-detail" title="${detail}">${detail}</span>
    <span class="p-status ${ev.status === "ok" ? "ok" : ev.status ? "err" : ""}">${status}</span>
  `;
  return div;
}

function appendPacketRow(container, row, removeEmpty) {
  if (removeEmpty) {
    const empty = container.querySelector(".packet-empty");
    if (empty) empty.remove();
  }
  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
}

$("clear-packets").addEventListener("click", () => {
  $("packet-log").innerHTML = '<div class="packet-empty">Log cleared.</div>';
  _packetCount = 0;
  $("packet-count").textContent = "0 events";
});


/* ══════════════════════════════════════════════════════════════════════════
   PLAYGROUND — example loader + file import + optimize
══════════════════════════════════════════════════════════════════════════ */

async function loadExamples() {
  try {
    const data = await (await fetch("/api/examples")).json();
    const sel = $("example-select");
    // group by use_case
    const groups = {};
    data.forEach(r => {
      (groups[r.use_case] = groups[r.use_case] || []).push(r);
    });
    Object.entries(groups).forEach(([uc, rows]) => {
      const og = document.createElement("optgroup");
      og.label = uc.replace(/_/g, " ");
      rows.forEach(r => {
        const o = document.createElement("option");
        o.value = JSON.stringify({ prompt: r.prompt, schema: r.schema });
        o.textContent = `${r.id} (${r.size})`;
        og.appendChild(o);
      });
      sel.appendChild(og);
    });
  } catch (_) {}
}

$("example-select").addEventListener("change", (e) => {
  if (!e.target.value) return;
  try {
    const ex = JSON.parse(e.target.value);
    $("prompt").value = ex.prompt;
    $("schema").value = JSON.stringify(ex.schema, null, 2);
    e.target.value = "";
  } catch (_) {}
});

$("file-import").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => { $("prompt").value = ev.target.result; };
  reader.readAsText(file);
  e.target.value = "";
});

const showError  = (msg) => { const el = $("error"); el.textContent = msg; el.classList.remove("hidden"); };
const clearError = () => $("error").classList.add("hidden");

async function runOptimization() {
  clearError();
  const btn     = $("run-btn");
  const prompt  = $("prompt").value.trim();
  const schemaRaw = $("schema").value.trim();
  const method  = $("method").value;

  if (!prompt) { showError("Prompt is required."); return; }

  let schema;
  try { schema = JSON.parse(schemaRaw); }
  catch (e) { showError("Schema is not valid JSON: " + e.message); return; }

  btn.disabled = true;
  btn.textContent = "Running…";

  try {
    const resp = await fetch("/api/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, schema, method }),
    });
    const data = await resp.json();
    if (!resp.ok) { showError(data.error || ("HTTP " + resp.status)); return; }
    renderResult(data);
  } catch (e) {
    showError("Network error: " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Run optimization";
  }
}

function renderResult(data) {
  $("empty").classList.add("hidden");
  $("result").classList.remove("hidden");

  $("tokens-before").textContent = data.baseline_tokens != null ? data.baseline_tokens : data.tokens_before;
  $("tokens-after").textContent  = data.method_tokens   != null ? data.method_tokens   : data.tokens_after;

  const s = data.token_savings_pct;
  const savingsEl = $("savings");
  savingsEl.textContent = savingsLabel(s);
  savingsEl.classList.toggle("negative", s < 0);

  $("method-used").textContent = data.method_requested === "auto"
    ? `${data.method_used} (auto)` : data.method_used;
  $("status").textContent  = data.status;
  $("elapsed").textContent = data.elapsed_s + "s";

  const reasonEl = $("route-reason");
  if (data.method_requested === "auto" && data.route_reason) {
    reasonEl.textContent = `Smart router → ${data.method_used}: ${data.route_reason}`;
    reasonEl.classList.remove("hidden");
  } else {
    reasonEl.classList.add("hidden");
  }

  $("decoded").textContent = fmtJSON(data.decoded_output);
  $("toon").textContent    = data.toon_output || "—";
  $("key-map").textContent = fmtJSON(data.key_map);
  $("raw").textContent     = data.raw_output || "—";
}

$("run-btn").addEventListener("click", runOptimization);
$("prompt").addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); runOptimization(); }
});


/* ══════════════════════════════════════════════════════════════════════════
   STATS PAGE
══════════════════════════════════════════════════════════════════════════ */

const METHOD_COLORS = {
  baseline:           "#999999",
  postprocess:        "#4c9f70",
  prompt_engineering: "#2e7d32",
  combined:           "#1b5e20",
};

async function loadStats() {
  try {
    const resp = await fetch("/api/stats");
    if (!resp.ok) { showStatsEmpty(); return; }
    const data = await resp.json();
    renderStats(data);
  } catch (_) { showStatsEmpty(); }
}

function showStatsEmpty() {
  $("stats-empty").style.display = "block";
  $("stats-content").style.display = "none";
}

function renderStats(d) {
  $("stats-empty").style.display = "none";
  $("stats-content").style.display = "block";

  // summary cards
  const best = d.by_method.reduce((a, b) => b.mean_savings > a.mean_savings ? b : a, d.by_method[0]);
  $("stats-summary").innerHTML = `
    <div class="stat-card">
      <div class="stat-card-label">Rows tested</div>
      <div class="stat-card-value">${d.total_rows}</div>
      <div class="stat-card-sub">${d.total_results} total results</div>
    </div>
    <div class="stat-card">
      <div class="stat-card-label">Methods</div>
      <div class="stat-card-value">${d.methods.length}</div>
      <div class="stat-card-sub">${d.methods.join(", ").replace(/_/g, " ")}</div>
    </div>
    <div class="stat-card">
      <div class="stat-card-label">Best savings</div>
      <div class="stat-card-value">${savingsLabel(best.mean_savings)}</div>
      <div class="stat-card-sub">${best.method.replace(/_/g, " ")}</div>
    </div>
    <div class="stat-card">
      <div class="stat-card-label">Best G-Eval</div>
      <div class="stat-card-value">${d.by_method.reduce((a, b) => b.mean_score > a.mean_score ? b : a, d.by_method[0]).mean_score.toFixed(2)}</div>
      <div class="stat-card-sub">out of 5</div>
    </div>
  `;

  // method table
  $("stats-method-table").innerHTML = buildTable(
    ["Method", "Mean savings %", "Mean G-Eval", "Rows"],
    d.by_method.map(r => [r.method, fmtNum(r.mean_savings) + "%", fmtNum(r.mean_score), r.rows])
  );

  // bar charts
  const maxSavings = Math.max(...d.by_method.map(r => Math.abs(r.mean_savings)), 1);
  $("stats-savings-chart").innerHTML = d.by_method.map(r => barRow(
    r.method, r.mean_savings, maxSavings,
    savingsLabel(r.mean_savings),
    METHOD_COLORS[r.method] || "#4c9f70"
  )).join("");

  const maxScore = 5;
  $("stats-quality-chart").innerHTML = d.by_method.map(r => barRow(
    r.method, r.mean_score, maxScore,
    r.mean_score.toFixed(2) + " / 5",
    METHOD_COLORS[r.method] || "#4c9f70"
  )).join("");

  // pivot tables
  $("stats-pivot-savings").innerHTML = buildPivotTable(d.pivot_savings, d.methods, "%");
  $("stats-pivot-quality").innerHTML = buildPivotTable(d.pivot_quality, d.methods, "");

  // quality/failure
  $("stats-qf").innerHTML = buildTable(
    ["Method", "Quality warnings", "Parse failed", "API failed", "Schema valid"],
    d.quality_failures.map(r => [r.method, r.quality_warnings, r.parse_failed, r.api_failed, r.schema_valid])
  );
}

function barRow(label, value, max, display, color) {
  const pct = Math.abs(value) / max * 100;
  const neg = value < 0;
  return `
    <div class="bar-row">
      <div class="bar-label">${label.replace(/_/g, " ")}</div>
      <div class="bar-track">
        ${neg
          ? `<div class="bar-fill bar-neg"><span class="bar-value" style="color:var(--red)">${display}</span></div>`
          : `<div class="bar-fill" style="width:${pct}%;background:${color}"><span class="bar-value">${display}</span></div>`
        }
      </div>
    </div>`;
}

function buildTable(headers, rows) {
  const ths = headers.map(h => `<th>${h}</th>`).join("");
  const trs = rows.map(r =>
    `<tr>${r.map((c, i) => `<td class="${i > 0 ? "num" : ""}">${c}</td>`).join("")}</tr>`
  ).join("");
  return `<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
}

function buildPivotTable(rows, methods, suffix) {
  if (!rows || !rows.length) return "<p>No data.</p>";
  const ths = ["Use case", ...methods.map(m => m.replace(/_/g, " "))].map(h => `<th>${h}</th>`).join("");
  const trs = rows.map(r => {
    const cells = [r.use_case, ...methods.map(m => {
      const v = r[m];
      return v == null ? "—" : fmtNum(v) + suffix;
    })].map((c, i) => `<td class="${i > 0 ? "num" : ""}">${c}</td>`).join("");
    return `<tr>${cells}</tr>`;
  }).join("");
  return `<table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>`;
}

function fmtNum(n) {
  if (n == null) return "—";
  return typeof n === "number" ? n.toFixed(Math.abs(n) < 10 ? 2 : 1) : n;
}

$("refresh-stats").addEventListener("click", loadStats);


/* ══════════════════════════════════════════════════════════════════════════
   REPORT PAGE
══════════════════════════════════════════════════════════════════════════ */

let _datasetRows = [];

async function loadDataset() {
  const container = $("dataset-list");
  if (_datasetRows.length) return;  // already loaded
  container.innerHTML = '<div class="empty">Loading dataset…</div>';
  try {
    const data = await (await fetch("/api/dataset")).json();
    _datasetRows = data;
    renderDataset(data);
    updateSelectedCount();
  } catch (_) {
    container.innerHTML = '<div class="empty">Failed to load dataset.</div>';
  }
}

function renderDataset(rows) {
  const container = $("dataset-list");
  container.innerHTML = "";
  const groups = {};
  rows.forEach(r => { (groups[r.use_case] = groups[r.use_case] || []).push(r); });

  Object.entries(groups).forEach(([uc, ucRows]) => {
    const group = document.createElement("div");
    group.className = "use-case-group";
    group.innerHTML = `
      <div class="uc-header">
        <span class="uc-name">${uc.replace(/_/g, " ")}</span>
        <span class="uc-count">${ucRows.length} rows</span>
        <button class="uc-toggle btn-sm" data-uc="${uc}" data-action="select">Select all</button>
      </div>
    `;
    ucRows.forEach(r => {
      const row = document.createElement("label");
      row.className = "dataset-row";
      row.innerHTML = `
        <input type="checkbox" class="row-check" value="${r.id}" checked />
        <span class="row-id">${r.id}</span>
        <span class="row-size">${r.size}</span>
        <span class="row-preview" title="${r.prompt_preview}">${r.prompt_preview}</span>
      `;
      row.querySelector(".row-check").addEventListener("change", updateSelectedCount);
      group.appendChild(row);
    });
    container.appendChild(group);
  });

  // group toggles
  document.querySelectorAll(".uc-toggle").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const uc = btn.dataset.uc;
      const checks = document.querySelectorAll(`.use-case-group .row-check[value^="${uc.split("_")[0]}"]`);
      // use the group's own rows
      const groupEl = btn.closest(".use-case-group");
      const groupChecks = groupEl.querySelectorAll(".row-check");
      const allChecked = [...groupChecks].every(c => c.checked);
      groupChecks.forEach(c => { c.checked = !allChecked; });
      btn.textContent = allChecked ? "Select all" : "Deselect all";
      updateSelectedCount();
    });
  });
}

function updateSelectedCount() {
  const checked = document.querySelectorAll(".row-check:checked").length;
  $("selected-count").textContent = `${checked} row${checked !== 1 ? "s" : ""} selected`;
  $("run-report-btn").disabled = checked === 0;
}

$("select-all").addEventListener("click", () => {
  document.querySelectorAll(".row-check").forEach(c => { c.checked = true; });
  document.querySelectorAll(".uc-toggle").forEach(b => { b.textContent = "Deselect all"; });
  updateSelectedCount();
});

$("deselect-all").addEventListener("click", () => {
  document.querySelectorAll(".row-check").forEach(c => { c.checked = false; });
  document.querySelectorAll(".uc-toggle").forEach(b => { b.textContent = "Select all"; });
  updateSelectedCount();
});

$("run-report-btn").addEventListener("click", async () => {
  const selected = [...document.querySelectorAll(".row-check:checked")].map(c => c.value);
  if (!selected.length) return;

  const btn = $("run-report-btn");
  btn.disabled = true;
  btn.textContent = "Running…";
  $("download-link").classList.add("hidden");
  $("report-error").classList.add("hidden");

  // show progress panel
  const progress = $("report-progress");
  const progressLog = $("report-packet-log");
  progressLog.innerHTML = "";
  progress.classList.remove("hidden");
  $("progress-label").textContent = `Running ${selected.length} row${selected.length !== 1 ? "s" : ""} × 4 methods…`;

  // subscribe to packet events during run
  _reportPacketTarget = progressLog;

  try {
    const resp = await fetch("/api/run-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ row_ids: selected }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      $("report-error").textContent = data.error || "Run failed.";
      $("report-error").classList.remove("hidden");
    } else {
      $("progress-label").textContent = `Done — ${data.results} results. PDF ready.`;
      $("download-link").classList.remove("hidden");
      progress.querySelector(".spinner").style.display = "none";
      // refresh stats if on that tab
      if (_activeTab === "stats") loadStats();
    }
  } catch (e) {
    $("report-error").textContent = "Network error: " + e.message;
    $("report-error").classList.remove("hidden");
  } finally {
    _reportPacketTarget = null;
    btn.disabled = false;
    btn.textContent = "Run & generate PDF";
    updateSelectedCount();
  }
});


/* ══════════════════════════════════════════════════════════════════════════
   INIT
══════════════════════════════════════════════════════════════════════════ */
document.addEventListener("DOMContentLoaded", () => {
  startSSE();
  loadExamples();
});
