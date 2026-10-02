"""Data structures and the ``Recommender`` protocol for the engine.

These are plain, dependency-free dataclasses so the engine can be unit-tested
without a database or web framework, and so a future ML recommender can satisfy
the same contract (docs/05 §7).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# The five components of the initial algorithm. Kept as constants so scorers,
# weights, and explanations all reference the same identifiers.
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
    """The privacy-safe features needed to score a user.

    Note: no exact address or postal code appears here — only FSA centroid
    coordinates and age *groups*.
    """

    user_id: str
    fsa: str | None
    centroid_lat: float | None
    centroid_lng: float | None
    interest_slugs: frozenset[str] = frozenset()
    child_age_group_ordinals: tuple[int, ...] = ()
    meetup_frequency_ordinal: int = 1
    cultural_pref: str = "mixed"


# A candidate is scored against the requesting user using the same feature shape.
CandidateContext = UserContext


@dataclass
class ComponentBreakdown:
    """A single component's raw score and its weighted contribution."""

    key: str
    score: float  # in [0, 1]
    weight: float
    weighted: float  # score * weight


@dataclass
class RecommendationResult:
    """The full result for one (user, candidate) pair."""

    candidate_user_id: str
    algorithm_version: str
    total_score: float
    components: list[ComponentBreakdown] = field(default_factory=list)
    explanation: str = ""

    @property
    def component_scores(self) -> dict[str, float]:
        """Return ``{component_key: raw_score}`` for persistence/serialization."""
        return {c.key: round(c.score, 4) for c in self.components}


@runtime_checkable
class Recommender(Protocol):
    """Contract every recommender (heuristic or ML) must satisfy."""

    version: str

    def score(self, user: UserContext, candidate: CandidateContext) -> RecommendationResult:
        """Score a single candidate for a user."""
        ...

    def rank(
        self, user: UserContext, candidates: list[CandidateContext], limit: int | None = None
    ) -> list[RecommendationResult]:
        """Score and rank candidates in descending total score."""
        ...
