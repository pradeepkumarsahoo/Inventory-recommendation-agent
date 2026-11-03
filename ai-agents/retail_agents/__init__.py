"""Retail intelligence agent package.

Public entry points:
    - run_supervisor(store_id): produces the daily store game plan.
    - Individual specialist agents are importable for direct use or testing.
"""
from .supervisor import SupervisorAgent, run_supervisor  # noqa: F401
from .data_access import RetailDataStore  # noqa: F401
from .models import Recommendation, RecommendationBundle  # noqa: F401

__all__ = [
    "SupervisorAgent",
    "run_supervisor",
    "RetailDataStore",
    "Recommendation",
    "RecommendationBundle",
]
