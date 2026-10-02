"""Per-component scorers for the initial heuristic algorithm.

Each scorer returns a float in ``[0, 1]``. Behaviour follows docs/05 §3. All
scorers operate on privacy-safe features only (FSA centroids, age-group ordinals,
interest slugs) — never exact addresses or child names.
"""

from __future__ import annotations

import math

from app.recommendation.interfaces import CandidateContext, UserContext

# Default maximum matching distance (km). Configurable via settings at call time.
DEFAULT_MAX_DISTANCE_KM = 25.0

# Neutral score used when a component cannot be meaningfully compared
# (e.g., one side has no children — the platform is not children-gated, F11).
NEUTRAL_SCORE = 0.5

_MEETUP_FREQ_MAX_ORDINAL = 3  # rarely=0 .. often=3


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometres between two lat/lng points."""
    radius_km = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lng / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(a))


def score_geographic_proximity(
    user: UserContext, candidate: CandidateContext, max_distance_km: float = DEFAULT_MAX_DISTANCE_KM
) -> float:
    """Distance-decayed proximity using FSA centroids (docs/05 §3.1)."""
    # Same FSA is a strong signal even if centroids are missing.
    if user.fsa and candidate.fsa and user.fsa == candidate.fsa:
        return 1.0
    if None in (
        user.centroid_lat,
        user.centroid_lng,
        candidate.centroid_lat,
        candidate.centroid_lng,
    ):
        return 0.0
    distance = haversine_km(
        user.centroid_lat,  # type: ignore[arg-type]
        user.centroid_lng,  # type: ignore[arg-type]
        candidate.centroid_lat,  # type: ignore[arg-type]
        candidate.centroid_lng,  # type: ignore[arg-type]
    )
    if max_distance_km <= 0:
        return 0.0
    return _clamp01(1.0 - distance / max_distance_km)


def score_children_age_compatibility(user: UserContext, candidate: CandidateContext) -> float:
    """Best age-group overlap; adjacent groups get partial credit (docs/05 §3.2).

    F11: if either side has no children, this component is *neutralized* (returns
    a neutral score) rather than penalized.
    """
    if not user.child_age_group_ordinals or not candidate.child_age_group_ordinals:
        return NEUTRAL_SCORE
    best = 0.0
    for a in user.child_age_group_ordinals:
        for b in candidate.child_age_group_ordinals:
            gap = abs(a - b)
            if gap == 0:
                pair = 1.0
            elif gap == 1:
                pair = 0.5
            else:
                pair = 0.0
            best = max(best, pair)
    return best


def score_children_age_compatibility_asymmetric(
    user: UserContext, candidate: CandidateContext
) -> float:
    """Children-age compatibility for v3, keyed on whether each side has children.

    - **both childless** -> 1.0: two users with no children are a perfect match on
      this dimension ("no children" is itself the shared trait).
    - **exactly one has children** -> 0.0: there are no children to be compatible
      with, so it must not read as a partial/neutral match.
    - **both have children** -> best age-group overlap (same as the base scorer).
    """
    user_has_children = bool(user.child_age_group_ordinals)
    candidate_has_children = bool(candidate.child_age_group_ordinals)
    if not user_has_children and not candidate_has_children:
        return 1.0
    if user_has_children != candidate_has_children:
        return 0.0
    return score_children_age_compatibility(user, candidate)


def score_shared_interests(user: UserContext, candidate: CandidateContext) -> float:
    """Jaccard similarity of interest sets (docs/05 §3.3). Used by v1/v2."""
    a, b = user.interest_slugs, candidate.interest_slugs
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def score_shared_interests_symmetric_mean(
    user: UserContext, candidate: CandidateContext
) -> float:
    """Symmetric mean of per-side overlap: ½·(|A∩B|/|A| + |A∩B|/|B|). Used by v3.

    Reads intuitively for differing interest counts and avoids the overlap
    coefficient's misleading 1.0 on subsets:
    - both list 3, share 2  → ½·(2/3 + 2/3) ≈ 0.67
    - A lists 2, B lists 3, A⊂B → ½·(2/2 + 2/3) ≈ 0.83
    - identical sets        → 1.0
    - either side empty     → 0.0
    """
    a, b = user.interest_slugs, candidate.interest_slugs
    if not a or not b:
        return 0.0
    shared = len(a & b)
    return 0.5 * (shared / len(a) + shared / len(b))


def score_meetup_frequency(user: UserContext, candidate: CandidateContext) -> float:
    """Closeness of meetup cadence preferences (docs/05 §3.4)."""
    gap = abs(user.meetup_frequency_ordinal - candidate.meetup_frequency_ordinal)
    return _clamp01(1.0 - gap / _MEETUP_FREQ_MAX_ORDINAL)


def score_cultural_preference(user: UserContext, candidate: CandidateContext) -> float:
    """Soft cultural-preference alignment (docs/05 §3.5, F7).

    Never returns 0 and is never used as a hard filter. ``mixed`` is compatible
    with everyone. Two strict-but-mismatched preferences get a reduced score.
    """
    a, b = user.cultural_pref, candidate.cultural_pref
    if a == "mixed" or b == "mixed":
        return 1.0
    if a == b:
        return 1.0
    # e.g. one 'brazilian_only' vs other 'prefers_brazilian' — compatible enough.
    if {a, b} <= {"prefers_brazilian", "brazilian_only"}:
        return 0.7
    return 0.4


# Registry of scorers keyed by component id, consumed by the weighted recommender.
from app.recommendation.interfaces import (  # noqa: E402  (kept local to avoid cycle at top)
    CHILDREN_AGE_COMPATIBILITY,
    CULTURAL_PREFERENCE,
    GEOGRAPHIC_PROXIMITY,
    MEETUP_FREQUENCY,
    SHARED_INTERESTS,
)

COMPONENT_SCORERS = {
    GEOGRAPHIC_PROXIMITY: score_geographic_proximity,
    CHILDREN_AGE_COMPATIBILITY: score_children_age_compatibility,
    SHARED_INTERESTS: score_shared_interests,
    MEETUP_FREQUENCY: score_meetup_frequency,
    CULTURAL_PREFERENCE: score_cultural_preference,
}
