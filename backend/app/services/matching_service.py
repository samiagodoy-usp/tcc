"""Matching use case: build candidate contexts, score, persist, and explain.

This service is the *only* bridge between the API and the recommendation engine.
It resolves the algorithm version from the registry (so a future ML model can be
swapped in transparently), scores privacy-safe contexts, persists per-component
scores for future validation (docs/05 §9), and returns privacy-filtered results.

Blocked users are excluded from candidates (docs/06 §4).
"""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models import (
    AlgorithmVersion,
    Child,
    ConnectionRequest,
    Interest,
    Profile,
    ProfileInterest,
    Recommendation,
    User,
)
from app.models.enums import (
    AgeGroup,
    ConnectionStatus,
    HouseholdType,
    MeetupFrequency,
    UserRole,
)
from app.recommendation import get_recommender
from app.recommendation.registry import DEFAULT_VERSION
from app.recommendation.weights import ComponentWeights
from app.schemas.matching import MatchConnection, MatchResult
from app.services.blocking import blocked_user_ids as _blocked_user_ids
from app.services.blocking import is_blocked
from app.services.privacy import to_public_profile, to_user_context

logger = logging.getLogger(__name__)


# Statuses that are meaningful for the "what button do I show?" decision.
# declined/cancelled requests are treated as "no connection" so the viewer can
# ask again with a fresh "Connect" button (FR-CONN-*).
_ACTIVE_CONNECTION_STATUSES = (ConnectionStatus.PENDING, ConnectionStatus.ACCEPTED)


def _connection_map(
    db: Session, user_id: uuid.UUID
) -> dict[uuid.UUID, MatchConnection]:
    """Map ``other_user_id -> MatchConnection`` for the viewer's active connections.

    One query over ``connection_requests`` where the viewer is sender or recipient
    and the status is pending/accepted. ``direction`` is from the *viewer's*
    perspective: ``incoming`` means the other user sent the request to the viewer,
    ``outgoing`` means the viewer sent it. When both an incoming and outgoing
    request exist for the same pair, accepted wins over pending (a live
    connection), otherwise the most recent request is kept.
    """
    rows = (
        db.execute(
            select(ConnectionRequest).where(
                (ConnectionRequest.sender_id == user_id)
                | (ConnectionRequest.recipient_id == user_id),
                ConnectionRequest.status.in_(_ACTIVE_CONNECTION_STATUSES),
            )
        )
        .scalars()
        .all()
    )

    # Keep the highest-priority request per other user.
    best: dict[uuid.UUID, ConnectionRequest] = {}
    for req in rows:
        other_id = req.sender_id if req.recipient_id == user_id else req.recipient_id
        current = best.get(other_id)
        if current is None or _connection_priority(req) > _connection_priority(current):
            best[other_id] = req

    return {
        other_id: MatchConnection(
            connection_id=req.id,
            status=req.status,
            direction="incoming" if req.recipient_id == user_id else "outgoing",
        )
        for other_id, req in best.items()
    }


def _connection_priority(req: ConnectionRequest):
    """Rank a request: accepted beats pending; then most recently created wins."""
    return (req.status == ConnectionStatus.ACCEPTED, req.created_at)


def _validate_interest_slugs(db: Session, slugs: list[str]) -> None:
    """Raise 422 if any slug isn't a known interest (mirrors onboarding validation)."""
    known = {
        s
        for s in db.execute(
            select(Interest.slug).where(Interest.slug.in_(slugs))
        ).scalars()
    }
    unknown = [s for s in slugs if s not in known]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unknown interest(s): {sorted(unknown)}. "
                "Use slugs from GET /api/v1/interests."
            ),
        )


