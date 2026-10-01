/* Grid Simulator web GUI – vanilla JS single page app. */
"use strict";

const state = { grids: [], current: null, info: null, lastGraph: null };
const $ = (sel) => document.querySelector(sel);

// ---------------------------------------------------------------- helpers
function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function fmt(v, d = 3) {
  if (v === null || v === undefined || v === "") return "–";
  if (typeof v === "number") return Number.isInteger(v) && d === 0 ? String(v) : v.toFixed(d);
  if (typeof v === "boolean") return v ? "yes" : "no";
  return esc(v);
}
function setStatus(msg, kind = "") {
  const el = $("#status");
  el.textContent = msg;
  el.className = "status " + kind;
}
async function api(path, body) {
  const opts = body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  };
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({ success: false, error: `HTTP ${res.status}` }));
  if (!res.ok || data.success === false) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}
async function busy(button, label, fn) {
  const buttons = document.querySelectorAll("button");
  buttons.forEach((b) => (b.disabled = true));
  setStatus(label, "busy");
  const t0 = performance.now();
  try {
    await fn();
    setStatus(`${label.replace(/…$/, "")} done (${((performance.now() - t0) / 1000).toFixed(1)} s)`);
  } catch (e) {
    setStatus(`Error: ${e.message}`, "error");
  } finally {
    buttons.forEach((b) => (b.disabled = false));
  }
}
function gridRef() {
  const [source, id] = $("#grid-select").value.split(":");
  return { source, id };
}

/**
 * Render a sortable table.
 * columns: [{key, label, digits, text, render}]
 * rowClass: optional fn(row) -> css class
 */
function renderTable(container, columns, rows, rowClass) {
  const el = typeof container === "string" ? $(container) : container;
  if (!rows || !rows.length) { el.innerHTML = "<p class='hint'>No data.</p>"; return; }
  let sortKey = null, asc = true;
  const draw = () => {
    let data = rows.slice();
    if (sortKey) {
      data.sort((a, b) => {
        const x = a[sortKey], y = b[sortKey];
        if (x === y) return 0;
        if (x === null || x === undefined) return 1;
        if (y === null || y === undefined) return -1;
        return (x > y ? 1 : -1) * (asc ? 1 : -1);
      });
    }
    const head = columns.map((c) =>
      `<th class="${c.text ? "text" : ""}" data-key="${c.key}">${esc(c.label)}${sortKey === c.key ? (asc ? " ▲" : " ▼") : ""}</th>`).join("");
    const body = data.map((r) => {
      const cls = rowClass ? rowClass(r) : "";
      const tds = columns.map((c) => {
        const v = c.render ? c.render(r) : fmt(r[c.key], c.digits ?? 3);
        return `<td class="${c.text ? "text" : ""}">${v}</td>`;
      }).join("");
      return `<tr class="${cls}">${tds}</tr>`;
    }).join("");
    el.innerHTML = `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
    el.querySelectorAll("th").forEach((th) => th.addEventListener("click", () => {
      const k = th.dataset.key;
      asc = sortKey === k ? !asc : true;
      sortKey = k;
      draw();
    }));
  };
  draw();
}
function kpis(container, items) {
  $(container).innerHTML = items.map(([label, value, cls]) =>
    `<div class="kpi ${cls || ""}"><div class="label">${esc(label)}</div><div class="value">${value}</div></div>`).join("");
}

// ---------------------------------------------------------------- network graph (SVG)
function drawGraph(graph, caption) {
  state.lastGraph = graph;
  $("#graph-caption").textContent = caption || "";
  const el = $("#graph");
  const W = el.clientWidth || 900, H = el.clientHeight || 560, pad = 40;
  const xs = graph.nodes.map((n) => n.x), ys = graph.nodes.map((n) => n.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const sx = (x) => pad + ((x - minX) / ((maxX - minX) || 1)) * (W - 2 * pad);
  const sy = (y) => pad + ((y - minY) / ((maxY - minY) || 1)) * (H - 2 * pad);
  const pos = {};
  graph.nodes.forEach((n) => (pos[n.id] = [sx(n.x), sy(n.y)]));
  const many = graph.nodes.length > 20;

  const edges = graph.edges.map((e) => {
    const [x1, y1] = pos[e.from], [x2, y2] = pos[e.to];
    const over = e.loading_percent != null && e.loading_percent > 85;
    const color = over ? "#d9534f" : e.type === "transformer" ? "#8e44ad" : "#7b8a99";
    const width = e.loading_percent != null ? 1.5 + Math.min(e.loading_percent, 150) / 30 : 2;
    const dash = e.type === "transformer" ? "6 4" : "";
    const title = `${e.type} ${e.element_id}: ${e.from} → ${e.to}` +
      (e.p_mw != null ? `\nP = ${e.p_mw} MW` : "") +
      (e.loading_percent != null ? `\nLoading = ${e.loading_percent} %` : "");
    return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="${width}" stroke-dasharray="${dash}"><title>${esc(title)}</title></line>`;
  }).join("");

  const nodes = graph.nodes.map((n) => {
    const [x, y] = pos[n.id];
    let fill = "#8a99a8";
    if (n.vm_pu != null) fill = n.vm_pu < 0.95 || n.vm_pu > 1.05 ? "#d9534f" : "#2e9d5b";
    const r = many ? 7 : 10;
    const gen = n.has_gen ? `<rect x="${x - r - 3}" y="${y - r - 3}" width="${2 * r + 6}" height="${2 * r + 6}" fill="none" stroke="#1f3b57" stroke-width="2"/>` : "";
    const label = `${n.id}` + (n.vm_pu != null && !many ? ` (${n.vm_pu.toFixed(3)})` : "");
    const title = `${n.name} (bus ${n.id})` + (n.vm_pu != null ? `\nV = ${n.vm_pu} p.u.` : "") +
      (n.has_gen ? "\ngenerator / ext. grid" : "") + (n.has_load ? "\nload" : "");
    return `<g>${gen}<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" stroke="#fff" stroke-width="1.5"><title>${esc(title)}</title></circle>` +
      `<text x="${x + r + 4}" y="${y - r + 2}">${esc(label)}</text></g>`;
  }).join("");
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">${edges}${nodes}</svg>`;
}

