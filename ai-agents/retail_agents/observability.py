"""Observability layer: OpenTelemetry-compatible metrics + traces.

A thin facade over OpenTelemetry so the agent code can emit spans, counters,
and histograms without hard-depending on `opentelemetry-*` packages. If the
real SDK is installed, spans export to the configured OTLP endpoint
(Prometheus / Grafana / Jaeger). If not, the facade degrades to an in-memory
`MetricsSink` suitable for CI and local test assertions.

Signals captured:
- `agent_execution_duration_seconds` histogram (per agent name)
- `tool_invocations_total` counter (name, status)
- `llm_tokens_total` counter (prompt_tokens, completion_tokens)
- `recommendation_outcomes_total` counter (action, state)
- `agent_retries_total` counter (tool)

Usage:
    tracer = get_tracer("retail-agents")
    with tracer.span("supervisor.analyze", attributes={"store_id": "S101"}):
        ...
    METRICS.increment("tool_invocations_total", 1, {"name": "get_sales_summary", "status": "ok"})
"""
from __future__ import annotations

import contextlib
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

logger = logging.getLogger(__name__)


# ---------- In-memory fallback sink -----------------------------------------

@dataclass
class MetricsSink:
    counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = field(default_factory=dict)
    histograms: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = \
        field(default_factory=lambda: defaultdict(list))
    spans: list[dict] = field(default_factory=list)

    def _key(self, name: str, labels: dict[str, str] | None) -> tuple:
        return (name, tuple(sorted((labels or {}).items())))

    def increment(self, name: str, value: float = 1.0,
                  labels: Optional[dict[str, str]] = None) -> None:
        k = self._key(name, labels)
        self.counters[k] = self.counters.get(k, 0.0) + value

    def observe(self, name: str, value: float,
                labels: Optional[dict[str, str]] = None) -> None:
        self.histograms[self._key(name, labels)].append(value)

    def record_span(self, span: dict) -> None:
        self.spans.append(span)

    def snapshot(self) -> dict[str, Any]:
        def _lbl(labels: tuple[tuple[str, str], ...]) -> dict[str, str]:
            return dict(labels)
        return {
            "counters": [
                {"name": name, "labels": _lbl(labels), "value": v}
                for (name, labels), v in self.counters.items()
            ],
            "histograms": [
                {
                    "name": name, "labels": _lbl(labels),
                    "count": len(vs),
                    "sum": round(sum(vs), 4),
                    "p50": _percentile(vs, 0.50),
                    "p95": _percentile(vs, 0.95),
                }
                for (name, labels), vs in self.histograms.items()
            ],
            "spans": self.spans,
        }


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = int(round((len(s) - 1) * p))
    return round(s[k], 4)


METRICS = MetricsSink()


# ---------- Tracer facade ---------------------------------------------------

class _NoOpSpan:
    def set_attribute(self, *_args, **_kw): pass
    def record_exception(self, *_args, **_kw): pass
    def set_status(self, *_args, **_kw): pass


class LocalTracer:
    def __init__(self, name: str):
        self.name = name

    @contextlib.contextmanager
    def span(self, span_name: str,
             attributes: Optional[dict[str, Any]] = None) -> Iterator[Any]:
        start = time.monotonic()
        status = "ok"
        try:
            yield _NoOpSpan()
        except Exception as e:
            status = "error"
            raise
        finally:
            duration = (time.monotonic() - start) * 1000
            METRICS.observe(f"{self.name}.duration_ms", duration,
                            {"span": span_name, "status": status})
            METRICS.record_span({
                "name": span_name, "tracer": self.name,
                "duration_ms": round(duration, 3),
                "status": status, "attributes": attributes or {},
            })


class _OTelTracer:  # pragma: no cover - integration path
    def __init__(self, name: str):
        from opentelemetry import trace
        self._t = trace.get_tracer(name)

    @contextlib.contextmanager
    def span(self, span_name: str,
             attributes: Optional[dict[str, Any]] = None) -> Iterator[Any]:
        with self._t.start_as_current_span(span_name, attributes=attributes or {}) as s:
            yield s


def _otel_available() -> bool:  # pragma: no cover
    try:
        import opentelemetry  # noqa: F401
        return True
    except Exception:
        return False


def get_tracer(name: str = "retail-agents"):
    if os.environ.get("RETAIL_OTEL_ENABLED", "0") == "1" and _otel_available():
        return _OTelTracer(name)  # pragma: no cover
    return LocalTracer(name)


# ---------- Convenience helpers used by other modules ----------------------

def record_tool_call(name: str, status: str, duration_ms: float) -> None:
    METRICS.increment("tool_invocations_total", 1, {"name": name, "status": status})
    METRICS.observe("tool_duration_ms", duration_ms, {"name": name})


def record_llm_usage(prompt_tokens: int, completion_tokens: int, model: str) -> None:
    METRICS.increment("llm_tokens_total", prompt_tokens, {"model": model, "kind": "prompt"})
    METRICS.increment("llm_tokens_total", completion_tokens, {"model": model, "kind": "completion"})


def record_recommendation_outcome(action_type: str, state: str) -> None:
    METRICS.increment("recommendation_outcomes_total", 1,
                      {"action": action_type, "state": state})


def record_retry(tool: str) -> None:
    METRICS.increment("agent_retries_total", 1, {"tool": tool})
