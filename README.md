# Retail Intelligence & Autonomous Store Decision Platform

**Author:** Pradeep Sahoo
**Purpose:** Learning Implementation

> An AI-powered retail decision intelligence learning implementation
> demonstrating how Databricks, C#, React, LangChain-based Agentic AI,
> and NVIDIA NeMo Guardrails can work together to transform retail data
> into measurable store business outcomes.

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

A **LangChain-driven supervisor** coordinates six specialists. Every
recommendation flows through a guardrail layer (NVIDIA NeMo Guardrails if
installed, or an equivalent local policy engine). Consequential actions
(pricing, transfers, markdowns, replenishment) always require human approval;
approvals and rejections are audited.

---

## Technologies used

- **LangChain** (`langchain`, `langchain-core`) — supervisor agent framework,
  tool-calling loop, provider-agnostic chat-model abstraction.
- **LangChain Anthropic / OpenAI connectors** (`langchain-anthropic`,
  `langchain-openai`) — pluggable LLM backends.
- **Pydantic v2** — tool argument schemas for structured tool calling.
- **Python 3.11** — stdlib-only deterministic specialists; LangChain layer sits on top.
- **Databricks + Delta Lake** — Bronze / Silver / Gold with a local CSV adapter for offline runs.
- **C# / .NET 8** — API layer: Clean Architecture, FluentValidation, Serilog, Swagger.
- **React 18 + TypeScript + Vite + Recharts** — 7-page enterprise dashboard.
- **NVIDIA NeMo Guardrails** — input / output / tool-call policies, with a local policy-engine fallback.
- **Pytest** — 26-case regression suite (agents, guardrails, sample data).
- **Docker Compose** — one-command local orchestration.

---

## Repository layout

```
databricks/         sample-data + Delta DDL + Bronze→Silver→Gold notebooks
api/                ASP.NET Core Web API (Clean Architecture, 5 projects)
ai-agents/          LangChain supervisor + 6 specialists + ToolRegistry
ai-guardrails/      NeMo config + local policy engine + security tests
ui/                 React 18 + TypeScript + Vite dashboard (7 pages)
reports/            Standalone HTML daily decision report
docs/               Architecture, data dictionary, API, agent, security, business rules
```

---

## LangChain agent code

The agent system is a **hybrid**: deterministic specialists own the numbers,
LangChain owns the reasoning and the natural-language layer on top. The LLM
can never invent a recommendation — it can only call auditable backend tools
and narrate what the deterministic engine already produced.

### 1. Tool shims (`langchain_tools.py`)

Each backend-grounded data accessor is exposed to LangChain as a
`StructuredTool` with a Pydantic schema so the LLM gets precise signatures:

```python
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

class _StoreIdOnly(BaseModel):
    store_id: str | None = Field(default=None, description="Store identifier, e.g. S101")

def build_langchain_tools(registry):
    def _wrap(name, args_schema, description):
        def _invoke(**kwargs):
            return registry.call(name, **{k: v for k, v in kwargs.items() if v is not None})
        return StructuredTool.from_function(
            func=_invoke, name=name, description=description, args_schema=args_schema,
        )
    return [
        _wrap("get_sales_summary",     _StoreIdOnly, "Per (store, product) 90-day sales features."),
        _wrap("get_inventory_position",_StoreIdOnly, "Inventory with aging/weeks-of-cover."),
        # ... 7 more tools ...
    ]
```

### 2. Provider-agnostic LLM (`langchain_llm_provider.py`)

Swap backends with one env var; the agent code is identical:

```python
def get_chat_model():
    provider = os.environ.get("RETAIL_LC_PROVIDER", "none").lower()
    temperature = float(os.environ.get("RETAIL_LC_TEMPERATURE", "0.1"))

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=os.environ.get("RETAIL_LC_MODEL", "claude-opus-4-7"),
                             temperature=temperature)
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=os.environ.get("RETAIL_LC_MODEL", "gpt-4o-mini"),
                          temperature=temperature)
    # Deterministic offline fallback for CI
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    return FakeListChatModel(responses=["[offline-fake-llm] deterministic metrics authoritative."])
```

### 3. LangChain supervisor (`langchain_supervisor.py`)

A ReAct-style supervisor built with `create_tool_calling_agent`:

