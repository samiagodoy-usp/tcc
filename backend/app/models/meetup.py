"""Meetups / playdates / community events (FR-MEET-*).

Meetups expose an FSA-level location only; exact coordinates are never shown to
non-attendees (INV-3).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CHAR, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import MeetupStatus, RsvpStatus


class Meetup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meetups"

    organizer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    fsa: Mapped[str | None] = mapped_column(CHAR(3), index=True, nullable=True)
    centroid_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    centroid_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Optional link to the meetup location (e.g. Google Maps URL, venue page).
    location_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Optional cap on how many families/attendees may join. None = no limit.
    max_families: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_brazilian_focused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[MeetupStatus] = mapped_column(
        Enum(MeetupStatus, name="meetup_status"), default=MeetupStatus.OPEN, nullable=False
    )

    attendees: Mapped[list[MeetupAttendee]] = relationship(
        back_populates="meetup", cascade="all, delete-orphan"
    )


class MeetupAttendee(Base):
    __tablename__ = "meetup_attendees"

    meetup_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetups.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[RsvpStatus] = mapped_column(
        Enum(RsvpStatus, name="rsvp_status"), default=RsvpStatus.GOING, nullable=False
    )

    meetup: Mapped[Meetup] = relationship(back_populates="attendees")
