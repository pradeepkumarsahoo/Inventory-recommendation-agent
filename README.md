# Retail Intelligence & Autonomous Store Decision Platform

**Author:** Pradeep Sahoo
**Purpose:** Learning Implementation

> An AI-powered retail decision intelligence learning implementation
> demonstrating how Databricks, C#, React, LangChain-based Agentic AI, and
> NVIDIA NeMo Guardrails can work together to transform retail data into
> measurable store business outcomes — with structured-output agents,
> quantitative inventory optimization, business-impact simulation, an
> accuracy evaluation harness, HITL governance, observability, and CI/CD.

This is a learning implementation, not a certified production system.

---

## What's new in this iteration

| # | Addition | Where |
|---|---|---|
| 1 | **Intelligent agent layer** — structured JSON output (Pydantic), dynamic tool selection, retry / timeout / fallback, call-trace telemetry. | [intelligent_agent.py](ai-agents/retail_agents/intelligent_agent.py) |
| 2 | **Quantitative inventory optimization** — safety stock, reorder point, EOQ, stockout probability, proportional allocation, supplier constraints. | [optimization.py](ai-agents/retail_agents/optimization.py) |
| 3 | **Business-impact simulation** — baseline vs AI 7-day P&L comparison (revenue, margin, carrying cost, aging, stockouts). | [simulation.py](ai-agents/retail_agents/simulation.py) |
| 4 | **Evaluation framework** — golden-dataset precision/recall/F1, WAPE/MAPE forecast error, false-positive detector, business-constraint checks. | [evaluation.py](ai-agents/retail_agents/evaluation.py) |
| 5 | **Explainability block** — evidence references with data timestamps, scoring breakdown, confidence rationale, decision summary. | [explainability.py](ai-agents/retail_agents/explainability.py) |
| 6 | **HITL governance workflow** — RBAC, state machine, audit log, expiry, idempotency, auto-escalation. | [governance.py](ai-agents/retail_agents/governance.py) |
| 7 | **Observability** — OpenTelemetry-compatible tracer + metrics sink (local fallback for CI). | [observability.py](ai-agents/retail_agents/observability.py) |
| 8 | **Security hardening** — row-level ACLs, PII masking, prompt-injection detection, tool authorization, secrets handling, audit log. | [security.py](ai-agents/retail_agents/security.py) |
| 9 | **FastAPI agents service** — the one HTTP contract between the .NET API and the Python agents. | [service.py](ai-agents/service.py) + [ai-agents/Dockerfile](ai-agents/Dockerfile) |
| 10 | **CI/CD** — four GitHub Actions workflows (Python, .NET, UI, docker-compose e2e) with security scanning. | [.github/workflows/](.github/workflows/) |

**45 new unit tests pass** across these modules (optimization, evaluation, governance, security, simulation + explainability).

---

## Changes done so far

Chronological delivery log (oldest first) — each row is one commit on `main`.