```python
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

class LangChainSupervisor:
    def __init__(self, store=None, verbose=False):
        self.registry      = ToolRegistry(store=store)
        self.deterministic = SupervisorAgent(store=store)   # numbers authority
        self.tools         = build_langchain_tools(self.registry)
        self.llm           = get_chat_model()

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),            # grounding + rules
            ("human",  "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        self.executor = AgentExecutor(
            agent=agent, tools=self.tools, verbose=verbose,
            handle_parsing_errors=True, max_iterations=6,
        )

    def analyze(self, store_id: str) -> dict:
        bundle    = self.deterministic.analyze(store_id)       # source of truth
        narrative = self.executor.invoke({"input":
            f"Prepare the daily evidence pack for store {store_id}."})["output"]
        payload = bundle.to_dict()
        payload["langchain_narrative"]  = narrative
        payload["langchain_tools_used"] = [t.name for t in self.tools]
        return payload
```

### 4. The system prompt that binds the loop

```python
SYSTEM_PROMPT = """You are the retail Supervisor Agent for a daily store-decision platform.
You coordinate six specialist agents by calling backend tools. You never invent
numbers. Every claim must come from a tool call. Flag missing data instead of
guessing. Never recommend an action without citing the tool call that justified it."""
```

---

## End-to-end flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│ 1. Data layer (Databricks / local CSV adapter)                             │
│    POS sales · inventory snapshots · returns · surveys · trends · stores   │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 2. ToolRegistry (plain Python)                                             │
│    9 read-only functions — the ONLY path to raw data.                      │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 3. LangChainSupervisor                                                     │
│    ─ build_langchain_tools(registry)  → StructuredTool list                │
│    ─ create_tool_calling_agent(llm, tools, prompt)                         │
│    ─ AgentExecutor runs the ReAct loop up to 6 iterations                  │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 4. Deterministic specialists (parallel, same evidence pack)                │
│    RetailIntelligence → ProductRecommendation / InventoryOpt /             │
│    PricingOpt / SalesForecasting / StoreExecution                          │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 5. Guardrails (NeMo or local policy engine)                                │
│    Every Recommendation validated. Rejections recorded in agent_trace.     │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 6. Conflict resolution → Action plan → RecommendationBundle                │
│    One pricing + one aging action per product, priority-ordered.           │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 7. Consumers                                                               │
│    C# API (approvals + audit) → React UI (7 pages) → HTML daily report     │
└────────────────────────────────────────────────────────────────────────────┘
```

### Step-by-step

1. **Generate / load retail data** — 50 products × 5 stores × 90 days.
2. **Boot `LangChainSupervisor(store_id)`** — wires registry, tools, LLM, deterministic core.
3. **LangChain executor runs** — calls `get_inventory_position`, `get_sales_summary`, etc.; produces an evidence narrative.
4. **Deterministic specialists run** — each returns `Recommendation` objects with full metrics.
5. **Guardrail validation** — every recommendation is accepted or logged as rejected.
6. **Deduplication & conflict resolution** — supervisor picks the strongest action per (product, action-type).
7. **Action plan assembly** — priority- and margin-ordered final list.
8. **Serve downstream** — JSON to C# API, UI, or HTML report.

---

## Trade-off decisions taken during development

These are the engineering-leader decisions where there was more than one
reasonable answer. Each one lists the alternatives considered, the choice,
and the reasoning. (This is what reviewers usually want to see — not the
code, but the thinking.)

### 1. Hybrid LangChain + deterministic specialists — not "all LLM"

- **Option A:** Let a LangChain agent decide prices, transfers, and markdowns directly.
- **Option B (chosen):** Keep every numeric decision in deterministic Python; let the LLM only call tools and narrate.
- **Why:** Retail decisions are **auditable financial actions**. If a markdown
  is challenged in a compliance review three months later, "the model felt
  it was right" is not an answer. The deterministic path lets us *replay*
  any day's decisions exactly from the same data. The LLM adds explainability
  for humans; it does not add non-determinism to the ledger.
- **Cost of this choice:** more code (two paths instead of one), and the LLM
  cannot "discover" a creative action the specialists weren't designed for.
  That's an acceptable trade for a learning / regulated-domain system.

### 2. LangChain over writing our own ReAct loop

- **Option A:** Hand-rolled tool-calling loop (we had it in `supervisor.py`).
- **Option B (chosen):** `langchain.agents.AgentExecutor` + `create_tool_calling_agent`.
- **Why:** The hand-rolled version was ~80 lines and worked, but we were about
  to add retries, streaming, structured parsing-error recovery, and
  provider-switching. All of that is already in LangChain's executor, and
  battle-tested. Reinventing it would have been muscle-memory work with no
  product value.
- **Cost of this choice:** one more big dependency, slightly slower cold start,
  and we are now subject to LangChain's API churn.

### 3. Pluggable `BaseChatModel` instead of a hard-coded provider

- **Option A:** Ship with Anthropic only.
- **Option B (chosen):** `get_chat_model()` dispatches on `RETAIL_LC_PROVIDER`:
  `anthropic` / `openai` / `none`.
- **Why:** A learner demoing this project today may have an OpenAI key; next
  month, an Anthropic one. More importantly, **CI has neither**. The
  `FakeListChatModel` fallback means every PR can run the full agent graph
  offline. One contract, three backends.

### 4. StructuredTool (Pydantic) over plain `@tool`-decorated functions

- **Option A:** Use `@tool` with free-form string arguments.
- **Option B (chosen):** `StructuredTool.from_function` with explicit
  Pydantic `BaseModel` argument schemas.
- **Why:** Free-form arguments mean the LLM invents keyword names
  (`store`, `storeID`, `store_identifier`) and the tool silently fails. A
  Pydantic schema forces exact signatures and catches drift at call time,
  not at the end of the agent loop.

### 5. Narrative-only LLM — never alters metrics

- The LLM's output is attached to the bundle as `langchain_narrative`,
  **beside** the authoritative recommendations, not **inside** them.
- **Why:** A reviewer should be able to disable the LLM entirely and still get
  identical approvals. The narrative is a convenience layer, not a decision
  layer. This also keeps the test suite deterministic.

### 6. Keep the old stdlib `supervisor.py` as the default

- **Option A:** Replace `supervisor.py` with the LangChain supervisor.
- **Option B (chosen):** Keep both. `run_supervisor` = stdlib,
  `run_langchain_supervisor` = LangChain.
- **Why:** The `ai-agents/requirements.txt` had **no required dependencies**
  before this change. Making LangChain mandatory would break every downstream
  consumer who installs the agent package in a thin environment. Optional
  is cheaper than compulsory.

### 7. Max 6 agent iterations, not unlimited

- **Option A:** Default `AgentExecutor` (15 iterations).
- **Option B (chosen):** Capped at 6.
- **Why:** With 9 tools and a focused prompt, 6 is enough to build the
  evidence pack. Capping prevents a runaway loop from inflating LLM cost
  and from blocking a store manager's morning briefing.

### 8. Supervisor validates input through guardrails *before* the LLM runs

- **Option A:** Validate at tool-call time only.
- **Option B (chosen):** Validate the request itself first, then every
  tool call, then every recommendation.
- **Why:** Defense in depth. If an unknown `store_id` arrives, we fail fast
  and don't burn LLM tokens discovering that fact.

---

## Hiccups faced during development

Honest list of things that didn't work the first time.

1. **FakeListChatModel doesn't implement `bind_tools`.** The offline fallback
   is great for CI but can't take tool calls. Fix: `create_tool_calling_agent`
   is wrapped in try/except; if `bind_tools` raises, the executor is set to
   `None` and the supervisor falls back to deterministic-only output.

2. **LangChain renamed `MessagesPlaceholder` import paths twice** between 0.1
   and 0.3. Settled on `from langchain_core.prompts import ChatPromptTemplate,
   MessagesPlaceholder` because `langchain_core` is the stable core and much
   less likely to churn than the top-level `langchain` package.

3. **`agent_scratchpad` placeholder is mandatory for tool-calling agents.**
   Without it, the executor raises `KeyError('agent_scratchpad')` at the
   first LLM response. Not obvious from the docs; found via a stack trace.

4. **Pydantic v1 vs v2 BaseModel conflicts.** Some older LangChain versions
   shipped `langchain.pydantic_v1`. Pinning `pydantic>=2.5.0` and
   `langchain>=0.3.0` eliminated the dual-path headache.

5. **Tool-call JSON serialization.** Our registry returned Python objects
   with `datetime` values. LangChain stringifies tool output; the agent then
   couldn't parse it back. Fix: every tool now returns JSON-serializable
   primitives (`str`, `int`, `float`, `list`, `dict`).

6. **Guardrails run twice when the LLM also hits a tool.** Early version
   validated inside the tool shim AND inside the supervisor. Deduplicated
   by moving guardrail validation to the supervisor only; the tool shim is a
   dumb pass-through.

7. **Windows path handling for guardrail service import.** `sys.path.insert`
   with a POSIX-style path broke on Windows. Switched to `pathlib.Path`
   with `.resolve()` throughout; works on both.

8. **Circular import between `supervisor.py` and `langchain_supervisor.py`.**
   First draft had `supervisor.py` importing LangChain supervisor for
   backwards compat. Reversed: `langchain_supervisor.py` imports and reuses
   `SupervisorAgent`; the stdlib path has zero LangChain awareness.

9. **`FakeListChatModel` responses exhaust.** It cycles through a fixed list;
   long test runs produced empty strings. Fixed by configuring a single
   deterministic response that cycles indefinitely.

10. **Max-iterations loop vs. tool rate.** Setting `max_iterations=3` caused
    the agent to time-out before building the evidence pack. 6 is the
    empirical sweet spot for a 9-tool registry.

---

## Quick start

```bash
# 1. Generate deterministic sample data (50 products × 5 stores × 90 days)
python databricks/generate_sample_data.py

