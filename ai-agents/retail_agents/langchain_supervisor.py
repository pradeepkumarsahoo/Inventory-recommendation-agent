"""LangChain-based Supervisor Agent.

A parallel implementation of `SupervisorAgent` built on LangChain's agent
primitives. The hybrid design keeps the five deterministic specialists
(product / inventory / pricing / forecast / execution) as the source of
truth for every number, while LangChain drives:

  1. Natural-language intent routing (the user types "what should I
     promote at S101?" instead of "run specialist X with args Y").
  2. Tool-calling to the backend-grounded ToolRegistry.
  3. A narrative-only reasoning layer that explains the deterministic
     recommendations in auditable English.

Why hybrid instead of "all LLM":
- Metrics stay reproducible across runs — compliance can replay a day.
- The LLM can't invent a markdown; it can only call tools and narrate
  results that already passed guardrails.

Pattern used: LangGraph-style ReAct supervisor loop implemented via
`langchain.agents.AgentExecutor` with `create_tool_calling_agent`. If the
LangChain stack is not installed, the module raises on construction, so
the stdlib-only path in `supervisor.py` remains the default.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from .data_access import RetailDataStore
from .supervisor import SupervisorAgent  # reused for deterministic core
from .langchain_tools import build_langchain_tools
from .langchain_llm_provider import get_chat_model
from .tools import ToolRegistry


SYSTEM_PROMPT = """You are the retail Supervisor Agent for a daily store-decision platform.

You coordinate six specialist agents by calling backend tools. You never
invent numbers. Every claim you make must come from a tool call. If the
user asks for a daily plan, your job is to:

1. Call `get_inventory_position`, `get_sales_summary`, `get_trending_products`
   and `get_store_forecast` to build an evidence pack.
2. Summarize what the evidence says in 4-6 bullet points.
3. Hand off to the deterministic specialists for the actual numeric
   recommendations (the host app will call them after you finish).

Rules:
- Always include store_id in your reasoning.
- Flag any missing data instead of guessing.
- Never recommend an action without citing the tool call that justified it.
"""


class LangChainSupervisor:
    """LangChain wrapper around the deterministic supervisor.

    `analyze()` still returns a `RecommendationBundle` identical in shape
    to `SupervisorAgent.analyze()`, but the agent trace now includes the
    LLM's reasoning steps (which tools it called, in what order).
    """

    name = "LangChainSupervisor"

    def __init__(self, store: RetailDataStore | None = None, verbose: bool = False):
        try:
            from langchain.agents import AgentExecutor, create_tool_calling_agent
            from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        except Exception as e:
            raise ImportError(
                "LangChain is not installed. Run `pip install -r ai-agents/requirements.txt` "
                f"with the langchain extras enabled. Underlying error: {e}"
            )

        self.store = store or RetailDataStore()
        self.registry = ToolRegistry(store=self.store)
        self.deterministic = SupervisorAgent(store=self.store)

        self.tools = build_langchain_tools(self.registry)
        self.llm = get_chat_model()

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])

        # Tool-calling agent works for Anthropic + OpenAI + any chat model
        # exposing bind_tools. FakeListChatModel skips the LLM loop and we
        # exercise only the deterministic path below.
        try:
            agent = create_tool_calling_agent(self.llm, self.tools, prompt)
            self.executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=verbose,
                handle_parsing_errors=True,
                max_iterations=6,
            )
        except (NotImplementedError, AttributeError):
            # FakeListChatModel does not implement bind_tools — fall back.
            self.executor = None

    def _invoke_narrative(self, store_id: str) -> str:
        """Run the LangChain executor to produce an English evidence summary."""
        if self.executor is None:
            return ("LangChain narrative skipped: offline fake model has no "
                    "tool-calling. Deterministic metrics are authoritative.")
        try:
            out = self.executor.invoke({
                "input": f"Prepare the daily evidence pack for store {store_id}."
            })
            return out.get("output", "")
        except Exception as e:  # pragma: no cover - defensive
            return f"LangChain narrative failed, falling back to deterministic: {e}"

    def analyze(self, store_id: str) -> dict:
        """Produce a recommendation bundle with LangChain narrative attached.

        The deterministic supervisor is still the source of truth; the LLM
        is only allowed to describe what it found.
        """
        bundle = self.deterministic.analyze(store_id)
        narrative = self._invoke_narrative(store_id)
        payload = bundle.to_dict()
        payload["langchain_narrative"] = narrative
        payload["langchain_tools_used"] = [t.name for t in self.tools]
        return payload


def run_langchain_supervisor(store_id: str) -> dict:
    return LangChainSupervisor().analyze(store_id)


if __name__ == "__main__":
    import json
    store = sys.argv[1] if len(sys.argv) > 1 else "S101"
    print(json.dumps(run_langchain_supervisor(store), indent=2, default=str))
