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
    DEFAULT_V3_WEIGHTS,
    ComponentWeights,
)


_REGISTRY: dict[str, Callable[..., Recommender]] = {}

DEFAULT_VERSION = "v3"


def register(version: str, factory: Callable[..., Recommender]) -> None:

    _REGISTRY[version] = factory


def list_versions() -> list[str]:

    return sorted(_REGISTRY)


def get_recommender(
    version: str = DEFAULT_V3_VERSION,
    *,
    weights: ComponentWeights | None = None,
    max_distance_km: float | None = None,
) -> Recommender:

    if version not in _REGISTRY:
        raise KeyError(f"Unknown algorithm version: {version!r}. Known: {list_versions()}")
    kwargs: dict[str, object] = {}
    if weights is not None:
        kwargs["weights"] = weights
    if max_distance_km is not None:
        kwargs["max_distance_km"] = max_distance_km
    return _REGISTRY[version](**kwargs)



def _v3_factory(**kwargs: object) -> Recommender:
    kwargs.setdefault("weights", DEFAULT_V3_WEIGHTS)
    kwargs.setdefault(
        "scorers",
        {
            SHARED_INTERESTS: score_shared_interests_symmetric_mean,
            CHILDREN_AGE_COMPATIBILITY: score_children_age_compatibility_asymmetric,
        },
    )
    return WeightedHeuristicRecommender(version="v3", **kwargs)  # type: ignore[arg-type]



register("v3", _v3_factory)