| # | Change | Scope |
|---|---|---|
| 1 | **Initial inventory-recommendation agent codebase** | Stdlib supervisor + 6 specialist agents (`retail_intelligence`, `product_recommendation`, `inventory_optimization`, `pricing_optimization`, `sales_forecasting`, `store_execution`), guardrails service (NeMo config + local policy engine), full .NET 8 Clean Architecture API (Domain / Application / Infrastructure / Api / Tests), React 18 + Vite UI shell (7 pages), standalone HTML daily report, pytest integration suite. |
| 2 | **Added Docker and README** | `docker-compose.yml`, top-level `README.md`, `pytest.ini`, `TODO.md`. |
| 3 | **Design and architecture flow added** | `ARCHITECTURE.html` landing page. |
| 4 | **Updated architecture flow with business problem** | Business-problem narrative baked into `ARCHITECTURE.html`. |
| 5 | **README refresh (×2)** | Documentation polish on the top-level README. |
| 6 | **LangChain integration for the agent** | `langchain_llm_provider.py`, `langchain_supervisor.py`, `langchain_tools.py`; requirements bumped; narrative LLM attached beside deterministic specialists. |
| 7 | **Review-comment code additions** | Nine new agent modules — `intelligent_agent.py` (structured Pydantic `AgentPlan` + retry/timeout/fallback), `optimization.py` (safety stock, ROP, EOQ, stockout probability), `simulation.py` (baseline vs AI 7-day P&L), `evaluation.py` (golden-dataset precision/recall/F1 + WAPE/MAPE), `explainability.py`, `governance.py` (HITL state machine, RBAC, TTL, audit), `observability.py` (OTel facade + local fallback), `security.py` (ACL, PII masking, prompt-injection), FastAPI `service.py` + `ai-agents/Dockerfile`; five new test modules (45 passing); four GitHub Actions workflows (`python.yml`, `dotnet.yml`, `ui.yml`, `e2e-stack.yml`); `docker-compose.yml` extended with the FastAPI `agents` service. |
| 8 | **CI workflows aligned to repo state** | `python.yml`, `dotnet.yml`, `ui.yml`, `e2e-stack.yml` corrected so path filters, matrix versions, and job steps match the actual tree. |
| 9 | **Architecture page updated with LangChain + new capability layers** | `ARCHITECTURE.html` extended to show intelligent agent, optimization, simulation, evaluation, governance, observability, security layers. |

Running totals after all changes:

- **71 pytest tests** across agents, guardrails, optimization, evaluation, governance, security, simulation, explainability.
- **3-service docker-compose stack** (agents + api + ui).
- **4 CI workflows** with path-filtered triggers.
- **9 read-only agent tools** behind one guarded call path.

---

## Technologies used

- **LangChain** (`langchain`, `langchain-core`) — tool-calling agent framework.
- **LangChain connectors** (`langchain-anthropic`, `langchain-openai`) — pluggable LLM backends.
- **Pydantic v2** — structured output + tool argument schemas.
- **FastAPI + Uvicorn** — Python agents HTTP service.
- **Python 3.11 / 3.12** — stdlib-only numeric core.
- **Databricks + Delta Lake** — Bronze / Silver / Gold layer with a local CSV adapter.
- **C# / .NET 8** — Clean Architecture API, FluentValidation, Serilog, Swagger.
- **React 18 + TypeScript + Vite + Recharts** — 7-page enterprise dashboard.
- **NVIDIA NeMo Guardrails** — input / output / tool-call policies with local fallback.
- **OpenTelemetry** (optional) — traces + metrics; local in-memory sink by default.
- **Docker + Docker Compose** — three-service local stack (agents + api + ui).
- **GitHub Actions** — Python matrix, .NET build, UI build, e2e compose smoke, dependency / secret / SAST scans.
- **Pytest** — regression suite (71 tests across agents, guardrails, sample data, optimization, evaluation, governance, security, simulation, explainability).

---

## The business problem it solves

Every retail store runs on a stream of time-pressured decisions before the
doors open. They are small individually, large in aggregate, and today they
are made from gut and spreadsheets rather than from the data every POS and
WMS already generates.

**The daily questions:** what goes on the front display today? which SKUs
need to move between stores? which prices should slide down this week before
margin bleeds? what's a realistic 7-day revenue target? which aged items
need a bundle vs. an outright markdown?

**What this platform is.** A decision assistant for that morning window:
prioritized daily action plans per store, grounded in evidence, bounded by
guardrails, gated by human approval, and now **measured** against a
golden-dataset harness and **simulated** against a do-nothing baseline so
reviewers can see the directional business impact, not just the agent's
output.

---

