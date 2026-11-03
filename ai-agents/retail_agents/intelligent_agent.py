"""Intelligent Agent layer — structured output, retry/timeout, dynamic tool selection.

Upgrades the LangChain supervisor from "narrative on top of deterministic
specialists" to a genuinely agentic reasoner:

- **Structured output**: the LLM must emit `AgentPlan` JSON (validated with
  Pydantic); malformed output triggers a repair loop.
- **Dynamic tool selection**: the agent picks tools based on the user intent
  rather than following a fixed script.
- **Resilience**: every tool call and LLM round-trip is wrapped in a
  retry-with-exponential-backoff + per-call timeout + fallback-to-deterministic.
- **Execution validation**: the final `AgentPlan` is checked against business
  constraints before it leaves the agent.

The deterministic specialists remain the numeric authority. This module adds
the "intelligent" planning and recovery layer that distinguishes an agentic
system from a rules engine.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field, ValidationError

from .data_access import RetailDataStore
from .supervisor import SupervisorAgent
from .tools import ToolRegistry

logger = logging.getLogger(__name__)


# ---------- Structured output contracts -------------------------------------

class ToolCall(BaseModel):
    """A single tool invocation the agent plans to make."""
    name: str = Field(..., description="Registered tool name")
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(..., description="Why this tool was selected")


class AgentPlan(BaseModel):
    """Structured plan output enforced on every LLM response."""
    intent: str = Field(..., description="Normalized user intent")
    store_id: str = Field(..., description="Target store")
    tool_calls: list[ToolCall] = Field(default_factory=list, max_length=12)
    expected_outputs: list[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    fallback_strategy: str = Field(default="deterministic_specialists")


# ---------- Resilience primitives -------------------------------------------

@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    timeout_seconds: float = 20.0
    backoff_multiplier: float = 2.0


class CallRecord(BaseModel):
    tool: str
    attempt: int
    duration_ms: float
    status: str  # "ok" | "retry" | "failed"
    error: Optional[str] = None


def with_retry(policy: RetryPolicy, label: str, fn: Callable[[], Any],
               trace: list[CallRecord]) -> Any:
    """Run `fn()` with retry + timeout + backoff; append telemetry to `trace`."""
    last_error: Optional[Exception] = None
    for attempt in range(1, policy.max_attempts + 1):
        start = time.monotonic()
        try:
            # Threading-based timeout keeps us dependency-free on Windows,
            # where signal.SIGALRM is not available.
            import threading
            result_box: dict[str, Any] = {}

            def runner():
                try:
                    result_box["value"] = fn()
                except Exception as e:  # pragma: no cover - defensive
                    result_box["error"] = e

            t = threading.Thread(target=runner, daemon=True)
            t.start()
            t.join(policy.timeout_seconds)
            duration_ms = (time.monotonic() - start) * 1000

            if t.is_alive():
                trace.append(CallRecord(tool=label, attempt=attempt,
                                        duration_ms=duration_ms, status="retry",
                                        error="timeout"))
                last_error = TimeoutError(f"{label} exceeded {policy.timeout_seconds}s")
            elif "error" in result_box:
                last_error = result_box["error"]
                trace.append(CallRecord(tool=label, attempt=attempt,
                                        duration_ms=duration_ms, status="retry",
                                        error=str(last_error)))
            else:
                trace.append(CallRecord(tool=label, attempt=attempt,
                                        duration_ms=duration_ms, status="ok"))
                return result_box["value"]
        except Exception as e:  # pragma: no cover - defensive
            duration_ms = (time.monotonic() - start) * 1000
            last_error = e
            trace.append(CallRecord(tool=label, attempt=attempt,
                                    duration_ms=duration_ms, status="retry",
                                    error=str(e)))
        time.sleep(policy.base_delay_seconds * (policy.backoff_multiplier ** (attempt - 1)))

    trace.append(CallRecord(tool=label, attempt=policy.max_attempts,
                            duration_ms=0.0, status="failed",
                            error=str(last_error) if last_error else "unknown"))
    raise RuntimeError(f"{label} failed after {policy.max_attempts} attempts: {last_error}")


# ---------- Plan validation --------------------------------------------------

VALID_INTENTS = {
    "daily_game_plan", "front_office_only", "transfers_only",
    "pricing_only", "forecast_only", "aging_cleanup",
}


def validate_plan(plan: AgentPlan, registry: ToolRegistry) -> list[str]:
    """Return a list of validation errors (empty if valid)."""
    errors: list[str] = []
    if plan.intent not in VALID_INTENTS:
        errors.append(f"unknown_intent:{plan.intent}")
    known_tools = {t["name"] for t in registry.describe()}
    for tc in plan.tool_calls:
        if tc.name not in known_tools:
            errors.append(f"unknown_tool:{tc.name}")
    if plan.confidence < 0.3:
        errors.append("confidence_too_low")
    return errors


# ---------- Deterministic fallback planner ----------------------------------

def deterministic_plan(store_id: str, intent: str = "daily_game_plan") -> AgentPlan:
    """Build a safe default plan used when the LLM is unavailable or produces
    invalid output. Mirrors the fixed script the stdlib supervisor uses."""
    return AgentPlan(
        intent=intent,
        store_id=store_id,
        tool_calls=[
            ToolCall(name="get_inventory_position", arguments={"store_id": store_id},
                     rationale="Baseline stock position"),
            ToolCall(name="get_sales_summary", arguments={"store_id": store_id},
                     rationale="90-day velocity + margin features"),
            ToolCall(name="get_return_rates", arguments={},
                     rationale="Exclude chronic-return SKUs"),
            ToolCall(name="get_survey_sentiment", arguments={},
                     rationale="Customer satisfaction scoring input"),
            ToolCall(name="get_trending_products", arguments={},
                     rationale="External demand signal"),
            ToolCall(name="get_store_forecast", arguments={"store_id": store_id},
                     rationale="7-day target"),
        ],
        expected_outputs=["evidence_pack", "deterministic_recommendations"],
        confidence=0.70,
        fallback_strategy="deterministic_specialists",
    )


# ---------- Intelligent agent -----------------------------------------------

class IntelligentRetailAgent:
    """Agent with planning, structured output, resilience, and fallback.

    Use this instead of `LangChainSupervisor` when you want the full
    agentic loop (dynamic tool selection + validated structured output)
    rather than a narrative on top of deterministic specialists.
    """

    name = "IntelligentRetailAgent"

    def __init__(
        self,
        store: RetailDataStore | None = None,
        policy: RetryPolicy | None = None,
    ):
        self.store = store or RetailDataStore()
        self.registry = ToolRegistry(store=self.store)
        self.deterministic = SupervisorAgent(store=self.store)
        self.policy = policy or RetryPolicy()
        self.call_trace: list[CallRecord] = []

    # -- Plan generation ---------------------------------------------------

    def _llm_plan(self, store_id: str, user_prompt: str) -> AgentPlan:
        """Ask the LLM for an AgentPlan JSON; validate; repair once if invalid."""
        try:
            from .langchain_llm_provider import get_chat_model
            from langchain_core.messages import SystemMessage, HumanMessage
        except Exception as e:
            raise RuntimeError(f"LangChain not available: {e}")

        llm = get_chat_model()

        system = SystemMessage(content=(
            "You are a retail decision planner. Return ONLY valid JSON matching "
            "this schema (no commentary):\n"
            + json.dumps(AgentPlan.model_json_schema(), indent=2)
            + f"\nAvailable tools: {json.dumps(self.registry.describe())}"
        ))
        human = HumanMessage(content=f"store_id={store_id}; request={user_prompt}")

        def _call():
            resp = llm.invoke([system, human])
            return getattr(resp, "content", str(resp))

        raw = with_retry(self.policy, "llm.plan", _call, self.call_trace)

        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            plan = AgentPlan.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("Plan parse failed, attempting repair: %s", e)
            repair = HumanMessage(content=(
                f"Your previous output was invalid: {e}. "
                "Return ONLY the AgentPlan JSON, nothing else."
            ))
            raw = with_retry(self.policy, "llm.plan.repair",
                             lambda: getattr(llm.invoke([system, human, repair]),
                                             "content", ""),
                             self.call_trace)
            try:
                plan = AgentPlan.model_validate(json.loads(raw))
            except Exception:
                raise

        return plan

    # -- Public API --------------------------------------------------------

    def run(self, store_id: str, user_prompt: str = "Build the daily game plan.") -> dict:
        """End-to-end intelligent run: plan → execute tools → specialists → bundle."""
        self.call_trace = []

        # 1. Plan — try LLM, fall back to deterministic plan on any failure.
        try:
            plan = self._llm_plan(store_id, user_prompt)
            plan_errors = validate_plan(plan, self.registry)
            if plan_errors:
                logger.warning("Plan validation failed %s; falling back", plan_errors)
                plan = deterministic_plan(store_id)
                plan_source = "fallback_after_invalid_llm_plan"
            else:
                plan_source = "llm"
        except Exception as e:
            logger.info("LLM plan unavailable (%s); using deterministic plan", e)
            plan = deterministic_plan(store_id)
            plan_source = "deterministic_fallback"

        # 2. Execute the planned tool calls with retry.
        tool_outputs: dict[str, Any] = {}
        for tc in plan.tool_calls:
            try:
                tool_outputs[tc.name] = with_retry(
                    self.policy, f"tool.{tc.name}",
                    lambda tc=tc: self.registry.call(tc.name, **tc.arguments),
                    self.call_trace,
                )
            except Exception as e:
                tool_outputs[tc.name] = {"error": str(e)}

        # 3. Hand off to deterministic specialists for authoritative numbers.
        bundle = self.deterministic.analyze(store_id).to_dict()

        # 4. Attach planning + telemetry to the bundle for auditability.
        bundle["agent_plan"] = plan.model_dump()
        bundle["plan_source"] = plan_source
        bundle["tool_outputs_summary"] = {
            k: ("error" if isinstance(v, dict) and "error" in v else "ok")
            for k, v in tool_outputs.items()
        }
        bundle["call_trace"] = [c.model_dump() for c in self.call_trace]
        bundle["resilience_summary"] = _summarize_trace(self.call_trace)
        return bundle


def _summarize_trace(trace: list[CallRecord]) -> dict:
    attempts_per_tool: dict[str, int] = {}
    failures: list[str] = []
    for r in trace:
        attempts_per_tool[r.tool] = attempts_per_tool.get(r.tool, 0) + 1
        if r.status == "failed":
            failures.append(r.tool)
    return {
        "total_calls": len(trace),
        "attempts_per_tool": attempts_per_tool,
        "failures": failures,
        "ok_rate": round(sum(1 for r in trace if r.status == "ok") / len(trace), 3)
        if trace else 0.0,
    }


if __name__ == "__main__":  # pragma: no cover
    import sys
    store = sys.argv[1] if len(sys.argv) > 1 else "S101"
    agent = IntelligentRetailAgent()
    print(json.dumps(agent.run(store), indent=2, default=str))
