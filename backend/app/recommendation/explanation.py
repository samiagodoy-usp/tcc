"""Deterministic, human-readable explanation builder.

Explanations are generated from the component scores so they always match the
stored scores (docs/05 §4). Every recommendation must carry an explanation.
"""

from __future__ import annotations

from app.recommendation.interfaces import (
    CHILDREN_AGE_COMPATIBILITY,
    CULTURAL_PREFERENCE,
    GEOGRAPHIC_PROXIMITY,
    MEETUP_FREQUENCY,
    SHARED_INTERESTS,
    CandidateContext,
    UserContext,
)

# Threshold above which a component is considered "notable" enough to mention.
_STRONG = 0.6


def build_explanation(
    user: UserContext,
    candidate: CandidateContext,
    component_scores: dict[str, float],
) -> str:
    """Return a short natural-language explanation for a recommendation."""
    reasons: list[str] = []

    geo = component_scores.get(GEOGRAPHIC_PROXIMITY, 0.0)
    if geo >= _STRONG:
        if user.fsa and candidate.fsa and user.fsa == candidate.fsa:
            reasons.append(f"you're in the same area ({candidate.fsa})")
        else:
            reasons.append("you're in nearby areas")

    shared = user.interest_slugs & candidate.interest_slugs
    interests = component_scores.get(SHARED_INTERESTS, 0.0)
    if interests > 0 and shared:
        count = len(shared)
        reasons.append(f"you share {count} interest{'s' if count != 1 else ''}")

    age = component_scores.get(CHILDREN_AGE_COMPATIBILITY, 0.0)
    if user.child_age_group_ordinals and candidate.child_age_group_ordinals and age >= _STRONG:
        reasons.append("your children are in compatible age groups")

    freq = component_scores.get(MEETUP_FREQUENCY, 0.0)
    if freq >= _STRONG:
        reasons.append("you prefer a similar meetup pace")

    cultural = component_scores.get(CULTURAL_PREFERENCE, 0.0)
    if cultural >= 1.0 and (
        user.cultural_pref != "mixed" or candidate.cultural_pref != "mixed"
    ):
        reasons.append("your community preferences align")

    if not reasons:
        return "This person is a potential match based on your overall profile."

    if len(reasons) == 1:
        body = reasons[0]
    else:
        body = ", ".join(reasons[:-1]) + f", and {reasons[-1]}"
    return f"You might connect because {body}."