# 2. Install dependencies (LangChain + optional provider)
pip install -r ai-agents/requirements.txt
pip install langchain-anthropic   # or langchain-openai

# 3. Produce the standalone HTML decision report
python reports/generate_report.py S101
# → reports/daily-store-decision-report.html

# 4. Run the test suite
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

---

## End-to-end agent run (no API, no UI)

Deterministic (stdlib only):

```bash
PYTHONPATH=ai-agents python -m retail_agents.supervisor S101
```

LangChain-driven (LLM narrative + tool-calling):

```bash
export RETAIL_LC_PROVIDER=anthropic   # or openai, or none for offline fake
export RETAIL_LC_MODEL=claude-opus-4-7
export ANTHROPIC_API_KEY=sk-ant-...

PYTHONPATH=ai-agents python -m retail_agents.langchain_supervisor S101
```

Both return a `RecommendationBundle` JSON with the agent trace, action plan,
and every recommendation. The LangChain run additionally includes
`langchain_narrative` (English evidence summary) and
`langchain_tools_used` (tool-call list).

---

## Business scenarios implemented

| # | Scenario | Agent | Example |
|---|---|---|---|
| 1 | Front-office placement | ProductRecommendation | "Feature North Trail Hiking Boots in the front display — composite score 0.89, 12 units/wk, 48% margin, 0.72 demand signal." |
| 2 | Inter-store transfer | InventoryOptimization | "Transfer 54 units from S102 to S101 — destination 16.9/wk velocity, 13 on hand; source 9.4/wk velocity, 159 on hand (17 wk cover)." |
| 3 | Aging inventory | InventoryOptimization | "Age 180+, margin 46.8% — recommend 15% markdown with regional approval." |
| 4 | Pricing | PricingOptimization | "Decrease price 5% — weeks-of-cover 12, margin 42%; projected margin 37.1% stays above 10% floor." |
| 5 | Daily game plan | StoreExecution | Prioritized list ordered by priority and margin impact. |
| 6 | Sales target | SalesForecasting | "Set 7-day target to $112,340 (+5% stretch) based on day-of-week seasonal forecast." |

