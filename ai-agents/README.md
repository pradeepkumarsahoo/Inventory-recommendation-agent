# AI Agents

Supervisor + specialist agents for retail decision intelligence.

## Run the supervisor

```bash
cd ..
PYTHONPATH=ai-agents python -m retail_agents.supervisor S101
```

Returns a JSON `RecommendationBundle` on stdout: the daily game plan,
agent trace, and insights.

## Package layout

```
retail_agents/
    __init__.py            # public entry points
    supervisor.py          # SupervisorAgent + run_supervisor
    models.py              # Recommendation / RecommendationBundle
    data_access.py         # Local CSV / Databricks adapters
    features.py            # Shared feature engineering
    tools.py               # Backend-grounded ToolRegistry
    llm_provider.py        # Null / Anthropic / OpenAI providers
    agents/
        retail_intelligence.py
        product_recommendation.py
        inventory_optimization.py
        pricing_optimization.py
        sales_forecasting.py
        store_execution.py
tests/
    test_agents.py         # End-to-end + unit tests
```

## LLM mode (optional)

Default is deterministic (`NullProvider`). Set:

```
RETAIL_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-...
RETAIL_LLM_MODEL=claude-opus-4-7
```

The LLM is used for narrative; metrics never come from the LLM.

## Tests

```bash
python -m pytest ai-agents/tests
```

Author: Pradeep Sahoo · Learning Implementation
