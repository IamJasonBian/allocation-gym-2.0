"""Render the EPS dataset as a self-contained local HTML grid.

The data is inlined into the page rather than fetched, so the output opens
straight off disk — `file://` blocks the fetch a served page would use, and
needing a web server to look at a grid is a bad trade.

Rendering lives here rather than in the engine: the engine writes the dataset,
this package reads it, and a plot is a read.
"""

from __future__ import annotations

import json

TEMPLATE = """<!DOCTYPE html>
<meta charset="utf-8">
<title>EPS Grid</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {
    --bg:#fff; --panel:#f7f7f8; --line:#e3e3e6;
    --ink:#16171a; --muted:#6b6d76;
    --beat:#16794a; --miss:#b3261e; --pending:#5b5ec7;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg:#131417; --panel:#1b1d21; --line:#2c2f35;
      --ink:#e9e9ec; --muted:#9a9ca5;
      --beat:#4ade80; --miss:#f87171; --pending:#a5b4fc;
    }
  }
  * { box-sizing:border-box; }
  body {
    margin:0; padding:24px; background:var(--bg); color:var(--ink);
    font:14px/1.45 ui-sans-serif, -apple-system, "Segoe UI", system-ui, sans-serif;
  }
  h1 { font-size:19px; margin:0 0 4px; letter-spacing:-0.01em; }
  .sub { color:var(--muted); font-size:13px; }
  .controls { margin:16px 0; display:flex; gap:8px; flex-wrap:wrap; }
  input, select {
    padding:6px 10px; border:1px solid var(--line); border-radius:6px;
    background:var(--panel); color:var(--ink); font:inherit; font-size:13px;
  }
  .grid { display:grid; gap:10px; grid-template-columns:repeat(auto-fill,minmax(230px,1fr)); }
  .card { border:1px solid var(--line); border-radius:8px; background:var(--panel); padding:12px 13px; }
  .tk { display:flex; justify-content:space-between; align-items:baseline; }
  .tk b { font-size:15px; }
  .tk span { color:var(--muted); font-size:11px; }
  table { width:100%; border-collapse:collapse; margin-top:9px; }
  th {
    text-align:right; font-size:10px; font-weight:600; color:var(--muted);
    text-transform:uppercase; letter-spacing:.05em; padding:0 0 3px;
    border-bottom:1px solid var(--line);
  }
  th:first-child { text-align:left; }
  td { padding:3px 0; text-align:right; font-variant-numeric:tabular-nums; font-size:12.5px; }
  td:first-child { text-align:left; color:var(--muted); font-size:11.5px; }
  tr.next td { color:var(--pending); font-weight:600; }
  .beat { color:var(--beat); } .miss { color:var(--miss); }
  .empty { color:var(--muted); padding:32px 0; }
  footer { margin-top:22px; color:var(--muted); font-size:12px; }
  code { background:var(--panel); border:1px solid var(--line); border-radius:4px; padding:1px 5px; font-size:12px; }
</style>

<h1>EPS Grid</h1>
<div class="sub" id="meta"></div>

<div class="controls">
  <input id="q" type="search" placeholder="filter tickers…" autocomplete="off">
  <select id="sort">
    <option value="next">sort: next report</option>
    <option value="ticker">sort: ticker</option>
  </select>
</div>

<div class="grid" id="grid"></div>
<div class="empty" id="empty" hidden>No rows.</div>

<footer>
  Written by <code>allocation-engine-2.0</code>, rendered by <code>allocation-gym-2.0</code>.
  Values are split-adjusted, so older quarters may not match headlines.
</footer>

<script>
const DATA = __EPS_DATA__;

const fmt = v => (v === null || v === undefined) ? "\\u2014" : v.toFixed(2);

function byTicker(rows) {
  const map = new Map();
  for (const r of rows) {
    if (!map.has(r.ticker)) map.set(r.ticker, []);
    map.get(r.ticker).push(r);
  }
  for (const list of map.values()) {
    list.sort((a, b) => a.earnings_date.localeCompare(b.earnings_date));
  }
  return map;
}

function render() {
  const needle = document.getElementById("q").value.trim().toUpperCase();
  const mode = document.getElementById("sort").value;

  const entries = [...byTicker(DATA.eps || []).entries()]
    .filter(([tk]) => !needle || tk.includes(needle));

  entries.sort(([ta, ra], [tb, rb]) => {
    if (mode === "ticker") return ta.localeCompare(tb);
    const na = ra.find(r => r.status === "upcoming");
    const nb = rb.find(r => r.status === "upcoming");
    // Tickers with no scheduled report sort last, then alphabetically.
    if (!na && !nb) return ta.localeCompare(tb);
    if (!na) return 1;
    if (!nb) return -1;
    return na.earnings_date.localeCompare(nb.earnings_date) || ta.localeCompare(tb);
  });

  document.getElementById("grid").innerHTML = entries.map(([tk, rows]) => {
    const next = rows.find(r => r.status === "upcoming");
    const body = rows.map(r => {
      const d = (r.eps_actual !== null && r.eps_estimate !== null)
        ? r.eps_actual - r.eps_estimate : null;
      const cls = d === null ? "" : (d > 0 ? "beat" : d < 0 ? "miss" : "");
      return `<tr class="${r.status === "upcoming" ? "next" : ""}">`
        + `<td>${r.earnings_date}</td><td>${fmt(r.eps_estimate)}</td>`
        + `<td>${fmt(r.eps_actual)}</td>`
        + `<td class="${cls}">${d === null ? "\\u2014" : (d > 0 ? "+" : "") + d.toFixed(2)}</td></tr>`;
    }).join("");

    return `<div class="card">`
      + `<div class="tk"><b>${tk}</b><span>${next ? "next " + next.earnings_date : "no date"}</span></div>`
      + `<table><tr><th>quarter</th><th>est</th><th>actual</th><th>&Delta;</th></tr>${body}</table></div>`;
  }).join("");

  document.getElementById("empty").hidden = entries.length > 0;
}

const upcoming = (DATA.eps || []).filter(r => r.status === "upcoming").length;
document.getElementById("meta").textContent =
  `${(DATA.tickers || []).length} tickers \\u00b7 ${(DATA.eps || []).length} quarters `
  + `\\u00b7 ${upcoming} upcoming \\u00b7 generated ${DATA.generated || "?"}`;

document.getElementById("q").addEventListener("input", render);
document.getElementById("sort").addEventListener("change", render);
render();
</script>
"""


def render(dataset: dict) -> str:
    """Build the self-contained HTML page.

    Args:
        dataset: the loaded dataset (generated / tickers / eps).

    Returns:
        A complete HTML document with the data inlined.
    """
    # `</script>` inside the JSON would close the tag early; escaping the
    # slash keeps it valid JSON and inert to the HTML parser.
    payload = json.dumps(dataset).replace("</", "<\\/")
    return TEMPLATE.replace("__EPS_DATA__", payload)


def write(dataset: dict, path: str = "eps-grid.html") -> str:
    """Render and write the page.

    Args:
        dataset: the loaded dataset.
        path: destination file.

    Returns:
        The path written.
    """
    with open(path, "w") as f:
        f.write(render(dataset))
    return path


__all__ = ["render", "write"]
