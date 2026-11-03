"""Pluggable LLM provider.

Default is `NullProvider`, which short-circuits every call and returns a
deterministic string. Real providers (`AnthropicProvider`,
`OpenAIProvider`) are imported lazily, so the stack has no required SDK
dependency. Configuration is through environment variables:

- RETAIL_LLM_PROVIDER = none | anthropic | openai  (default: none)
- ANTHROPIC_API_KEY, RETAIL_LLM_MODEL (defaults to claude-opus-4-7)
- OPENAI_API_KEY, RETAIL_LLM_MODEL  (defaults to gpt-4o-mini)

The LLM is used only for NARRATIVE on top of deterministic analytics.
It never alters recommendation metrics or approves actions.
"""
from __future__ import annotations

import os
from typing import Any


class NullProvider:
    name = "null"

    def generate(self, prompt: str, context: dict[str, Any] | None = None) -> str:
        return "[deterministic mode] Narrative generation is disabled; metrics unchanged."


class AnthropicProvider:  # pragma: no cover - integration path
    name = "anthropic"

    def __init__(self):
        import anthropic  # type: ignore
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = os.environ.get("RETAIL_LLM_MODEL", "claude-opus-4-7")

    def generate(self, prompt: str, context: dict[str, Any] | None = None) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(getattr(b, "text", "") for b in msg.content)


class OpenAIProvider:  # pragma: no cover - integration path
    name = "openai"

    def __init__(self):
        from openai import OpenAI  # type: ignore
        self.client = OpenAI()
        self.model = os.environ.get("RETAIL_LLM_MODEL", "gpt-4o-mini")

    def generate(self, prompt: str, context: dict[str, Any] | None = None) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
        )
        return resp.choices[0].message.content or ""


def get_provider():
    choice = os.environ.get("RETAIL_LLM_PROVIDER", "none").lower()
    if choice == "anthropic":
        return AnthropicProvider()
    if choice == "openai":
        return OpenAIProvider()
    return NullProvider()
