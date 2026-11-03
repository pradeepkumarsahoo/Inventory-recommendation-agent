"""Retail intelligence agent package.

Public entry points:
    - run_supervisor(store_id): deterministic stdlib supervisor.
    - run_langchain_supervisor(store_id): LangChain-driven supervisor
      with LLM narrative on top of the deterministic recommendations.
    - IntelligentRetailAgent: full agentic loop with structured output,
      retry/timeout, dynamic tool selection, fallback.
    - Individual specialist agents are importable for direct use or testing.
"""
from .supervisor import SupervisorAgent, run_supervisor  # noqa: F401
from .data_access import RetailDataStore  # noqa: F401
from .models import Recommendation, RecommendationBundle  # noqa: F401
from .intelligent_agent import IntelligentRetailAgent  # noqa: F401
from .optimization import (  # noqa: F401
    InventoryParameters, optimize_sku, score_position,
)
from .evaluation import run_full_evaluation  # noqa: F401
from .simulation import compare, SKUState  # noqa: F401
from .governance import GovernanceStore, Role, RecommendationState  # noqa: F401
from .explainability import explain, explain_all  # noqa: F401
from .observability import METRICS, get_tracer  # noqa: F401
from .security import Principal, guarded_call, mask_pii  # noqa: F401

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
    "IntelligentRetailAgent",
    "InventoryParameters",
    "optimize_sku",
    "score_position",
    "run_full_evaluation",
    "compare",
    "SKUState",
    "GovernanceStore",
    "Role",
    "RecommendationState",
    "explain",
    "explain_all",
    "METRICS",
    "get_tracer",
    "Principal",
    "guarded_call",
    "mask_pii",
]
if _LC_AVAILABLE:
    __all__ += ["LangChainSupervisor", "run_langchain_supervisor"]
