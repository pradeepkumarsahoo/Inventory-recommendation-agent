"""Generate the standalone daily-store-decision HTML report.

Produces /reports/daily-store-decision-report.html using the live agent
output for a selected store. Run:

    python reports/generate_report.py S101
"""
from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai-agents"))

from retail_agents import run_supervisor  # noqa: E402


REPORT_PATH = ROOT / "reports" / "daily-store-decision-report.html"


def _h(s): return html.escape(str(s))


def _format_currency(v):
    return f"${float(v):,.0f}"


def _row(label, value):
    return f"<div class='kv'><div class='k'>{_h(label)}</div><div class='v'>{_h(value)}</div></div>"


def _priority_badge(p):
    cls = {"HIGH": "p-high", "MEDIUM": "p-med", "LOW": "p-low"}.get(p, "p-med")
    return f"<span class='badge {cls}'>{_h(p)}</span>"


def _render_action_card(idx, action, rec):
    metrics = rec.get("supporting_metrics", {})
    metrics_html = "".join(
        f"<li><strong>{_h(k.replace('_', ' '))}</strong>: {_h(v)}</li>"
        for k, v in metrics.items() if not isinstance(v, (list, dict))
    )
    risks_html = "".join(f"<li>{_h(r)}</li>" for r in rec.get("risks", []))
    return f"""
    <article class='action-card'>
      <header>
        <span class='rank'>#{idx}</span>
        {_priority_badge(action['priority'])}
        <h3>{_h(action['title'])}</h3>
      </header>
      <section class='why'>
        <div class='block'>
          <div class='block-h'>Why it matters</div>
          <p>{_h(action['why'])}</p>
        </div>
        <div class='block'>
          <div class='block-h'>Who &amp; when</div>
          <p>Owner: <strong>{_h(action['owner'])}</strong><br/>
             Deadline: <strong>{_h(action['deadline_hours'])}h</strong><br/>
             Approval: <strong>{_h(action['requires_approval'])}</strong></p>
        </div>
        <div class='block'>
          <div class='block-h'>Expected impact</div>
          <p>Revenue: <strong>{_format_currency(action['expected_sales_impact'])}</strong><br/>
             Margin: <strong>{_format_currency(action['expected_margin_impact'])}</strong><br/>
             KPI: {_h(action['success_kpi'])}</p>
        </div>
      </section>
      <details>
        <summary>Supporting evidence</summary>
        <ul class='metrics'>{metrics_html}</ul>
        <div class='block-h'>Risks</div>
        <ul class='risks'>{risks_html}</ul>
      </details>
    </article>
    """


def _render_kpi_tiles(bundle):
    sp = bundle["insights"].get("store_performance", {})
    aging = bundle["insights"].get("aging_value_by_bucket", {})
    aging_total = sum(aging.values())
    recs = bundle["recommendations"]
    expected_rev = sum(r.get("expected_sales_impact", 0) for r in recs)
    expected_margin = sum(r.get("expected_margin_impact", 0) for r in recs)
    high_cnt = sum(1 for r in recs if r.get("priority") == "HIGH")
    tiles = [
        ("Current 90-day revenue", _format_currency(sp.get("total_revenue", 0))),
        ("Gross margin", f"{sp.get('gross_margin_percent', 0)}%"),
        ("Inventory value", _format_currency(bundle["insights"].get("inventory_value_total", 0))),
        ("Aging inventory (91d+)", _format_currency(aging.get("91-180", 0) + aging.get("180+", 0))),
        ("Expected revenue uplift", _format_currency(expected_rev)),
        ("Expected gross profit", _format_currency(expected_margin)),
        ("High-priority actions", str(high_cnt)),
        ("Total actions", str(len(recs))),
    ]
    cells = "".join(
        f"<div class='tile'><div class='t-label'>{_h(l)}</div><div class='t-value'>{_h(v)}</div></div>"
        for l, v in tiles
    )
    return f"<section class='tiles'>{cells}</section>"


def _render_targets(bundle):
    target = next((r for r in bundle["recommendations"] if r.get("action_type") == "TARGET"), None)
    if not target:
        return ""
    daily = target["supporting_metrics"].get("daily_breakdown", [])
    rows = "".join(
        f"<tr><td>{_h(d['date'])}</td><td>{_format_currency(d['baseline_forecast_revenue'])}</td>"
        f"<td>{_format_currency(d['recommended_target_revenue'])}</td></tr>"
        for d in daily
    )
    return f"""
    <section class='targets'>
      <h2>Sales Targets</h2>
      <p>{_h(target['justification'])}</p>
      <table class='pretty'>
        <thead><tr><th>Date</th><th>Baseline forecast</th><th>Recommended target</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """


def _css():
    return """
    :root {
      --bg: #0b1020;
      --surface: #11162b;
      --surface-2: #19203a;
      --accent: #4f8cff;
      --accent-2: #7bffb2;
      --warn: #ffb13d;
      --danger: #ff6b7a;
      --text: #e6ecff;
      --muted: #9aa3c7;
      --border: rgba(255,255,255,0.08);
    }
    :root:not([data-theme="dark"]) {
      --bg: #f6f8ff;
      --surface: #ffffff;
      --surface-2: #f0f3fb;
      --accent: #2f58cd;
      --accent-2: #0d9b65;
      --warn: #b47400;
      --danger: #c62537;
      --text: #0e1430;
      --muted: #5a6487;
      --border: rgba(14,20,48,0.08);
    }
    @media (prefers-color-scheme: dark) {
      :root:not([data-theme="light"]) {
        --bg: #0b1020; --surface:#11162b; --surface-2:#19203a; --accent:#4f8cff;
        --accent-2:#7bffb2; --warn:#ffb13d; --danger:#ff6b7a; --text:#e6ecff;
        --muted:#9aa3c7; --border:rgba(255,255,255,0.08);
      }
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; background: var(--bg); color: var(--text);
      font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      padding: 24px 16px; min-height: 100vh;
    }
    .wrap { max-width: 1180px; margin: 0 auto; }
    header.top {
      display: flex; flex-wrap: wrap; align-items: baseline;
      justify-content: space-between; gap: 12px; margin-bottom: 20px;
    }
    header.top h1 { font-size: 26px; margin: 0; letter-spacing: -0.01em; }
    .brand-sub { color: var(--muted); font-size: 13px; }
    .meta { color: var(--muted); font-size: 13px; }
    .tiles {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px; margin-bottom: 24px;
    }
    .tile {
      background: var(--surface); border: 1px solid var(--border);
      padding: 14px 16px; border-radius: 10px;
    }
    .t-label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
    .t-value { font-size: 20px; font-weight: 600; margin-top: 4px; }
    h2 { margin: 32px 0 12px; font-size: 20px; letter-spacing: -0.01em; }
    .action-card {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 12px; padding: 16px; margin-bottom: 12px;
    }
    .action-card header {
      display: flex; align-items: center; gap: 10px;
      margin-bottom: 10px; flex-wrap: wrap;
    }
    .action-card header h3 { margin: 0; font-size: 17px; font-weight: 600; }
    .rank {
      display: inline-flex; align-items: center; justify-content: center;
      width: 30px; height: 30px; background: var(--surface-2);
      color: var(--muted); border-radius: 8px; font-weight: 600; font-size: 13px;
    }
    .badge {
      display: inline-block; padding: 3px 10px; border-radius: 999px;
      font-size: 11px; font-weight: 700; letter-spacing: 0.04em;
    }
    .p-high { background: color-mix(in srgb, var(--danger) 22%, transparent); color: var(--danger); }
    .p-med  { background: color-mix(in srgb, var(--warn) 24%, transparent); color: var(--warn); }
    .p-low  { background: color-mix(in srgb, var(--accent) 20%, transparent); color: var(--accent); }
    .why {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(220px,1fr));
      gap: 12px;
    }
    .block {
      background: var(--surface-2); padding: 10px 12px; border-radius: 8px;
    }
    .block-h {
      font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em;
      color: var(--muted); margin-bottom: 4px;
    }
    details { margin-top: 10px; }
    details summary {
      cursor: pointer; color: var(--accent); font-size: 13px; padding: 6px 0;
    }
    ul.metrics, ul.risks { margin: 0; padding-left: 18px; }
    ul.metrics li, ul.risks li { font-size: 13px; margin-bottom: 2px; color: var(--muted); }
    table.pretty {
      width: 100%; border-collapse: collapse; margin-top: 10px;
      background: var(--surface); border-radius: 10px; overflow: hidden;
    }
    table.pretty th, table.pretty td {
      padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border);
      font-size: 14px;
    }
    table.pretty th { background: var(--surface-2); color: var(--muted); font-weight: 600; }
    footer {
      margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--border);
      color: var(--muted); font-size: 12px;
    }
    @media print {
      body { background: white; color: #0b1020; }
      .action-card, .tile, .block, table.pretty { break-inside: avoid; }
      details > summary { display: none; }
      details > * { display: block !important; }
      header.top { page-break-after: avoid; }
    }
    """


def build_html(bundle):
    actions = bundle["insights"]["action_plan"]
    rec_by_id = {r["recommendation_id"]: r for r in bundle["recommendations"]}
    cards_html = "".join(
        _render_action_card(a["sequence"], a, rec_by_id.get(a["recommendation_id"], {}))
        for a in actions[:12]
    )
    store_id = bundle["store_id"]
    generated = bundle["generated_at"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Daily Store Decision Report — {store_id}</title>
<style>{_css()}</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div>
      <h1>Daily Store Decision Report</h1>
      <div class="brand-sub">Retail Intelligence &amp; Autonomous Store Decision Platform · Author: Pradeep Sahoo · Learning Implementation</div>
    </div>
    <div class="meta">
      <div><strong>Store:</strong> {store_id}</div>
      <div><strong>Generated:</strong> {generated}</div>
    </div>
  </header>

  {_render_kpi_tiles(bundle)}

  <h2>What should the store do first?</h2>
  <p class="meta">Top prioritized actions from the agent supervisor, each one grounded in the data it was derived from.</p>
  {cards_html}

  {_render_targets(bundle)}

  <h2>Monitoring &amp; Risks</h2>
  <ul>
    <li>Monitor stockout days against the destination stores for every approved transfer.</li>
    <li>Track realized vs projected gross profit for pricing changes; roll back after 14 days if below projection.</li>
    <li>Investigate any product whose return rate exceeds 20% before promoting further.</li>
    <li>Re-run the agent supervisor daily; recommendations are a 24-hour snapshot.</li>
  </ul>

  <footer>
    <div>“An AI-powered retail decision intelligence learning implementation demonstrating how Databricks, C#, React, Agentic AI, and NVIDIA NeMo Guardrails can work together to transform retail data into measurable store business outcomes.”</div>
    <div style="margin-top:4px;">Author: Pradeep Sahoo · Purpose: Learning Implementation · Not an officially certified production implementation.</div>
  </footer>
</div>
</body>
</html>
"""


def main():
    store_id = sys.argv[1] if len(sys.argv) > 1 else "S101"
    bundle = run_supervisor(store_id)
    REPORT_PATH.write_text(build_html(bundle), encoding="utf-8")
    print(f"[ok] wrote {REPORT_PATH}")
    print(f"      {len(bundle['recommendations'])} recommendations, {len(bundle['insights']['action_plan'])} actions")


if __name__ == "__main__":
    main()