// ---------------------------------------------------------------- grid loading
async function loadGrids() {
  const data = await api("/api/grids");
  state.grids = data.grids;
  const sel = $("#grid-select");
  const groups = { example: "Built-in examples", db: "Saved in database (grid.db)" };
  sel.innerHTML = Object.entries(groups).map(([src, label]) => {
    const opts = data.grids.filter((g) => g.source === src)
      .map((g) => `<option value="${src}:${esc(g.id)}" title="${esc(g.description)}">${esc(g.name)}</option>`).join("");
    return opts ? `<optgroup label="${esc(label)}">${opts}</optgroup>` : "";
  }).join("");
  const def = data.grids.find((g) => g.source === "example" && g.id === "ieee39");
  if (def) sel.value = "example:ieee39";
}

function fillSelect(id, items, labelFn) {
  $(id).innerHTML = items.map((i) => `<option value="${esc(i.id)}">${esc(labelFn(i))}</option>`).join("");
}
function selected(id) {
  return Array.from($(id).selectedOptions).map((o) => o.value);
}

async function loadGrid() {
  const info = await api("/api/grid", gridRef());
  state.info = info;
  const s = info.stats;
  $("#grid-stats").innerHTML = `<h3>${esc(info.name)}</h3><table class="stats">` +
    [["Buses", s.bus], ["Lines", s.line], ["Transformers", s.trafo], ["Generators", s.gen],
     ["Static generators", s.sgen], ["Loads", s.load], ["External grids", s.ext_grid]]
      .map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("") + "</table>";
  drawGraph(info.graph, "(topology – run a load flow to colour by voltage)");
  const el = info.elements;
  fillSelect("#lf-out-line", el.lines, (l) => `${l.id}: ${l.name} (${l.from_bus}–${l.to_bus})`);
  fillSelect("#lf-out-trafo", el.trafos, (t) => `${t.id}: ${t.name} (${t.hv_bus}–${t.lv_bus})`);
  fillSelect("#lf-out-gen", el.gens, (g) => `${g.id}: ${g.name} (bus ${g.bus})`);
  fillSelect("#se-outage-buses", el.buses, (b) => `${b.id}: ${b.name}`);
  ["#lf-summary", "#ca-summary", "#se-summary"].forEach((s) => ($(s).innerHTML = ""));
  ["#lf-buses", "#lf-lines", "#lf-trafos", "#lf-gens", "#ca-results", "#ca-violations", "#se-table", "#se-meas"]
    .forEach((s) => ($(s).innerHTML = ""));
  $("#se-outage").textContent = "";
}

