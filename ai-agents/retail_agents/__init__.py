"""Retail intelligence agent package.

Public entry points:
    - run_supervisor(store_id): deterministic stdlib supervisor.
    - run_langchain_supervisor(store_id): LangChain-driven supervisor
      with LLM narrative on top of the deterministic recommendations.
    - Individual specialist agents are importable for direct use or testing.
"""
from .supervisor import SupervisorAgent, run_supervisor  # noqa: F401
from .data_access import RetailDataStore  # noqa: F401
from .models import Recommendation, RecommendationBundle  # noqa: F401

try:  # LangChain is optional
    from .langchain_supervisor import LangChainSupervisor, run_langchain_supervisor  # noqa: F401
    _LC_AVAILABLE = True
except Exception:  # pragma: no cover - import guard
    _LC_AVAILABLE = False

__all__ = [
    "SupervisorAgent",
    "run_supervisor",
    "RetailDataStore",
    "Recommendation",
    "RecommendationBundle",
]
if _LC_AVAILABLE:
    __all__ += ["LangChainSupervisor", "run_langchain_supervisor"]
