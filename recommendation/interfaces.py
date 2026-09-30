from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


GEOGRAPHIC_PROXIMITY = "geographic_proximity"
CHILDREN_AGE_COMPATIBILITY = "children_age_compatibility"
SHARED_INTERESTS = "shared_interests"
MEETUP_FREQUENCY = "meetup_frequency"
CULTURAL_PREFERENCE = "cultural_preference"

COMPONENT_KEYS: tuple[str, ...] = (
    GEOGRAPHIC_PROXIMITY,
    CHILDREN_AGE_COMPATIBILITY,
    SHARED_INTERESTS,
    MEETUP_FREQUENCY,
    CULTURAL_PREFERENCE,
)


@dataclass(frozen=True)
class UserContext:
 
    user_id: str
    fsa: str | None
    centroid_lat: float | None
    centroid_lng: float | None
    interest_slugs: frozenset[str] = frozenset()
    child_age_group_ordinals: tuple[int, ...] = ()
    meetup_frequency_ordinal: int = 1
    cultural_pref: str = "mixed"


CandidateContext = UserContext


@dataclass
class ComponentBreakdown:
  

    key: str
    score: float  # in [0, 1]
    weight: float
    weighted: float  # score * weight


@dataclass
class RecommendationResult:


    candidate_user_id: str
    algorithm_version: str
    total_score: float
    components: list[ComponentBreakdown] = field(default_factory=list)
    explanation: str = ""

    @property
    def component_scores(self) -> dict[str, float]:

        return {c.key: round(c.score, 4) for c in self.components}


@runtime_checkable
class Recommender(Protocol):


    version: str

    def score(self, user: UserContext, candidate: CandidateContext) -> RecommendationResult:
        """Score a single candidate for a user."""
        ...

    def rank(
        self, user: UserContext, candidates: list[CandidateContext], limit: int | None = None
    ) -> list[RecommendationResult]:
        """Score and rank candidates in descending total score."""
        ...
