from __future__ import annotations

import math

from app.recommendation.interfaces import CandidateContext, UserContext

DEFAULT_MAX_DISTANCE_KM = 25.0

NEUTRAL_SCORE = 0.5

_MEETUP_FREQ_MAX_ORDINAL = 3  # rarely=0 .. often=3


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lng / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(a))


def score_geographic_proximity(
    user: UserContext, candidate: CandidateContext, max_distance_km: float = DEFAULT_MAX_DISTANCE_KM
) -> float:

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
   
    user_has_children = bool(user.child_age_group_ordinals)
    candidate_has_children = bool(candidate.child_age_group_ordinals)
    if not user_has_children and not candidate_has_children:
        return 1.0
    if user_has_children != candidate_has_children:
        return 0.0
    return score_children_age_compatibility(user, candidate)


def score_shared_interests(user: UserContext, candidate: CandidateContext) -> float:
  
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
   
    a, b = user.interest_slugs, candidate.interest_slugs
    if not a or not b:
        return 0.0
    shared = len(a & b)
    return 0.5 * (shared / len(a) + shared / len(b))


def score_meetup_frequency(user: UserContext, candidate: CandidateContext) -> float:
   
    gap = abs(user.meetup_frequency_ordinal - candidate.meetup_frequency_ordinal)
    return _clamp01(1.0 - gap / _MEETUP_FREQ_MAX_ORDINAL)


def score_cultural_preference(user: UserContext, candidate: CandidateContext) -> float:
  
    a, b = user.cultural_pref, candidate.cultural_pref
    if a == "mixed" or b == "mixed":
        return 1.0
    if a == b:
        return 1.0
    # e.g. one 'brazilian_only' vs other 'prefers_brazilian' — compatible enough.
    if {a, b} <= {"prefers_brazilian", "brazilian_only"}:
        return 0.7
    return 0.4



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
