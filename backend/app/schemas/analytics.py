"""Response schemas for the admin analytics dashboard (docs/16).

Frontend-friendly, aggregate-only shapes. No PII, coordinates (other than
FSA-region centroids), or postal codes appear here.
"""

from __future__ import annotations

from pydantic import BaseModel


class OverviewOut(BaseModel):
    total_users: int
    # Live users active (authenticated request) within the last 30 days.
    active_users: int
    active_users_note: str
    total_connections: int
    total_meetups: int


class FamilyGroupOut(BaseModel):
    count: int
    percentage: float


class FamilyProfileOut(BaseModel):
    total_users: int
    with_children: FamilyGroupOut
    without_children: FamilyGroupOut


class ChildrenAgeGroupOut(BaseModel):
    age_group: str  # enum value, e.g. "toddler"
    label: str  # human range, e.g. "Toddler (1-3)"
    count: int  # number of CHILDREN in this age group (see docs/16)


class GeographicCityOut(BaseModel):
    city: str
    users: int


class GeographicMapPointOut(BaseModel):
    fsa: str
    area: str  # FSA region name (fallback: the FSA code)
    user_count: int
    latitude: float  # FSA-region centroid — never a user's location
    longitude: float


class InterestOut(BaseModel):
    slug: str
    interest: str  # human label
    users: int


class InterestGroupOut(BaseModel):
    group: str  # category slug, e.g. "outdoors"
    label: str  # display label, e.g. "Outdoors"
    users: int  # distinct users with >=1 interest in this category
    percentage: float  # share of total category-memberships (groups sum to 100%)


class MeetupFrequencyOut(BaseModel):
    frequency: str
    count: int
    percentage: float


class EngagementOut(BaseModel):
    connection_requests: int
    accepted_connections: int
    declined_connection_requests: int
    messages_sent: int
    meetups_created: int
    meetup_participations: int


class AcceptanceRateOut(BaseModel):
    requests_sent: int
    accepted: int
    declined: int
    pending: int
    cancelled: int
    resolved: int
    # None when there are no resolved requests yet.
    acceptance_rate: float | None = None
    acceptance_rate_denominator: str


class DashboardOut(BaseModel):
    overview: OverviewOut
    family_profile: FamilyProfileOut
    children_age_groups: list[ChildrenAgeGroupOut]
    geographic_distribution: list[GeographicCityOut]
    geographic_map: list[GeographicMapPointOut]
    popular_interests: list[InterestOut]
    meetup_frequency: list[MeetupFrequencyOut]
    interest_groups: list[InterestGroupOut]
    engagement: EngagementOut
    connection_acceptance_rate: AcceptanceRateOut
    privacy_notice: str
