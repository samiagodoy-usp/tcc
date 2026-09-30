from __future__ import annotations

from collections.abc import Callable

from app.recommendation.components import (
    score_children_age_compatibility_asymmetric,
    score_shared_interests_symmetric_mean,
)
from app.recommendation.interfaces import (
    CHILDREN_AGE_COMPATIBILITY,
    SHARED_INTERESTS,
    Recommender,
)
from app.recommendation.weighted import WeightedHeuristicRecommender
from app.recommendation.weights import (
    DEFAULT_V1_WEIGHTS,
    DEFAULT_V2_WEIGHTS,
    DEFAULT_V3_WEIGHTS,
    ComponentWeights,
)

# Factories are used (not instances) so per-request configuration (e.g. custom
# weights or max distance from the DB/settings) can be applied at resolution time.
_REGISTRY: dict[str, Callable[..., Recommender]] = {}

# v3 is the current active algorithm: geo 0.40 / interests 0.30 / children-age
# 0.20 / meetup 0.10 / cultural 0.00. Shared interests use the symmetric mean of
# per-side overlap (½·(|A∩B|/|A| + |A∩B|/|B|)) instead of Jaccard. Children-age is
# keyed on whether each side has children: both childless -> 1.0, exactly one has
# children -> 0.0, both have children -> age-group overlap. v1/v2 remain
# registered for comparison.
DEFAULT_VERSION = "v3"


def register(version: str, factory: Callable[..., Recommender]) -> None:
    """Register a recommender factory under a version string."""
    _REGISTRY[version] = factory


def list_versions() -> list[str]:
    """Return all registered algorithm versions."""
    return sorted(_REGISTRY)


def get_recommender(
    version: str = DEFAULT_VERSION,
    *,
    weights: ComponentWeights | None = None,
    max_distance_km: float | None = None,
) -> Recommender:
    """Resolve a recommender for the given version.

    Raises ``KeyError`` for an unknown version.
    """
    if version not in _REGISTRY:
        raise KeyError(f"Unknown algorithm version: {version!r}. Known: {list_versions()}")
    kwargs: dict[str, object] = {}
    if weights is not None:
        kwargs["weights"] = weights
    if max_distance_km is not None:
        kwargs["max_distance_km"] = max_distance_km
    return _REGISTRY[version](**kwargs)


def _v1_factory(**kwargs: object) -> Recommender:
    kwargs.setdefault("weights", DEFAULT_V1_WEIGHTS)
    return WeightedHeuristicRecommender(version="v1", **kwargs)  # type: ignore[arg-type]


def _v2_factory(**kwargs: object) -> Recommender:
    kwargs.setdefault("weights", DEFAULT_V2_WEIGHTS)
    return WeightedHeuristicRecommender(version="v2", **kwargs)  # type: ignore[arg-type]


def _v3_factory(**kwargs: object) -> Recommender:
    # v3 = geo 0.40 / interests 0.30 / children-age 0.20 / meetup 0.10 + symmetric
    # -mean interest scoring + children-age scoring keyed on has-children:
    # both childless -> 1.0, exactly one has children -> 0.0, both have children ->
    # age-group overlap.
    kwargs.setdefault("weights", DEFAULT_V3_WEIGHTS)
    kwargs.setdefault(
        "scorers",
        {
            SHARED_INTERESTS: score_shared_interests_symmetric_mean,
            CHILDREN_AGE_COMPATIBILITY: score_children_age_compatibility_asymmetric,
        },
    )
    return WeightedHeuristicRecommender(version="v3", **kwargs)  # type: ignore[arg-type]


# Register algorithms. v3 is the active default; v1/v2 retained for comparison.
register("v1", _v1_factory)
register("v2", _v2_factory)
register("v3", _v3_factory)