---

## Documentation

- `docs/architecture.md` and `docs/architecture-diagram.html`
- `docs/data-dictionary.md`
- `docs/api-specification.md`
- `docs/agent-design.md`
- `docs/security-design.md`
- `docs/business-rules.md`
- `docs/deployment-guide.md`

---

## Environment constraints during this build

- The Python stack (data, agents, guardrails, report, tests) runs on the build host.
- The C# API and React UI are complete source trees; building them requires
  installing .NET 8 SDK and Node.js 20, which were not available on the build
  host. See `docs/deployment-guide.md`.
- LangChain and its provider SDKs are optional; the stdlib supervisor runs
  without them.

---

## Verified during this build

- `python databricks/generate_sample_data.py` → 17,369 sales / 250 inventory snapshots / 1,024 surveys etc.
- `python -m retail_agents.supervisor S101` → 38 recommendations with priority, impact, evidence.
- `python -m retail_agents.langchain_supervisor S101` → identical recommendations + LangChain narrative.
- `python reports/generate_report.py S101` → styled HTML report with 38 action cards.
- `python -m pytest` → 26/26 passing (agents, guardrails, sample data).

---

Attribution:
"An AI-powered retail decision intelligence learning implementation
demonstrating how Databricks, C#, React, LangChain-based Agentic AI, and
NVIDIA NeMo Guardrails can work together to transform retail data into
measurable store business outcomes."

Author: Pradeep Sahoo · Learning Implementation
