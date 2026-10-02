"""Onboarding schemas.

The postal code is accepted here (write-only), immediately converted to an
encrypted value + derived FSA, and never echoed back (INV-1/INV-2).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.reference.cities import normalize_city
from app.models.enums import (
    AgeGroup,
    CulturalPreference,
    HouseholdPreference,
    MeetupFrequency,
)
from app.schemas.profile import _normalize_photo_url


class OnboardingRequest(BaseModel):
    # Write-only: used to derive FSA + encrypted storage, never returned.
    postal_code: str = Field(min_length=3, max_length=7, examples=["V5K 0A1"])
    # Service-area city (validated against the canonical list). Publicly visible.
    city: str | None = Field(default=None, max_length=80, examples=["Vancouver"])
    neighbourhood_label: str | None = Field(default=None, max_length=120)
    # Optional link to a profile photo (hosted elsewhere); http(s):// only.
    photo_url: str | None = Field(default=None, max_length=500)
    languages: list[str] = Field(default_factory=lambda: ["pt"])
    interest_slugs: list[str] = Field(default_factory=list)
    meetup_frequency_pref: MeetupFrequency = MeetupFrequency.MONTHLY
    cultural_pref: CulturalPreference = CulturalPreference.MIXED
    # "Who would you like to meet": families / individuals / either (default).
    household_pref: HouseholdPreference = HouseholdPreference.EITHER
    # Optional family info — the platform is NOT children-gated (F11).
    child_age_groups: list[AgeGroup] = Field(default_factory=list)

    @field_validator("city")
    @classmethod
    def _validate_city(cls, value: str | None) -> str | None:
        return normalize_city(value)

    @field_validator("photo_url")
    @classmethod
    def _validate_photo_url(cls, value: str | None) -> str | None:
        return _normalize_photo_url(value)


class OnboardingStatus(BaseModel):
    onboarding_completed: bool
    has_profile: bool
    city: str | None = None
    fsa: str | None = None
    interest_count: int = 0