## End-to-end flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 1. Data layer (Databricks / local CSV)                                   │
│    sales · inventory · returns · surveys · trends · store_proximity      │
└──────────────────────┬───────────────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 2. ToolRegistry (9 read-only tools, the ONLY path to raw data)           │
│    Wrapped by `security.guarded_call` for ACL + PII + injection checks.  │
└──────────────────────┬───────────────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 3. IntelligentRetailAgent  (LLM planner)                                 │
│    LLM emits AgentPlan JSON → validated by Pydantic → repair-loop on     │
│    failure → fallback to deterministic plan. Retry + timeout per call.   │
└──────────────────────┬───────────────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 4. Deterministic specialists (authoritative numbers)                     │
│    Intelligence → Product / Inventory / Pricing / Forecast / Execution   │
│    + Quantitative optimizer: safety stock, ROP, EOQ, stockout prob.      │
└──────────────────────┬───────────────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 5. Guardrails (NeMo / local policy engine)                               │
│    Rejections recorded in agent_trace. Every allow/deny is audited.      │
└──────────────────────┬───────────────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 6. Explainability layer                                                  │
│    Evidence refs (source+metric+timestamp), scoring breakdown,           │
│    confidence rationale, what-could-go-wrong, decision summary.          │
└──────────────────────┬───────────────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 7. HITL governance                                                       │
│    State machine (pending→approved→executed), RBAC, TTL expiry,          │
│    idempotency, auto-escalation on margin/transfer thresholds.           │
└──────────────────────┬───────────────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 8. Simulation + Evaluation                                               │
│    SIMULATED baseline-vs-AI 7-day P&L.  Golden dataset: precision,       │
│    recall, F1.  Forecast error: WAPE / MAPE / bias.                      │
└──────────────────────┬───────────────────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ 9. Serving                                                               │
│    FastAPI agents svc  →  C# API (approvals + audit)  →  React UI        │
│                       └→  HTML report (reports/)                         │
│    Observability: tracer spans + counters/histograms → /metrics endpoint │
└──────────────────────────────────────────────────────────────────────────┘
```

### Step-by-step

1. **Generate / load retail data** (50 products × 5 stores × 90 days).
2. **Boot the stack** via `docker compose up` (agents + api + ui).
3. **UI → .NET API → `agents` service** (`/recommendations/{store}/intelligent`).
4. **Intelligent agent plans** — LLM returns an `AgentPlan`; validated; repaired if invalid; falls back to deterministic plan otherwise.
5. **Tools execute** with retry + timeout + telemetry.
6. **Deterministic specialists** produce the authoritative numbers.
7. **Explainability** attaches evidence + scoring breakdown.
8. **Governance** routes each recommendation to the right role, with TTL and audit.
9. **Simulation** computes directional business impact; **evaluation** scores quality.
10. **UI renders** the prioritized action plan and the simulation deltas.

---

## Agent code — key snippets

### Intelligent agent with structured output + resilience

```python
class AgentPlan(BaseModel):
    intent: str
    store_id: str
    tool_calls: list[ToolCall] = Field(default_factory=list, max_length=12)
    expected_outputs: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    fallback_strategy: str = "deterministic_specialists"

class IntelligentRetailAgent:
    def run(self, store_id, user_prompt="Build the daily game plan."):
        self.call_trace = []
        try:
            plan = self._llm_plan(store_id, user_prompt)           # structured JSON
            if validate_plan(plan, self.registry):                 # schema+business rules
                plan = deterministic_plan(store_id)
        except Exception:
            plan = deterministic_plan(store_id)                    # fallback

        tool_outputs = {}
        for tc in plan.tool_calls:
            tool_outputs[tc.name] = with_retry(                    # retry + timeout
                self.policy, f"tool.{tc.name}",
                lambda tc=tc: self.registry.call(tc.name, **tc.arguments),
                self.call_trace,
            )
        bundle = self.deterministic.analyze(store_id).to_dict()    # authoritative numbers
        bundle.update({"agent_plan": plan.model_dump(),
                       "call_trace": [c.model_dump() for c in self.call_trace],
                       "resilience_summary": _summarize_trace(self.call_trace)})
        return bundle
```

### Quantitative inventory optimization

```python
def safety_stock(demand_std_daily, lead_time_days, service_level):
    return _z_for_service_level(service_level) * demand_std_daily * math.sqrt(lead_time_days)

