"""LangChain-backed LLM provider.

Replaces the vendor-specific `llm_provider.py` with a single abstraction
that LangChain's `ChatModel` interface already gives us: swap backends
by changing one environment variable, keep the agent code identical.

Supported providers (lazy-imported; install only what you use):
- RETAIL_LC_PROVIDER=anthropic  →  langchain-anthropic
- RETAIL_LC_PROVIDER=openai     →  langchain-openai
- RETAIL_LC_PROVIDER=none       →  FakeListChatModel (offline / tests)

Env knobs: RETAIL_LC_MODEL, RETAIL_LC_TEMPERATURE (default 0.1).
"""
from __future__ import annotations

import os
from typing import Any


def get_chat_model() -> Any:
    """Return a configured LangChain `BaseChatModel`.

    The default is a deterministic fake model so the full LangChain agent
    graph can be exercised in CI without network or API keys.
    """
    provider = os.environ.get("RETAIL_LC_PROVIDER", "none").lower()
    temperature = float(os.environ.get("RETAIL_LC_TEMPERATURE", "0.1"))

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic  # type: ignore
        model = os.environ.get("RETAIL_LC_MODEL", "claude-opus-4-7")
        return ChatAnthropic(model=model, temperature=temperature)

    if provider == "openai":
        from langchain_openai import ChatOpenAI  # type: ignore
        model = os.environ.get("RETAIL_LC_MODEL", "gpt-4o-mini")
        return ChatOpenAI(model=model, temperature=temperature)

    # Offline fallback. FakeListChatModel cycles through a fixed response list,
    # so unit tests still produce stable traces when no key is available.
    from langchain_core.language_models.fake_chat_models import FakeListChatModel  # type: ignore
    return FakeListChatModel(responses=[
        "[offline-fake-llm] Deterministic analytics drive this recommendation; "
        "the LLM narrative layer is disabled because no provider is configured."
    ])