// ---------------------------------------------------------------- load flow
async function runLoadFlow() {
  const outages = { line: selected("#lf-out-line"), trafo: selected("#lf-out-trafo"), gen: selected("#lf-out-gen") };
  const r = await api("/api/loadflow", { ...gridRef(), outages });
  const s = r.summary;
  kpis("#lf-summary", [
    ["Converged", s.converged ? "yes" : "no", s.converged ? "good" : "bad"],
    ["Min V (p.u.)", fmt(s.min_vm_pu, 4)],
    ["Max V (p.u.)", fmt(s.max_vm_pu, 4)],
    ["Max loading (%)", fmt(s.max_loading_percent, 1), s.max_loading_percent > 85 ? "bad" : ""],
    ["Generation (MW)", fmt(s.total_generation_mw, 1)],
    ["Load (MW)", fmt(s.total_load_mw, 1)],
    ["Losses (MW)", fmt(s.losses_mw, 2)],
    ["Voltage violations", s.voltage_violations, s.voltage_violations ? "bad" : "good"],
    ["Overloads (>85 %)", s.overloads, s.overloads ? "bad" : "good"],
    ["Outaged elements", r.outages.length ? esc(r.outages.join(", ")) : "none"],
  ]);
  renderTable("#lf-buses", [
    { key: "id", label: "Bus", digits: 0 }, { key: "name", label: "Name", text: true },
    { key: "vn_kv", label: "Vn (kV)", digits: 1 }, { key: "vm_pu", label: "V (p.u.)", digits: 4 },
    { key: "va_degree", label: "Angle (°)", digits: 2 }, { key: "p_mw", label: "P (MW)", digits: 2 },
    { key: "q_mvar", label: "Q (Mvar)", digits: 2 },
  ], r.buses, (b) => (b.violation ? "warn" : ""));
  const branchCls = (x) => (!x.in_service ? "oos" : x.overloaded ? "warn" : "");
  renderTable("#lf-lines", [
    { key: "id", label: "Line", digits: 0 }, { key: "name", label: "Name", text: true },
    { key: "from_bus", label: "From", digits: 0 }, { key: "to_bus", label: "To", digits: 0 },
    { key: "p_from_mw", label: "P from (MW)", digits: 2 }, { key: "q_from_mvar", label: "Q from (Mvar)", digits: 2 },
    { key: "p_to_mw", label: "P to (MW)", digits: 2 }, { key: "q_to_mvar", label: "Q to (Mvar)", digits: 2 },
    { key: "pl_mw", label: "Losses (MW)", digits: 3 }, { key: "i_ka", label: "I (kA)", digits: 3 },
    { key: "loading_percent", label: "Loading (%)", digits: 1 },
  ], r.lines, branchCls);
  renderTable("#lf-trafos", [
    { key: "id", label: "Trafo", digits: 0 }, { key: "name", label: "Name", text: true },
    { key: "from_bus", label: "HV bus", digits: 0 }, { key: "to_bus", label: "LV bus", digits: 0 },
    { key: "p_hv_mw", label: "P HV (MW)", digits: 2 }, { key: "q_hv_mvar", label: "Q HV (Mvar)", digits: 2 },
    { key: "p_lv_mw", label: "P LV (MW)", digits: 2 }, { key: "q_lv_mvar", label: "Q LV (Mvar)", digits: 2 },
    { key: "loading_percent", label: "Loading (%)", digits: 1 },
  ], r.trafos, branchCls);
  renderTable("#lf-gens", [
    { key: "id", label: "Gen", text: true }, { key: "name", label: "Name", text: true },
    { key: "bus", label: "Bus", digits: 0 }, { key: "p_mw", label: "P (MW)", digits: 2 },
    { key: "q_mvar", label: "Q (Mvar)", digits: 2 }, { key: "vm_pu", label: "V set (p.u.)", digits: 4 },
    { key: "slack", label: "Slack", text: true },
  ], r.gens);
  drawGraph(r.graph, `(load flow results${r.outages.length ? ", outages: " + r.outages.join(", ") : ""})`);
}

