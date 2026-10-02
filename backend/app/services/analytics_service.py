"""Admin analytics: aggregate, privacy-preserving community & platform metrics.

All queries aggregate at the DATABASE level (COUNT / GROUP BY / conditional
aggregation) — no loading rows into Python to compute stats, no N+1. Every metric
is aggregate-only and exposes NO personally identifiable information: no
passwords, tokens, message content, addresses, exact coordinates, or full postal
codes. Location is exposed only at city / FSA granularity, and small geographic
groups are bucketed (see ``MIN_GROUP_SIZE``) to reduce re-identification risk.

Metric definitions, formulas, and known BACKEND GAPS are documented in
docs/16-admin-analytics.md.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import (
    Child,
    ConnectionRequest,
    FsaRegion,
    Interest,
    Meetup,
    MeetupAttendee,
    Message,
    Profile,
    ProfileInterest,
    User,
)
from app.models.enums import (
    AgeGroup,
    ConnectionStatus,
    MeetupFrequency,
    RsvpStatus,
    UserRole,
)

# Minimum users a geographic group must have to be shown on its own; smaller
# groups are folded into an "Other" bucket so a subgroup can't identify a person.
MIN_GROUP_SIZE = 3
_OTHER_GROUP_LABEL = "Other (fewer than 3 users each)"

# Human-readable age ranges for the child age-group enum (docs/16).
_AGE_GROUP_LABELS: dict[AgeGroup, str] = {
    AgeGroup.INFANT: "Infant (0-1)",
    AgeGroup.TODDLER: "Toddler (1-3)",
    AgeGroup.PRESCHOOL: "Preschool (3-5)",
    AgeGroup.CHILD: "Child (6-9)",
    AgeGroup.PRETEEN: "Preteen (10-12)",
    AgeGroup.TEEN: "Teen (13-17)",
}


def _pct(part: int, whole: int) -> float:
    """Percentage of ``part`` within ``whole``, rounded to 1dp (0.0 when empty)."""
    return round(part / whole * 100, 1) if whole else 0.0


def _live_users_filter():
    """Predicate for "real" platform members: active, not soft-deleted, non-admin.

    Admin/test accounts are excluded so community analytics reflect actual users.
    """
    return and_(
        User.is_active.is_(True),
        User.deleted_at.is_(None),
        User.role != UserRole.ADMIN,
    )


def _live_user_count(db: Session) -> int:
    return db.execute(
        select(func.count()).select_from(User).where(_live_users_filter())
    ).scalar_one()


# --- 1. Overview -----------------------------------------------------------

# Active-user window: a user is "active" if they made an authenticated request in
# the last N days (measured via User.last_active_at, stamped by the auth layer).
ACTIVE_WINDOW_DAYS = 30


def overview(db: Session) -> dict[str, Any]:
    """High-level platform KPIs.

    ``active_users`` = live users whose ``last_active_at`` is within the last
    ``ACTIVE_WINDOW_DAYS`` days. ``last_active_at`` is stamped (throttled) by the
    auth dependency on authenticated requests, so it reflects real activity — not
    ``updated_at`` (which changes on any row mutation). It is NULL until a user's
    first authenticated request after the field shipped, so early counts start low
    and grow (historical activity can't be backfilled).
    """
    total_users = _live_user_count(db)
    total_connections = db.execute(
        select(func.count())
        .select_from(ConnectionRequest)
        .where(ConnectionRequest.status == ConnectionStatus.ACCEPTED)
    ).scalar_one()
    total_meetups = db.execute(select(func.count()).select_from(Meetup)).scalar_one()

    cutoff = datetime.now(UTC) - timedelta(days=ACTIVE_WINDOW_DAYS)
    active_users = db.execute(
        select(func.count())
        .select_from(User)
        .where(_live_users_filter(), User.last_active_at >= cutoff)
    ).scalar_one()

    return {
        "total_users": int(total_users),
        "active_users": int(active_users),
        "active_users_note": (
            f"Users with an authenticated request in the last {ACTIVE_WINDOW_DAYS} "
            "days (via last_active_at). Starts low and grows after deploy — "
            "historical activity is not backfilled."
        ),
        "total_connections": int(total_connections),
        "total_meetups": int(total_meetups),
    }


# --- 2. Family profile -----------------------------------------------------

def family_profile(db: Session) -> dict[str, Any]:
    """Users with vs. without children (derived from the children relationship).

    A user "has children" iff their profile has >= 1 child row. Counted over live
    users who have completed a profile (a profile row exists).
    """
    total_profiles = db.execute(
        select(func.count())
        .select_from(Profile)
        .join(User, User.id == Profile.user_id)
        .where(_live_users_filter())
    ).scalar_one()

    with_children = db.execute(
        select(func.count())
        .select_from(Profile)
        .join(User, User.id == Profile.user_id)
        .where(_live_users_filter(), Profile.children.any())
    ).scalar_one()

    without_children = int(total_profiles) - int(with_children)
    return {
        "total_users": int(total_profiles),
        "with_children": {
            "count": int(with_children),
            "percentage": _pct(int(with_children), int(total_profiles)),
        },
        "without_children": {
            "count": without_children,
            "percentage": _pct(without_children, int(total_profiles)),
        },
    }


# --- 3. Children age groups ------------------------------------------------

def children_age_groups(db: Session) -> list[dict[str, Any]]:
    """Distribution of children by age group.

    INTERPRETATION: this counts CHILDREN per age group (one row per child in the
    ``children`` table), NOT users. A user with two children in different groups
    contributes to two groups. This matches the model (children are individual
    rows with an age_group) and is documented in docs/16. All six enum buckets are
    returned (0 when none) so the chart axis is stable.
    """
    rows = dict(
        db.execute(
            select(Child.age_group, func.count())
            .join(Profile, Profile.id == Child.profile_id)
            .join(User, User.id == Profile.user_id)
            .where(_live_users_filter())
            .group_by(Child.age_group)
        ).all()
    )
    return [
        {
            "age_group": ag.value,
            "label": _AGE_GROUP_LABELS[ag],
            "count": int(rows.get(ag, 0)),
        }
        for ag in AgeGroup
    ]


# --- 4. Geographic distribution --------------------------------------------

def _apply_min_group_threshold(
    counts: list[tuple[str, int]], key_name: str
) -> list[dict[str, Any]]:
    """Sort desc and fold groups below MIN_GROUP_SIZE into one "Other" bucket.

    Keeps totals reconcilable (small groups are aggregated, not dropped) while
    ensuring no exposed subgroup identifies a person.
    """
    shown = [(k, c) for k, c in counts if k and c >= MIN_GROUP_SIZE]
    small_total = sum(c for k, c in counts if k and c < MIN_GROUP_SIZE)
    shown.sort(key=lambda kc: kc[1], reverse=True)
    out = [{key_name: k, "users": int(c)} for k, c in shown]
    if small_total:
        out.append({key_name: _OTHER_GROUP_LABEL, "users": int(small_total)})
    return out


def geographic_distribution(db: Session) -> list[dict[str, Any]]:
    """Users per city, most populous first. Small groups bucketed (privacy)."""
    rows = db.execute(
        select(Profile.city, func.count())
        .join(User, User.id == Profile.user_id)
        .where(_live_users_filter(), Profile.city.is_not(None))
        .group_by(Profile.city)
    ).all()
    return _apply_min_group_threshold([(c, n) for c, n in rows], "city")


def geographic_map(db: Session) -> list[dict[str, Any]]:
    """Per-FSA user counts at the FSA's SHARED centroid (privacy-safe).

    Uses ``fsa_regions`` centroids — NEVER a user's ``Profile.centroid_lat/lng``.
    FSAs with fewer than MIN_GROUP_SIZE users are omitted from the map (a single
    dot at a small FSA centroid could hint at a person); the count still appears
    in the "Other" bucket of the city distribution. FSAs without a centroid row
    are skipped (documented; not invented).
    """
    rows = db.execute(
        select(
            Profile.fsa,
            FsaRegion.region_name,
            FsaRegion.centroid_lat,
            FsaRegion.centroid_lng,
            func.count(),
        )
        .join(User, User.id == Profile.user_id)
        .join(FsaRegion, FsaRegion.fsa == Profile.fsa)
        .where(_live_users_filter(), Profile.fsa.is_not(None))
        .group_by(
            Profile.fsa,
            FsaRegion.region_name,
            FsaRegion.centroid_lat,
            FsaRegion.centroid_lng,
        )
        .having(func.count() >= MIN_GROUP_SIZE)
        .order_by(func.count().desc())
    ).all()
    return [
        {
            "fsa": fsa,
            "area": region_name or fsa,
            "user_count": int(count),
            "latitude": float(lat),
            "longitude": float(lng),
        }
        for fsa, region_name, lat, lng, count in rows
    ]


# --- 5. Interests ----------------------------------------------------------

def popular_interests(db: Session, limit: int | None = None) -> list[dict[str, Any]]:
    """Interests by number of users who selected them, most popular first."""
    stmt = (
        select(Interest.slug, Interest.label, func.count(ProfileInterest.profile_id))
        .join(ProfileInterest, ProfileInterest.interest_id == Interest.id)
        .join(Profile, Profile.id == ProfileInterest.profile_id)
        .join(User, User.id == Profile.user_id)
        .where(_live_users_filter())
        .group_by(Interest.slug, Interest.label)
        .order_by(func.count(ProfileInterest.profile_id).desc(), Interest.label)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return [
        {"slug": slug, "interest": label, "users": int(count)}
        for slug, label, count in db.execute(stmt).all()
    ]


# Display labels for the interest ``category`` slugs stored in the taxonomy.
_INTEREST_CATEGORY_LABELS: dict[str, str] = {
    "creative": "Creative",
    "outdoors": "Outdoors",
    "culture": "Culture",
    "family": "Family",
    "social": "Social",
    "community": "Community",
    "sports": "Sports",
    "wellness": "Wellness",
    "other": "Other",
}


def interest_groups(db: Session) -> list[dict[str, Any]]:
    """Interests aggregated into their taxonomy CATEGORY, share summing to 100%.

    Grouping uses the ``Interest.category`` column already stored in the taxonomy
    (creative / outdoors / culture / family / social / community / sports /
    wellness / other) — no categories are invented for the dashboard.

    Counting & denominator (documented so the chart is honest):
      * ``users`` = distinct live users who selected AT LEAST ONE interest in the
        category (``COUNT(DISTINCT profile_id)``). A user counts once per category
        they touch, so a user with interests in two categories is in both.
      * ``percentage`` = category ``users`` / SUM of ``users`` across all
        categories * 100. Because a multi-category user is counted in each
        category, the denominator is the total number of category-memberships,
        NOT the number of distinct users — which is precisely why the percentages
        **sum to 100%** (each bar is that category's *share of interest*). This
        avoids the "sums to >100%" problem of dividing by distinct users.

    Ordered by ``users`` descending. Categories with zero users are omitted.
    """
    rows = db.execute(
        select(
            Interest.category,
            func.count(func.distinct(ProfileInterest.profile_id)),
        )
        .join(ProfileInterest, ProfileInterest.interest_id == Interest.id)
        .join(Profile, Profile.id == ProfileInterest.profile_id)
        .join(User, User.id == Profile.user_id)
        .where(_live_users_filter(), Interest.category.is_not(None))
        .group_by(Interest.category)
    ).all()

    total_memberships = sum(int(c) for _, c in rows)
    out = [
        {
            "group": category,
            "label": _INTEREST_CATEGORY_LABELS.get(
                category, category.replace("_", " ").title()
            ),
            "users": int(count),
            "percentage": _pct(int(count), total_memberships),
        }
        for category, count in rows
    ]
    out.sort(key=lambda g: g["users"], reverse=True)
    return out


# --- 6. Meetup frequency ---------------------------------------------------

def meetup_frequency(db: Session) -> list[dict[str, Any]]:
    """Distribution of the preferred meetup frequency across live users.

    All enum buckets returned (0 when none). Percentages are of the profiled
    population.
    """
    rows = dict(
        db.execute(
            select(Profile.meetup_frequency_pref, func.count())
            .join(User, User.id == Profile.user_id)
            .where(_live_users_filter())
            .group_by(Profile.meetup_frequency_pref)
        ).all()
    )
    total = sum(int(v) for v in rows.values())
    return [
        {
            "frequency": freq.value,
            "count": int(rows.get(freq, 0)),
            "percentage": _pct(int(rows.get(freq, 0)), total),
        }
        for freq in MeetupFrequency
    ]


# --- 7. Engagement ---------------------------------------------------------

def engagement(db: Session) -> dict[str, Any]:
    """Aggregate platform-activity counters (all DB-level).

    - connection_requests: all ConnectionRequest rows ever created.
    - accepted_connections / declined_connection_requests: by status.
    - messages_sent: messages excluding soft-deleted tombstones.
    - meetups_created: all Meetup rows.
    - meetup_participations: MeetupAttendee rows with status GOING.
    """
    status_counts = dict(
        db.execute(
            select(ConnectionRequest.status, func.count()).group_by(
                ConnectionRequest.status
            )
        ).all()
    )
    total_requests = sum(int(v) for v in status_counts.values())

    messages_sent = db.execute(
        select(func.count()).select_from(Message).where(Message.deleted_at.is_(None))
    ).scalar_one()
    meetups_created = db.execute(select(func.count()).select_from(Meetup)).scalar_one()
    participations = db.execute(
        select(func.count())
        .select_from(MeetupAttendee)
        .where(MeetupAttendee.status == RsvpStatus.GOING)
    ).scalar_one()

    return {
        "connection_requests": int(total_requests),
        "accepted_connections": int(status_counts.get(ConnectionStatus.ACCEPTED, 0)),
        "declined_connection_requests": int(
            status_counts.get(ConnectionStatus.DECLINED, 0)
        ),
        "messages_sent": int(messages_sent),
        "meetups_created": int(meetups_created),
        "meetup_participations": int(participations),
    }


# --- 8. Connection acceptance rate -----------------------------------------

def connection_acceptance_rate(db: Session) -> dict[str, Any]:
    """Acceptance rate over RESOLVED requests only.

    acceptance_rate = accepted / (accepted + declined)

    Pending and cancelled requests are EXCLUDED from the denominator: pending
    ones have no decision yet, and cancelled ones were withdrawn by the sender
    (not a recipient decision). Reported alongside the raw counts so the
    denominator is transparent (docs/16). This is an engagement metric — it is
    NOT a claim that the recommendation algorithm is effective.
    """
    status_counts = dict(
        db.execute(
            select(ConnectionRequest.status, func.count()).group_by(
                ConnectionRequest.status
            )
        ).all()
    )
    accepted = int(status_counts.get(ConnectionStatus.ACCEPTED, 0))
    declined = int(status_counts.get(ConnectionStatus.DECLINED, 0))
    pending = int(status_counts.get(ConnectionStatus.PENDING, 0))
    cancelled = int(status_counts.get(ConnectionStatus.CANCELLED, 0))
    resolved = accepted + declined

    return {
        "requests_sent": accepted + declined + pending + cancelled,
        "accepted": accepted,
        "declined": declined,
        "pending": pending,
        "cancelled": cancelled,
        "resolved": resolved,
        "acceptance_rate": round(accepted / resolved * 100, 2) if resolved else None,
        "acceptance_rate_denominator": "resolved requests (accepted + declined)",
    }


# --- Combined dashboard ----------------------------------------------------

def dashboard(db: Session) -> dict[str, Any]:
    """Everything the Admin Dashboard needs in one response (fewer round-trips)."""
    return {
        "overview": overview(db),
        "family_profile": family_profile(db),
        "children_age_groups": children_age_groups(db),
        "geographic_distribution": geographic_distribution(db),
        "geographic_map": geographic_map(db),
        "popular_interests": popular_interests(db),
        "meetup_frequency": meetup_frequency(db),
        "interest_groups": interest_groups(db),
        "engagement": engagement(db),
        "connection_acceptance_rate": connection_acceptance_rate(db),
        "privacy_notice": (
            "Aggregated data — personal information and exact user locations are "
            "not displayed."
        ),
    }
