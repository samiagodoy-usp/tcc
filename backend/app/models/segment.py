"""Offline KModes segmentation output (F8).

This table is written ONLY by the offline segmentation pipeline
(``app/analytics/segmentation``) and is never read by the recommendation scorer.
It exists to keep exploratory clustering fully separate from live scoring.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONBType


class UserSegment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_segments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    segment_label: Mapped[int] = mapped_column(Integer, nullable=False)
    model_run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    features_snapshot: Mapped[dict] = mapped_column(JSONBType, default=dict)