def reorder_point(demand_mean_daily, lead_time_days, safety):
    return demand_mean_daily * lead_time_days + safety

def economic_order_quantity(annual_demand, ordering_cost, unit_cost, holding_rate):
    return math.sqrt((2 * annual_demand * ordering_cost) / (unit_cost * holding_rate))

def stockout_probability(on_hand, mu_daily, sigma_daily, lead_time_days):
    mu, sigma = mu_daily * lead_time_days, sigma_daily * math.sqrt(lead_time_days)
    z = (on_hand - mu) / sigma
    return 0.5 * math.erfc(z / math.sqrt(2))
```

### Business-impact simulation

```python
def compare(skus, recommendations):
    base = simulate_baseline_week(skus)                 # do-nothing
    ai   = simulate_ai_week(skus, recommendations)      # AI-recommended
    return {
        "baseline": base.to_dict(), "ai": ai.to_dict(),
        "deltas": { "revenue_delta_pct": _pct(ai.revenue, base.revenue), ... },
        "assumptions": ASSUMPTIONS,                     # every coefficient documented
        "disclaimer": "SIMULATED RESULTS. ...",
    }
```

### Evaluation harness

```python
GOLDEN_SCENARIOS = [
    GoldenScenario("G002", "aged dead stock → markdown",
        inputs={"weekly_velocity": 0.4, "margin": 0.45, "on_hand": 80, "age_days": 215},
        expected_action_types={"MARKDOWN", "AGING_REVIEW"},
        forbidden_action_types={"FRONT_OFFICE", "REPLENISH"}),
    ...
]

report = run_full_evaluation(
    agent_outputs = {sid: [...]},     # what the agent produced per scenario
    recommendations = [...],          # all emitted recs
    actual_7d = [...], forecast_7d = [...],   # forecast accuracy
)
# → precision / recall / F1  +  WAPE / MAPE / bias
#   +  business_constraint violations  +  false_positives list
```

### HITL governance workflow

```python
store = GovernanceStore(ttl_hours=24)
gov = store.intake(rec_dict)                                   # auto-escalation applies
store.approve(gov.idempotency_key, "alice", Role.STORE_MANAGER, reason="looks good")
store.execute(gov.idempotency_key, "exec-svc")                 # idempotent

# Observable from the audit log:
for entry in gov.audit_log:
    print(entry.action, entry.actor, entry.actor_role, entry.reason)
```

### Security guard around every tool call

```python
principal = Principal(user_id="alice", role="store_manager",
                      allowed_stores={"S101"}, allowed_tools={"get_sales_summary"})

result = guarded_call(principal, "get_sales_summary", {"store_id": "S101"},
                      registry.call)
