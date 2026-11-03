# AI Guardrails

NVIDIA NeMo Guardrails integration with a local fallback.

## Design

- `config/config.yml` — NeMo rails, input/output flows, allowed topics.
- `config/prompts.yml` — self-check prompts.
- `service/guardrail_service.py` — the `GuardrailService` class. Loads
  NeMo if installed; always enforces the same policies locally so the
  stack behaves identically with or without the external package.
- `service/guardrail_cli.py` — stdin/stdout wrapper used by the C# API.
- `tests/test_guardrails.py` — policy tests (prompt injection, grounding,
  approval, PII scrubbing, role hierarchy).

## Install NeMo (optional)

```bash
pip install nemoguardrails
```

Set `RETAIL_GUARDRAILS_DISABLE_NEMO=1` to force the local policy engine
even when NeMo is installed — useful for deterministic tests.

## Policies enforced

1. **Input validation** — allow-listed intents, known store IDs, prompt
   injection patterns.
2. **PII protection** — email, SSN, phone patterns scrubbed from any
   string reaching the LLM.
3. **Topic restriction** — retail, inventory, pricing, promotions, sales
   targets, store operations.
4. **Tool invocation allowlist** — only registered agent tools can be
   called.
5. **Output validation** — recommendations must have evidence,
   bounded confidence, grounded IDs.
6. **Action authorization** — consequential actions require human
   approval; role hierarchy enforced.
7. **Hallucination mitigation** — product_id/store_id grounded against
   the master data.

Fail-closed on any policy error.

## Known limitations

- Pattern-based injection detection; a classifier model is the next step.
- Name/address PII is not scrubbed (pattern-based scrubber covers email,
  SSN, phone only).

Author: Pradeep Sahoo · Learning Implementation
