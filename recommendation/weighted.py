from __future__ import annotations

from app.recommendation.components import COMPONENT_SCORERS, DEFAULT_MAX_DISTANCE_KM
from app.recommendation.explanation import build_explanation
from app.recommendation.interfaces import (
    GEOGRAPHIC_PROXIMITY,
    CandidateContext,
    ComponentBreakdown,
    RecommendationResult,
    UserContext,
)
from app.recommendation.weights import DEFAULT_WEIGHTS, ComponentWeights


class WeightedHeuristicRecommender:
    """Weighted linear combination of component scores."""

    def __init__(
        self,
        weights: ComponentWeights | None = None,
        max_distance_km: float = DEFAULT_MAX_DISTANCE_KM,
        scorers: dict | None = None,
    ) -> None:
        self.version = version
        self.weights = weights or DEFAULT_WEIGHTS
        self.max_distance_km = max_distance_km
        self.scorers = {**COMPONENT_SCORERS, **(scorers or {})}

    def score(self, user: UserContext, candidate: CandidateContext) -> RecommendationResult:
        components: list[ComponentBreakdown] = []
        total = 0.0
        for key, scorer in self.scorers.items():
            if key == GEOGRAPHIC_PROXIMITY:
                raw = scorer(user, candidate, self.max_distance_km)  # type: ignore[call-arg]
            else:
                raw = scorer(user, candidate)
            weight = self.weights[key]
            weighted = raw * weight
            total += weighted
            components.append(
                ComponentBreakdown(key=key, score=raw, weight=weight, weighted=weighted)
            )

        component_scores = {c.key: c.score for c in components}
        explanation = build_explanation(user, candidate, component_scores)
        return RecommendationResult(
            candidate_user_id=candidate.user_id,
            algorithm_version=self.version,
            total_score=round(total, 4),
            components=components,
            explanation=explanation,
        )

    def rank(
        self,
        user: UserContext,
        candidates: list[CandidateContext],
        limit: int | None = None,
    ) -> list[RecommendationResult]:
        results = [self.score(user, c) for c in candidates if c.user_id != user.user_id]
        results.sort(key=lambda r: r.total_score, reverse=True)
        return results[:limit] if limit is not None else results