def _resolve_version(db: Session, version: str | None):
    """Return (version_string, recommender, AlgorithmVersion row).

    Uses the stored, possibly-overridden weights for the version if present.
    """
    version = version or DEFAULT_VERSION
    row = db.execute(
        select(AlgorithmVersion).where(AlgorithmVersion.version == version)
    ).scalar_one_or_none()

    weights = None
    if row is not None and row.weights:
        weights = ComponentWeights.from_mapping(row.weights)

    settings = get_settings()
    recommender = get_recommender(
        version, weights=weights, max_distance_km=settings.match_max_distance_km
    )
    return version, recommender, row


def get_matches(
    db: Session,
    user: User,
    *,
    limit: int = 20,
    version: str | None = None,
    cities: list[str] | None = None,
    household_type: HouseholdType | None = None,
    meetup_frequencies: list[MeetupFrequency] | None = None,
    interest_slugs: list[str] | None = None,
    child_age_groups: list[AgeGroup] | None = None,
    requires_children: bool = False,
    persist: bool = True,
) -> list[MatchResult]:
    """Rank candidate users for ``user`` and (optionally) persist the scores.

    ``cities`` (canonical service-area names) hard-filters candidates to those
    cities before scoring — the Discover screen's city filter, which may select
    several. It operates on the stored ``Profile.city`` value, so it works even
    for users who've hidden their city from the public payload. ``None`` or an
    empty list means no city filter.

    ``household_type`` hard-filters candidates by whether they have children:
    ``FAMILY`` keeps profiles with at least one child, ``INDIVIDUAL`` keeps those
    with none. Derived from the ``children`` relationship (no stored field);
    ``None`` means no household filter.

    ``meetup_frequencies`` hard-filters candidates to those whose stored
    ``meetup_frequency_pref`` is one of the given values — the Discover "Select
    frequency" filter, which may select several. This is distinct from the
    *soft* frequency scoring component; ``None`` or an empty list means no filter.

    ``interest_slugs`` hard-filters candidates to those who share **at least one**
    of the given interests (match-any) — the Discover "Select interests" filter.
    Unknown slugs raise 422 (consistent with onboarding). This is a hard filter,
    distinct from the *soft* shared-interests scoring; ``None``/empty = no filter.

    ``child_age_groups`` hard-filters candidates to those with a child in **at
    least one** of the given age groups (match-any) — the Discover "children's
    age" filter. Because it requires a matching child, it inherently excludes
    candidates with no children; ``None``/empty = no filter.

    ``requires_children`` hard-filters to candidates who have at least one child.
    Powers the "Similar kids' ages" view: that mode ranks by child-age
    compatibility, so childless candidates (whose age-compatibility score is a
    *neutral* 0.5 by F11) must not appear at all. Implied when ``child_age_groups``
    is set (that already requires a child), so this is for the case where the view
    doesn't restrict to specific age groups but still must exclude non-parents.
    """
    if interest_slugs:
        _validate_interest_slugs(db, interest_slugs)
    me = db.execute(
        select(Profile)
        .options(selectinload(Profile.children), selectinload(Profile.interests))
        .where(Profile.user_id == user.id)
    ).scalar_one_or_none()
    if me is None:
        return []

    hidden = _blocked_user_ids(db, user.id)
    hidden.add(user.id)

    candidate_query = (
        select(Profile)
        .join(User, User.id == Profile.user_id)
        .options(selectinload(Profile.children), selectinload(Profile.interests))
        .where(
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            User.onboarding_completed.is_(True),
            User.role != UserRole.ADMIN,  # admin/test accounts aren't matchable
            Profile.user_id.notin_(hidden),
        )
    )
    if cities:
        candidate_query = candidate_query.where(Profile.city.in_(cities))
    if household_type is HouseholdType.FAMILY:
        candidate_query = candidate_query.where(Profile.children.any())
    elif household_type is HouseholdType.INDIVIDUAL:
        candidate_query = candidate_query.where(~Profile.children.any())
    if meetup_frequencies:
        candidate_query = candidate_query.where(
            Profile.meetup_frequency_pref.in_(meetup_frequencies)
        )
    if interest_slugs:
        # Match-any: keep candidates sharing at least one selected interest.
        candidate_query = candidate_query.where(
            Profile.interests.any(
                ProfileInterest.interest.has(Interest.slug.in_(interest_slugs))
            )
        )
    if child_age_groups:
        # Match-any: keep candidates with a child in one of the selected age
        # groups. Excludes childless candidates by construction.
        candidate_query = candidate_query.where(
            Profile.children.any(Child.age_group.in_(child_age_groups))
        )
    elif requires_children:
        # "Similar kids' ages" view without a specific age-group filter: still
        # exclude candidates who have no children (they'd otherwise appear via the
        # neutral age-compatibility score).
        candidate_query = candidate_query.where(Profile.children.any())

    candidate_profiles = db.execute(candidate_query).scalars().all()

    version_str, recommender, version_row = _resolve_version(db, version)

    my_ctx = to_user_context(me)
    candidate_ctxs = [to_user_context(p) for p in candidate_profiles]
    ranked = recommender.rank(my_ctx, candidate_ctxs, limit=limit)

    profiles_by_id = {str(p.user_id): p for p in candidate_profiles}
    connections = _connection_map(db, user.id)
    results: list[MatchResult] = []
    for r in ranked:
        candidate_profile = profiles_by_id[r.candidate_user_id]
        connection = connections.get(candidate_profile.user_id)
        results.append(_to_match_result(candidate_profile, r, connection))
        if persist:
            _persist(db, user.id, r, version_row, version_str)
    if persist:
        db.commit()
    return results


