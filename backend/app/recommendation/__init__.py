"""Modular, versioned recommendation engine.

This package is intentionally free of FastAPI, SQLAlchemy, and heavy ML
dependencies so it is independently testable and can be replaced by a more
advanced ML model later (docs/05 §7). The service layer depends only on the
:class:`~app.recommendation.interfaces.Recommender` protocol resolved from the
:mod:`~app.recommendation.registry`.
"""

from app.recommendation.interfaces import (
    CandidateContext,
    ComponentBreakdown,
    RecommendationResult,
    Recommender,
    UserContext,
)
from app.recommendation.registry import get_recommender, list_versions, register
from app.recommendation.weights import DEFAULT_V1_WEIGHTS, ComponentWeights

__all__ = [
    "CandidateContext",
    "ComponentBreakdown",
    "ComponentWeights",
    "DEFAULT_V1_WEIGHTS",
    "RecommendationResult",
    "Recommender",
    "UserContext",
    "get_recommender",
    "list_versions",
    "register",
]
