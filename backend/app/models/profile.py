"""User profile and children models.

Privacy notes:
- ``postal_code_encrypted`` stores the postal code encrypted at rest (INV-2). It
  is never exposed by any read schema.
- ``fsa`` + ``centroid_lat/lng`` are the only location signals used for matching
  and the coarsest ever exposed (INV-3).
- Children carry an ``age_group`` only — no name, no birthdate (INV-4).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    Enum,
    Float,
    ForeignKey,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONBType, StringArray
from app.models.enums import (
    AgeGroup,
    CulturalPreference,
    HouseholdPreference,
    MeetupFrequency,
)

if TYPE_CHECKING:

    from app.models.interest import ProfileInterest
    from app.models.user import User


class Profile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    languages: Mapped[list[str]] = mapped_column(StringArray, default=list)
    # Link to a profile photo hosted elsewhere (we don't store images). Publicly
    # visible by default; hideable via the visibility map.
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # --- Location (privacy-preserving) ---
    postal_code_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    fsa: Mapped[str | None] = mapped_column(CHAR(3), index=True, nullable=True)
    centroid_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    centroid_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    neighbourhood_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Service-area city (validated against SERVICE_AREA_CITIES at the schema layer).
    # Publicly visible; coarse location, no exact address.
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # --- Matching preferences ---
    meetup_frequency_pref: Mapped[MeetupFrequency] = mapped_column(
        Enum(MeetupFrequency, name="meetup_frequency"),
        default=MeetupFrequency.MONTHLY,
        nullable=False,
    )
    cultural_pref: Mapped[CulturalPreference] = mapped_column(
        Enum(CulturalPreference, name="cultural_preference"),
        default=CulturalPreference.MIXED,
        nullable=False,
    )
    # "Who would you like to meet" — families / individuals / either (default).
    household_pref: Mapped[HouseholdPreference] = mapped_column(
        Enum(HouseholdPreference, name="household_preference"),
        default=HouseholdPreference.EITHER,
        server_default=HouseholdPreference.EITHER.name,
        nullable=False,
    )

    # Per-field visibility controls (docs/06 §7), e.g. {"bio": true, "languages": false}
    visibility: Mapped[dict] = mapped_column(JSONBType, default=dict)

    @property
    def postal_code(self) -> str | None:
        """The decrypted postal code, for OWNER-facing reads only.

        Decrypts ``postal_code_encrypted`` on demand. Only ``OwnProfile`` exposes
        this — the public profile never does — so the plaintext code is returned
        solely to its own owner. Best-effort: returns ``None`` when unset or if
        decryption fails, so a profile read never breaks on a bad/rotated key.
        """
        if not self.postal_code_encrypted:
            return None
        try:
            from app.core.crypto import PostalCodeCipher

            return PostalCodeCipher().decrypt(self.postal_code_encrypted)
        except Exception:  # noqa: BLE001 - never let a decrypt error break a read
            return None

    user: Mapped[User] = relationship(back_populates="profile")
    children: Mapped[list[Child]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    interests: Mapped[list[ProfileInterest]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class Child(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A child, represented ONLY by age group (INV-4)."""

    __tablename__ = "children"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    age_group: Mapped[AgeGroup] = mapped_column(Enum(AgeGroup, name="age_group"), nullable=False)

    profile: Mapped[Profile] = relationship(back_populates="children")