def get_match_for_candidate(
    db: Session,
    user: User,
    candidate_id: uuid.UUID,
    *,
    version: str | None = None,
) -> MatchResult | None:
    """Score a single candidate for ``user`` without scanning the whole population.

    Returns ``None`` if the candidate is not an eligible match (missing, inactive,
    deleted, not onboarded, blocked in either direction, or the user themselves).
    """
    if candidate_id == user.id or is_blocked(db, user.id, candidate_id):
        return None

    me = db.execute(
        select(Profile)
        .options(selectinload(Profile.children), selectinload(Profile.interests))
        .where(Profile.user_id == user.id)
    ).scalar_one_or_none()
    if me is None:
        return None

    candidate_profile = db.execute(
        select(Profile)
        .join(User, User.id == Profile.user_id)
        .options(selectinload(Profile.children), selectinload(Profile.interests))
        .where(
            Profile.user_id == candidate_id,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            User.onboarding_completed.is_(True),
            User.role != UserRole.ADMIN,  # admin/test accounts aren't matchable
        )
    ).scalar_one_or_none()
    if candidate_profile is None:
        return None

    _, recommender, _ = _resolve_version(db, version)
    result = recommender.score(to_user_context(me), to_user_context(candidate_profile))
    connection = _connection_map(db, user.id).get(candidate_id)
    return _to_match_result(candidate_profile, result, connection)


def _to_match_result(
    candidate_profile: Profile,
    result,
    connection: MatchConnection | None = None,
) -> MatchResult:
    return MatchResult(
        candidate=to_public_profile(candidate_profile),
        algorithm_version=result.algorithm_version,
        total_score=result.total_score,
        component_scores=result.component_scores,
        explanation=result.explanation,
        connection=connection,
    )


def _persist(
    db: Session,
    for_user_id: uuid.UUID,
    result,
    version_row: AlgorithmVersion | None,
    version_str: str,
) -> None:
    if version_row is None:
        # No stored AlgorithmVersion row => cannot persist scores for validation.
        # Surface this instead of silently dropping the data (docs/05 §9).
        logger.warning(
            "Skipping recommendation persistence: no algorithm_versions row for "
            "version %r. Seed it (python -m app.db.seed) to capture validation data.",
            version_str,
        )
        return
    db.add(
        Recommendation(
            for_user_id=for_user_id,
            candidate_user_id=uuid.UUID(result.candidate_user_id),
            algorithm_version_id=version_row.id,
            total_score=result.total_score,
            component_scores=result.component_scores,
            explanation=result.explanation,
        )
    )