// ---------------------------------------------------------------- contingency
let lastContingency = null;
async function runContingency() {
  lastContingency = await api("/api/contingency", gridRef());
  showContingency();
}
function showContingency() {
  const r = lastContingency;
  if (!r) return;
  const s = r.summary;
  kpis("#ca-summary", [
    ["Security status", esc(s.security_status), s.security_status === "Secure" ? "good" : "bad"],
    ["Contingencies", s.total_contingencies],
    ["Converged", `${s.converged_cases} (${esc(s.convergence_rate)})`],
    ["Critical", s.critical_contingencies, s.critical_contingencies ? "bad" : ""],
    ["High", s.high_severity, s.high_severity ? "bad" : ""],
    ["Medium", s.medium_severity], ["Low", s.low_severity],
  ]);
  let rows = r.results;
  if ($("#ca-only-critical").checked) rows = rows.filter((x) => ["High", "Critical"].includes(x.severity));
  const sevRank = { Critical: 0, High: 1, Medium: 2, Low: 3 };
  rows = rows.map((x) => ({ ...x, sev_rank: sevRank[x.severity] ?? 9 }));
  renderTable("#ca-results", [
    { key: "contingency_type", label: "Type", text: true }, { key: "element_name", label: "Element", text: true },
    { key: "converged", label: "Converged", text: true },
    { key: "min_voltage_pu", label: "Min V (p.u.)", digits: 4 }, { key: "max_voltage_pu", label: "Max V (p.u.)", digits: 4 },
    { key: "max_line_loading", label: "Max line (%)", digits: 1 }, { key: "max_trafo_loading", label: "Max trafo (%)", digits: 1 },
    { key: "voltage_violations", label: "V viol.", digits: 0 }, { key: "overload_violations", label: "Overloads", digits: 0 },
    { key: "sev_rank", label: "Severity", text: true, render: (x) => esc(x.severity) + (x.error ? ` – ${esc(x.error)}` : "") },
  ], rows, (x) => `sev-${x.severity}`);
  renderTable("#ca-violations", [
    { key: "contingency_type", label: "Contingency", text: true }, { key: "contingency_element", label: "Outaged element", text: true },
    { key: "violation_type", label: "Violation", text: true }, { key: "element_type", label: "Element type", text: true },
    { key: "element_name", label: "Element", text: true }, { key: "violation_value", label: "Value", text: true },
    { key: "limit_value", label: "Limit", text: true }, { key: "severity", label: "Severity", text: true },
  ], r.violations, (x) => `sev-${x.severity}`);
}