# ACL check  →  prompt-injection scan  →  invoke  →  PII mask on result
```

---

## Trade-off decisions taken during development

These are the engineering-leader calls where there was more than one reasonable
answer. Each lists the alternatives, the choice, and the reasoning.

### 1. Hybrid LLM + deterministic — not "all LLM"

- **Chosen:** keep every numeric decision in deterministic Python; let the LLM only call tools, plan, and narrate.
- **Why:** retail decisions are **auditable financial actions**. "The model felt it was right" is not a compliance answer. Deterministic metrics can be replayed exactly; the LLM adds explainability without adding non-determinism to the ledger.
- **Cost:** two code paths. The LLM cannot invent an action the specialists weren't designed for — that's acceptable in a regulated domain.

### 2. Structured output (Pydantic AgentPlan) over free-form

- **Chosen:** force the LLM to emit a Pydantic-validated `AgentPlan` JSON; repair-loop once if invalid; fall back to a hard-coded plan on second failure.
- **Why:** free-form LLM outputs mean every downstream consumer has to parse ambiguity. A schema makes failures explicit and recoverable.
- **Cost:** repair loop occasionally doubles LLM cost on bad days — bounded by retry policy.

### 3. Dynamic tool selection, bounded to 6 iterations and 12 tool calls

- **Chosen:** let the agent pick which tools to call based on the user intent, but cap `max_iterations=6` and `tool_calls max_length=12`.
- **Why:** a runaway agent on a store-manager's morning briefing is a cost and latency incident. Caps give room to be smart without being unbounded.

### 4. Retry/timeout/fallback at the TOOL layer, not just the LLM

- **Chosen:** every tool call wraps in `with_retry()`; failures emit a `CallRecord` and the whole call-trace rides on the output bundle.
- **Why:** most agent failures I've debugged come from flaky tools, not flaky LLMs. The trace lets ops see which tool is the problem without needing distributed tracing stood up.
- **Cost:** telemetry adds ~10% overhead; opt-out available by passing a `RetryPolicy(max_attempts=1)`.

### 5. Pluggable `BaseChatModel` instead of hard-coded provider

- **Chosen:** `get_chat_model()` dispatches on `RETAIL_LC_PROVIDER` (`anthropic` / `openai` / `none`).
- **Why:** a learner demoing this project today may have an OpenAI key; CI has neither. The `FakeListChatModel` fallback means every PR runs the full agent graph offline.

### 6. StructuredTool (Pydantic schemas) over `@tool`-decorated plain functions

- **Chosen:** every tool declares a Pydantic argument schema.
- **Why:** free-form arguments mean the LLM invents keyword names and the tool silently fails. Schemas catch drift at call time, not at loop end.

### 7. Narrative-only LLM: never alters metrics

- **Chosen:** `langchain_narrative` is attached **beside** the authoritative recommendations, not **inside** them.
- **Why:** a reviewer should be able to disable the LLM and still get identical approvals.

### 8. Golden dataset over "ask the LLM to grade itself"

- **Chosen:** a hand-curated `GOLDEN_SCENARIOS` list with expected and forbidden action types; precision/recall/F1 computed directly.
- **Why:** LLM-as-judge is pleasant to demo but useless as a regression trip-wire. A frozen dataset moves with the code and catches drift.

### 9. SIMULATED labels and open assumption dict

- **Chosen:** every simulation output carries a `disclaimer` field and an `assumptions` dict listing every coefficient used.
- **Why:** executive-dashboard numbers are a career-ending category of overclaim. Make the assumptions impossible to hide.

### 10. Governance in-memory for the learning scope, pluggable for production

- **Chosen:** `GovernanceStore` is a plain Python dict with a clean interface.
- **Why:** committing to Postgres + outbox + Kafka inside a learning repo would be over-engineering. The interface is small enough that a production team can back it with the real stack without touching callers.

### 11. Observability facade over hard OpenTelemetry dependency

- **Chosen:** `get_tracer()` returns a real OTel tracer when `RETAIL_OTEL_ENABLED=1` and the SDK is installed; otherwise an in-memory `LocalTracer`.
- **Why:** OTel is heavy and often not wired in a learner's environment. The facade lets the agent code emit spans unconditionally.

### 12. Security as code paths, not just documentation

- **Chosen:** actual Python ACL checks, PII regex masking, injection patterns — plus an audit log entry on every allow/deny.
- **Why:** a `security-design.md` file is a wish list. A `test_security.py` test suite is a contract.

### 13. GitHub Actions split across four files, not one monolith

- **Chosen:** `python.yml`, `dotnet.yml`, `ui.yml`, `e2e-stack.yml`.
- **Why:** path-filtered triggers mean a UI-only PR doesn't spin up the Python matrix (and vice versa). Faster iterations, smaller noise.

### 14. One HTTP contract between .NET and Python (FastAPI service)

- **Chosen:** `agents` is a service in `docker-compose.yml`; the .NET API calls it over HTTP.
- **Why:** `python3` subprocess per request has no connection pooling, no observability, and double-cold-starts on every call. A tiny FastAPI service costs ~30MB RAM and makes the whole stack testable in isolation.

### 15. Keep the stdlib supervisor as the default entry point

- **Chosen:** `run_supervisor` is stdlib-only; `IntelligentRetailAgent` is opt-in.
- **Why:** the stdlib path has **zero required dependencies**. Making LangChain mandatory would break anyone installing the agent package in a thin runtime.

---

## Hiccups faced during development

Honest list of things that didn't work the first time.

1. **FakeListChatModel doesn't implement `bind_tools`.** Great for CI but can't take tool calls. Fix: `create_tool_calling_agent` wrapped in try/except; falls back to deterministic-only output.
2. **LangChain renamed `MessagesPlaceholder` import paths twice** between 0.1 and 0.3. Settled on `langchain_core.prompts` because core churns less.
3. **`agent_scratchpad` placeholder is mandatory** for tool-calling agents. Missing it throws `KeyError('agent_scratchpad')` at the first LLM response.
4. **Pydantic v1 vs v2 BaseModel conflicts** in older LangChain versions. Pinning `pydantic>=2.5.0` and `langchain>=0.3.0` fixed it.
5. **Tool-call JSON serialization.** Registry returned `datetime` values. LangChain stringifies tool output; the agent couldn't parse it back. Fix: every tool returns JSON-serializable primitives.
6. **Guardrails ran twice** when the LLM also hit a tool. Deduplicated by moving validation to the supervisor only.
7. **Windows path handling** for guardrail service import broke on POSIX-style paths. Switched to `pathlib.Path(...).resolve()`.
8. **Circular import** between `supervisor.py` and `langchain_supervisor.py`. Reversed the dependency: LangChain imports stdlib supervisor, never the other way.
9. **`FakeListChatModel` responses exhaust** on long runs. Configured a single deterministic response.
10. **Max-iterations loop tuning.** `max_iterations=3` timed out; 6 is the sweet spot.
11. **Timeout on Windows.** `signal.SIGALRM` isn't available. Switched to threading-based timeout in `with_retry()`.
12. **Agent plan repair loop infinite-looped once** when the LLM kept emitting the same invalid output. Fix: single repair attempt, then fallback.
13. **Golden-dataset F1 was always 1.0** at first — expected sets were empty everywhere, so every miss counted as "no action expected" which collapsed FN to zero. Added a positive expected set per scenario.
14. **`stockout_probability` returned `nan`** when demand std was zero. Added a zero-std branch that returns 0.0 or 1.0 based on on-hand vs mean.
15. **Governance idempotency key included `created_at` to the second**, so two calls in the same request produced different keys. Truncated to the day.
16. **Allocation rounding** didn't preserve the total unit count. Added remainder-distribution step.
17. **Audit log grew unbounded** in long test runs. Documented that the production backend owns rotation — in-memory is for the learning scope.
18. **PII regex over-matched** on product IDs with embedded digits. Narrowed `card` and `customer_id` patterns.
19. **`SimulationRequest.recommendations: list[dict]`** can't be a plain `list` under Pydantic v2 without a type annotation. Added `list[dict]`.
20. **FastAPI `uvicorn` dockerfile layer-cache**. Installing uvicorn after `pip install -r requirements.txt` invalidated the cache; collapsed into a single install.

---

## Repository layout

```
databricks/         sample-data + Delta DDL + Bronze→Silver→Gold notebooks
api/                ASP.NET Core Web API (Clean Architecture, 5 projects)
ai-agents/          LangChain supervisor + 6 specialists + intelligent agent +
                    optimization + evaluation + simulation + governance +
                    observability + security + explainability + FastAPI service
