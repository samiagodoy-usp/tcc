"""Enumerations shared by ORM models and schemas.

Ordinal helpers are provided where the ordering carries meaning for matching
(e.g., meetup frequency, child age groups).
"""

from __future__ import annotations

import enum


class UserRole(enum.StrEnum):
    USER = "user"
    ADMIN = "admin"


class AgeGroup(enum.StrEnum):
    """Child representation is age-group only — never a name or birthdate (INV-4)."""

    INFANT = "infant"  # 0-1
    TODDLER = "toddler"  # 1-3
    PRESCHOOL = "preschool"  # 3-5
    CHILD = "child"  # 6-9
    PRETEEN = "preteen"  # 10-12
    TEEN = "teen"  # 13-17

    @property
    def ordinal(self) -> int:
        return _AGE_GROUP_ORDER[self]


_AGE_GROUP_ORDER: dict[AgeGroup, int] = {
    AgeGroup.INFANT: 0,
    AgeGroup.TODDLER: 1,
    AgeGroup.PRESCHOOL: 2,
    AgeGroup.CHILD: 3,
    AgeGroup.PRETEEN: 4,
    AgeGroup.TEEN: 5,
}


class HouseholdType(enum.StrEnum):
    """Derived (not stored) household type for the Discover filter.

    ``FAMILY`` = the profile has at least one child; ``INDIVIDUAL`` = no children.
    Computed from the ``Profile.children`` relationship, so it needs no migration
    and reflects current data. Used only as a match filter, never persisted.
    """

    FAMILY = "family"
    INDIVIDUAL = "individual"


class MeetupFrequency(enum.StrEnum):
    RARELY = "rarely"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    OFTEN = "often"

    @property
    def ordinal(self) -> int:
        return _MEETUP_FREQUENCY_ORDER[self]


_MEETUP_FREQUENCY_ORDER: dict[MeetupFrequency, int] = {
    MeetupFrequency.RARELY: 0,
    MeetupFrequency.MONTHLY: 1,
    MeetupFrequency.WEEKLY: 2,
    MeetupFrequency.OFTEN: 3,
}


class CulturalPreference(enum.StrEnum):
    """Cultural meetup preference. A *soft* signal only (F7) — never a hard filter."""

    MIXED = "mixed"
    PREFERS_BRAZILIAN = "prefers_brazilian"
    BRAZILIAN_ONLY = "brazilian_only"


class HouseholdPreference(enum.StrEnum):
    """Who a user would like to meet ("who would you like to meet").

    A stored profile preference (distinct from :class:`HouseholdType`, which is a
    transient Discover query filter with no "no preference" option). ``EITHER`` is
    the default so a user can express no preference.
    """

    FAMILIES = "families"  # prefers to meet people who have children
    INDIVIDUALS = "individuals"  # prefers to meet people without children
    EITHER = "either"  # no preference


class ConnectionStatus(enum.StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class MeetupStatus(enum.StrEnum):
    OPEN = "open"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class RsvpStatus(enum.StrEnum):
    GOING = "going"
    MAYBE = "maybe"
    DECLINED = "declined"


class NotificationType(enum.StrEnum):
    CONNECTION_REQUEST = "connection_request"
    CONNECTION_ACCEPTED = "connection_accepted"
    NEW_MESSAGE = "new_message"
    MEETUP_INVITE = "meetup_invite"
    SYSTEM = "system"


class PlaceType(enum.StrEnum):
    """Public meeting-place categories (Nearby Places, F-PLACES).

    Extensible: add new categories here (e.g. ``library``, ``playground``) and
    normalize source values to them in each provider — no schema change needed.
    """

    PARK = "park"
    COMMUNITY_CENTRE = "community_centre"


class ReportReason(enum.StrEnum):
    HARASSMENT = "harassment"
    SPAM = "spam"
    INAPPROPRIATE = "inappropriate"
    SAFETY = "safety"
    OTHER = "other"


class ReportStatus(enum.StrEnum):
    OPEN = "open"
    REVIEWING = "reviewing"
    ACTIONED = "actioned"
    DISMISSED = "dismissed"