// ---------------------------------------------------------------- state estimation
function seParams() {
  return {
    ...gridRef(),
    mode: $("#se-mode").value,
    voltage_noise_percent: parseFloat($("#se-vnoise").value),
    power_noise_percent: parseFloat($("#se-pnoise").value),
    max_iterations: parseInt($("#se-iter").value, 10),
  };
}
async function runSE() {
  const r = await api("/api/state-estimation", seParams());
  const errs = (r.true_voltage_magnitudes || []).map((t, i) =>
    Math.abs((r.voltage_magnitudes[i] - t) / t) * 100);
  kpis("#se-summary", [
    ["Converged", r.converged ? "yes" : "no", r.converged ? "good" : "bad"],
    ["Iterations", r.iterations],
    ["Measurements", r.measurements_count],
    ["Objective J(x)", fmt(r.objective_function, 4)],
    ["Max |V error| (%)", errs.length ? fmt(Math.max(...errs), 3) : "–"],
    ["Mean |V error| (%)", errs.length ? fmt(errs.reduce((a, b) => a + b, 0) / errs.length, 3) : "–"],
  ]);
  const rows = (r.bus_ids || []).map((id, i) => ({
    id, name: r.bus_names[i],
    true_vm: r.true_voltage_magnitudes ? r.true_voltage_magnitudes[i] : null,
    est_vm: r.voltage_magnitudes[i],
    err: errs.length ? ((r.voltage_magnitudes[i] - r.true_voltage_magnitudes[i]) / r.true_voltage_magnitudes[i]) * 100 : null,
    true_va: r.true_voltage_angles_deg[i], est_va: r.voltage_angles_deg[i],
  }));
  renderTable("#se-table", [
    { key: "id", label: "Bus", digits: 0 }, { key: "name", label: "Name", text: true },
    { key: "true_vm", label: "True V (p.u.)", digits: 4 }, { key: "est_vm", label: "Est. V (p.u.)", digits: 4 },
    { key: "err", label: "V error (%)", digits: 3 },
    { key: "true_va", label: "True angle (°)", digits: 2 }, { key: "est_va", label: "Est. angle (°)", digits: 2 },
  ], rows, (x) => (x.err != null && Math.abs(x.err) > 2 ? "warn" : ""));
  renderTable("#se-meas", [
    { key: "Index", label: "#", digits: 0 }, { key: "Type", label: "Type", text: true },
    { key: "Element", label: "Element", digits: 0 },
    { key: "Bus From", label: "Bus from", digits: 0 }, { key: "Bus To", label: "Bus to", digits: 0 },
    { key: "Value", label: "Measured value", text: true }, { key: "Std Dev", label: "Std. dev.", text: true },
  ], r.measurement_summary || []);
  if (!r.converged) setStatus("State estimation did not converge – try voltage-only mode or more iterations", "error");
}
async function runOutage() {
  const buses = selected("#se-outage-buses");
  if (!buses.length) throw new Error("Select at least one bus for the measurement outage");
  const r = await api("/api/measurement-outage", { ...seParams(), outage_buses: buses });
  $("#se-outage").textContent = r.scenario_summary || JSON.stringify(r.comparison_analysis, null, 2);
}

// ---------------------------------------------------------------- wiring
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === t));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === "tab-" + t.dataset.tab));
  if (t.dataset.tab === "network" && state.lastGraph) drawGraph(state.lastGraph, $("#graph-caption").textContent);
}));
$("#btn-load-grid").addEventListener("click", (e) => busy(e.target, "Loading grid…", loadGrid));
$("#grid-select").addEventListener("change", (e) => busy(e.target, "Loading grid…", loadGrid));
$("#btn-loadflow").addEventListener("click", (e) => busy(e.target, "Running load flow…", runLoadFlow));
$("#btn-lf-clear").addEventListener("click", () =>
  ["#lf-out-line", "#lf-out-trafo", "#lf-out-gen"].forEach((s) => Array.from($(s).options).forEach((o) => (o.selected = false))));
$("#btn-contingency").addEventListener("click", (e) => busy(e.target, "Running N-1 contingency analysis…", runContingency));
$("#ca-only-critical").addEventListener("change", showContingency);
$("#btn-se").addEventListener("click", (e) => busy(e.target, "Running state estimation…", runSE));
$("#btn-outage").addEventListener("click", (e) => busy(e.target, "Simulating measurement outage…", runOutage));
window.addEventListener("resize", () => state.lastGraph && $("#tab-network").classList.contains("active") &&
  drawGraph(state.lastGraph, $("#graph-caption").textContent));

(async () => {
  try {
    await loadGrids();
    await busy(null, "Loading grid…", loadGrid);
  } catch (e) {
    setStatus(`Error: ${e.message}`, "error");
  }
})();
