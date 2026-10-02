"""Configurable component weights with validation.

The initial ``v1`` weights come from the research desired-features findings
(F5, F7, F9). They are an expert-informed heuristic and are NOT statistically
validated (docs/05 §1). Weights are configurable and validated: they must be
non-negative and sum to 1.0.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.recommendation.interfaces import (
    CHILDREN_AGE_COMPATIBILITY,
    COMPONENT_KEYS,
    CULTURAL_PREFERENCE,
    GEOGRAPHIC_PROXIMITY,
    MEETUP_FREQUENCY,
    SHARED_INTERESTS,
)

_SUM_TOLERANCE = 1e-6


@dataclass(frozen=True)
class ComponentWeights:
    """A validated set of component weights that sums to 1.0."""

    values: dict[str, float]

    def __post_init__(self) -> None:
        missing = set(COMPONENT_KEYS) - set(self.values)
        if missing:
            raise ValueError(f"Missing weights for components: {sorted(missing)}")
        unknown = set(self.values) - set(COMPONENT_KEYS)
        if unknown:
            raise ValueError(f"Unknown component keys in weights: {sorted(unknown)}")
        if any(w < 0 for w in self.values.values()):
            raise ValueError("Weights must be non-negative")
        total = sum(self.values.values())
        if abs(total - 1.0) > _SUM_TOLERANCE:
            raise ValueError(f"Weights must sum to 1.0 (got {total})")

    def __getitem__(self, key: str) -> float:
        return self.values[key]

    @classmethod
    def from_mapping(cls, mapping: dict[str, float]) -> ComponentWeights:
        """Build and validate weights from a plain mapping (e.g., DB JSONB)."""
        return cls(values=dict(mapping))


# Initial algorithm weights (docs/05 §2).
DEFAULT_V1_WEIGHTS = ComponentWeights(
    values={
        GEOGRAPHIC_PROXIMITY: 0.35,
        CHILDREN_AGE_COMPATIBILITY: 0.30,
        SHARED_INTERESTS: 0.20,
        MEETUP_FREQUENCY: 0.10,
        CULTURAL_PREFERENCE: 0.05,
    }
)

# v2 weights: emphasize proximity and drop cultural preference from scoring.
# geo 0.40 / child-age 0.30 / interests 0.20 / meetup 0.10 / cultural 0.00.
# Cultural preference stays a defined component (so v1 remains comparable) but
# contributes nothing to the v2 ranking. Still an expert heuristic, NOT validated.
DEFAULT_V2_WEIGHTS = ComponentWeights(
    values={
        GEOGRAPHIC_PROXIMITY: 0.40,
        CHILDREN_AGE_COMPATIBILITY: 0.30,
        SHARED_INTERESTS: 0.20,
        MEETUP_FREQUENCY: 0.10,
        CULTURAL_PREFERENCE: 0.00,
    }
)

# v3 weights: geo 0.40 / interests 0.30 / children-age 0.20 / meetup 0.10 /
# cultural 0.00. Interests and children-age swap relative to v2 (interests now
# outweigh children-age). Paired with the asymmetric children-age scorer:
# both-childless pairs score 1.0 on children-age (a "virtually 100%" match on
# that dimension), and a mixed pair (only one has children) scores 0.0.
DEFAULT_V3_WEIGHTS = ComponentWeights(
    values={
        GEOGRAPHIC_PROXIMITY: 0.40,
        SHARED_INTERESTS: 0.30,
        CHILDREN_AGE_COMPATIBILITY: 0.20,
        MEETUP_FREQUENCY: 0.10,
        CULTURAL_PREFERENCE: 0.00,
    }
)
