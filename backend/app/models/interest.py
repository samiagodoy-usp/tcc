"""Interest taxonomy and the profile<->interest association."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:

    from app.models.profile import Profile


class Interest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interests"

    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ProfileInterest(Base):
    """Association row linking a profile to an interest."""

    __tablename__ = "profile_interests"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    interest_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interests.id", ondelete="CASCADE"), primary_key=True
    )

    profile: Mapped[Profile] = relationship(back_populates="interests")
    interest: Mapped[Interest] = relationship()
