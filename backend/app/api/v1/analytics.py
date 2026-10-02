"""Admin analytics dashboard endpoints (docs/16).

Aggregate, privacy-preserving community & platform metrics for the admin
dashboard (and the PertoApp MBA Data Science project). ALL endpoints require an
authenticated administrator (401 unauthenticated / 403 non-admin, via AdminUser).
No endpoint returns PII, passwords, tokens, message content, addresses, exact
user coordinates, or full postal codes — location is city / FSA-centroid only,
and small geographic groups are bucketed (see analytics_service.MIN_GROUP_SIZE).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import AdminUser, DbSession
from app.schemas.analytics import (
    AcceptanceRateOut,
    ChildrenAgeGroupOut,
    DashboardOut,
    EngagementOut,
    FamilyProfileOut,
    GeographicCityOut,
    GeographicMapPointOut,
    InterestGroupOut,
    InterestOut,
    MeetupFrequencyOut,
    OverviewOut,
)
from app.services import analytics_service

router = APIRouter(prefix="/admin/analytics", tags=["admin", "analytics"])


@router.get("/overview", response_model=OverviewOut)
def overview(admin: AdminUser, db: DbSession) -> OverviewOut:
    return OverviewOut(**analytics_service.overview(db))


@router.get("/family-profile", response_model=FamilyProfileOut)
def family_profile(admin: AdminUser, db: DbSession) -> FamilyProfileOut:
    return FamilyProfileOut(**analytics_service.family_profile(db))


@router.get("/children-age-groups", response_model=list[ChildrenAgeGroupOut])
def children_age_groups(admin: AdminUser, db: DbSession) -> list[ChildrenAgeGroupOut]:
    return [ChildrenAgeGroupOut(**r) for r in analytics_service.children_age_groups(db)]


@router.get("/geographic-distribution", response_model=list[GeographicCityOut])
def geographic_distribution(
    admin: AdminUser, db: DbSession
) -> list[GeographicCityOut]:
    return [
        GeographicCityOut(**r) for r in analytics_service.geographic_distribution(db)
    ]


@router.get("/geographic-map", response_model=list[GeographicMapPointOut])
def geographic_map(admin: AdminUser, db: DbSession) -> list[GeographicMapPointOut]:
    return [GeographicMapPointOut(**r) for r in analytics_service.geographic_map(db)]


@router.get("/interests", response_model=list[InterestOut])
def interests(admin: AdminUser, db: DbSession) -> list[InterestOut]:
    return [InterestOut(**r) for r in analytics_service.popular_interests(db)]


@router.get("/interest-groups", response_model=list[InterestGroupOut])
def interest_groups(admin: AdminUser, db: DbSession) -> list[InterestGroupOut]:
    """Interests aggregated into taxonomy categories; percentages sum to 100%."""
    return [InterestGroupOut(**r) for r in analytics_service.interest_groups(db)]


@router.get("/meetup-frequency", response_model=list[MeetupFrequencyOut])
def meetup_frequency(admin: AdminUser, db: DbSession) -> list[MeetupFrequencyOut]:
    return [MeetupFrequencyOut(**r) for r in analytics_service.meetup_frequency(db)]


@router.get("/engagement", response_model=EngagementOut)
def engagement(admin: AdminUser, db: DbSession) -> EngagementOut:
    return EngagementOut(**analytics_service.engagement(db))


@router.get("/connection-acceptance-rate", response_model=AcceptanceRateOut)
def connection_acceptance_rate(admin: AdminUser, db: DbSession) -> AcceptanceRateOut:
    return AcceptanceRateOut(**analytics_service.connection_acceptance_rate(db))


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(admin: AdminUser, db: DbSession) -> DashboardOut:
    """Everything the Admin Dashboard needs in one call (fewer HTTP requests)."""
    return DashboardOut(**analytics_service.dashboard(db))