ai-guardrails/      NeMo config + local policy engine + security tests
ui/                 React 18 + TypeScript + Vite dashboard (7 pages)
reports/            Standalone HTML daily decision report
.github/workflows/  Python / .NET / UI / e2e CI
docs/               Architecture, data dictionary, API, agent, security, business rules
docker-compose.yml  agents (FastAPI) + api (.NET) + ui (Vite)
```

---

## Quick start

```bash
# 1. Generate deterministic sample data (50 products × 5 stores × 90 days)
python databricks/generate_sample_data.py

# 2. Run the full stack (agents + API + UI)
docker compose up --build
# → http://localhost:5173           React dashboard
# → http://localhost:5080/swagger   .NET API
# → http://localhost:7071/docs      Python agents (FastAPI)
```

Or run pieces individually:

```bash
# Python agents service only
pip install -r ai-agents/requirements.txt
pip install fastapi uvicorn
PYTHONPATH=ai-agents python ai-agents/service.py

# Direct CLI run (no HTTP)
PYTHONPATH=ai-agents python -m retail_agents.supervisor S101
PYTHONPATH=ai-agents python -m retail_agents.intelligent_agent S101
PYTHONPATH=ai-agents python -m retail_agents.langchain_supervisor S101
```

### LLM backend (optional)

```bash
export RETAIL_LC_PROVIDER=anthropic    # or openai, or none for offline fake
export RETAIL_LC_MODEL=claude-opus-4-7
export ANTHROPIC_API_KEY=sk-ant-...
```

### Tests

```bash
PYTHONPATH=ai-agents python -m pytest
# 71 tests across agents, guardrails, optimization, evaluation,
# governance, security, simulation, explainability.
```

---

## Business scenarios implemented

| # | Scenario | Agent | Example |
|---|---|---|---|
| 1 | Front-office placement | ProductRecommendation | "Feature North Trail Boots — composite 0.89, 12 units/wk, 48% margin." |
| 2 | Inter-store transfer | InventoryOptimization | "Transfer 54 units S102 → S101. 17 weeks of cover at source." |
| 3 | Aging inventory | InventoryOptimization | "180+ days, 46.8% margin — 15% markdown with regional approval." |
| 4 | Pricing | PricingOptimization | "−5%; projected margin 37.1% stays above 10% floor." |
| 5 | Daily game plan | StoreExecution | Priority- and margin-ordered action plan. |
| 6 | Sales target | SalesForecasting | "7-day target $112,340 (+5% stretch)." |
| 7 | **Safety stock & ROP** | Optimization engine | "ROP = 42; EOQ = 180; stockout P = 2.1%." |
| 8 | **Baseline-vs-AI simulation** | simulation.compare | "+8.4% net profit, −32 aged units, 0 added stockouts (SIMULATED)." |
| 9 | **Golden-dataset evaluation** | evaluation.run_full_evaluation | "F1 = 0.92; 1 false positive; forecast WAPE = 0.11." |

---

## Verified during this build

- `python databricks/generate_sample_data.py` → 17,369 sales / 250 inventory / 1,024 surveys.
- `PYTHONPATH=ai-agents python -m pytest ai-agents/tests/test_optimization.py ai-agents/tests/test_evaluation.py ai-agents/tests/test_governance.py ai-agents/tests/test_security.py ai-agents/tests/test_simulation_explainability.py` → **45/45 passing**.
- All new modules import cleanly without LangChain installed (graceful degradation path verified).
- `docker-compose.yml` extended with a FastAPI `agents` service; `ai-agents/Dockerfile` builds it.
- `.github/workflows/*.yml` adds Python matrix, .NET build, UI build, e2e compose smoke, and dependency / SAST / secret scans.

---

## Environment constraints during this build

- The Python stack (data, agents, guardrails, report, tests, FastAPI service) runs on the build host.
- The C# API and React UI are complete source trees. Building them requires .NET 8 SDK and Node.js 20, which were not available on this build host; the CI workflows exercise them.
- LangChain and its provider SDKs are optional; the stdlib supervisor runs without them.

---

Attribution:
"An AI-powered retail decision intelligence learning implementation
demonstrating how Databricks, C#, React, LangChain-based Agentic AI, and
NVIDIA NeMo Guardrails can work together to transform retail data into
measurable store business outcomes."

Author: Pradeep Sahoo · Learning Implementation
