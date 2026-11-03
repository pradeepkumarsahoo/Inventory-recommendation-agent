# Retail Intelligence &amp; Autonomous Store Decision Platform

**Author:** Pradeep Sahoo
**Purpose:** Learning Implementation

> An AI-powered retail decision intelligence learning implementation
> demonstrating how Databricks, C#, React, Agentic AI, and NVIDIA NeMo
> Guardrails can work together to transform retail data into measurable
> store business outcomes.

This is a learning implementation, not a certified production system.

---

## The business problem it solves

Every retail store runs on a stream of time-pressured decisions that happen
before the doors open. They are small individually, large in aggregate, and
today they are made from gut and spreadsheets rather than from the data every
POS and WMS already generates.

**The daily questions a store manager faces:**

- What goes on the front display today?
- Which SKUs need to move between stores before they stock out or age out?
- Which prices should slide down this week before margin bleeds further?
- What's a realistic 7-day revenue target to steer the team toward?
- Which aging items need a bundle vs. an outright markdown?

**What goes wrong today:**

- Fast movers understocked while slow movers age in back-rooms.
- Blanket markdowns that erode margin unnecessarily.
- Stale product mix on prime front-office real estate.
- Inconsistent decisions across stores — no shared playbook.
- Pricing and discount actions that are not reliably auditable for compliance.

**Why it isn't a data problem.** POS, inventory, returns, and surveys already
generate the signals. The gap is that nobody has time to synthesize
*five signals × fifty SKUs × five stores* every morning — and when they do,
no one can later prove why a markdown was approved.

**What this platform is.** A decision assistant for that morning window: a
prioritized daily action plan per store, grounded in evidence, bounded by
guardrails, and gated by human approval. Every recommendation carries its
reasoning, expected revenue and margin impact, required-approval flag, and a
success KPI — so the manager acts with confidence and operations can audit
later.

---

## What it does

For every store, the platform generates a prioritized daily action plan:
front-office product placements, inter-store inventory transfers, replenishment,
aging-inventory interventions, pricing optimization, and a 7-day sales target.
Each recommendation carries evidence, risk, expected revenue and margin impact,
required approval, confidence, and a success KPI.

A supervisor agent coordinates six specialists. Every recommendation flows
through a guardrail layer (NVIDIA NeMo Guardrails if installed, or an
equivalent local policy engine). Consequential actions (pricing, transfers,
markdowns, replenishment) always require human approval; approvals and
rejections are audited.

## Repository layout

```
databricks/         sample-data + Delta DDL + Bronze→Silver→Gold notebooks
api/                ASP.NET Core Web API (Clean Architecture, 5 projects)
ai-agents/          Python supervisor + 6 specialists + ToolRegistry
ai-guardrails/      NeMo config + local policy engine + security tests
ui/                 React 18 + TypeScript + Vite dashboard (7 pages)
reports/            Standalone HTML daily decision report
docs/               Architecture, data dictionary, API, agent, security, business rules
```

## Quick start

```bash
# 1. Generate deterministic sample data (50 products × 5 stores × 90 days)
python databricks/generate_sample_data.py

# 2. Produce the standalone HTML decision report
python reports/generate_report.py S101
# → reports/daily-store-decision-report.html

# 3. Run the test suite
python -m pytest
```

Then boot the stack:

```bash
# API
cd api && dotnet run --project Retail.Api --urls http://localhost:5080

# UI
cd ui && npm install && npm run dev
```

Open http://localhost:5173.

## End-to-end agent run (no API, no UI)

```bash
PYTHONPATH=ai-agents python -m retail_agents.supervisor S101
```

Returns a `RecommendationBundle` JSON with the agent trace, action plan, and
every recommendation.

## Business scenarios implemented

| # | Scenario | Agent | Example |
|---|---|---|---|
| 1 | Front-office placement | ProductRecommendation | "Feature North Trail Hiking Boots in the front display — composite score 0.89, 12 units/wk, 48% margin, 0.72 demand signal." |
| 2 | Inter-store transfer | InventoryOptimization | "Transfer 54 units from S102 to S101 — destination 16.9/wk velocity, 13 on hand; source 9.4/wk velocity, 159 on hand (17 wk cover)." |
| 3 | Aging inventory | InventoryOptimization | "Age 180+, margin 46.8% — recommend 15% markdown with regional approval." |
| 4 | Pricing | PricingOptimization | "Decrease price 5% — weeks-of-cover 12, margin 42%; projected margin 37.1% stays above 10% floor." |
| 5 | Daily game plan | StoreExecution | Prioritized list ordered by priority and margin impact. |
| 6 | Sales target | SalesForecasting | "Set 7-day target to $112,340 (+5% stretch) based on day-of-week seasonal forecast." |

## Technology

- **Databricks** — Delta Lake Bronze/Silver/Gold; local CSV adapter for offline runs.
- **C# / .NET 8** — Clean Architecture; FluentValidation; Serilog; Swagger.
- **Python** — supervisor + 6 specialists; backend-grounded tool registry.
- **NVIDIA NeMo Guardrails** — input/output/tool policies with local fallback.
- **React 18 + TypeScript + Vite** — 7-page enterprise dashboard with Recharts.

## Documentation

- `docs/architecture.md` and `docs/architecture-diagram.html`
- `docs/data-dictionary.md`
- `docs/api-specification.md`
- `docs/agent-design.md`
- `docs/security-design.md`
- `docs/business-rules.md`
- `docs/deployment-guide.md`

## Environment constraints during this build

- The Python stack (data, agents, guardrails, report, tests) runs on the build
  host; see verified test output below.
- The C# API and React UI are complete and conventional source trees; building
  and running them requires installing .NET 8 SDK and Node.js 20, which were
  not available on the build host. See `docs/deployment-guide.md`.

## Verified during this build

- `python databricks/generate_sample_data.py` → 17,369 sales / 250 inventory
  snapshots / 1,024 surveys etc.
- `python -m retail_agents.supervisor S101` → 38 recommendations with
  priority, impact, evidence.
- `python reports/generate_report.py S101` → styled HTML report with 38
  action cards.
- `python -m pytest` → 26/26 passing (agents, guardrails, sample data).

Attribution:
"An AI-powered retail decision intelligence learning implementation
demonstrating how Databricks, C#, React, Agentic AI, and NVIDIA NeMo
Guardrails can work together to transform retail data into measurable
store business outcomes."

Author: Pradeep Sahoo · Learning Implementation
