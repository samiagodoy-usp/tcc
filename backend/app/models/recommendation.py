"""Algorithm versioning and persisted recommendations.

Every recommendation stores its per-component scores, total, version, and a
human-readable explanation. This is the data captured to enable FUTURE empirical
validation (docs/05 §9) — storing it makes no claim that the weights are
validated.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.types import JSONBType


class AlgorithmVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A registered matching-algorithm version and its (configurable) weights."""

    __tablename__ = "algorithm_versions"

    version: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Configurable weight set for this version (validated to sum to 1.0 in code).
    weights: Mapped[dict] = mapped_column(JSONBType, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Recommendation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recommendations"

    for_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    algorithm_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("algorithm_versions.id", ondelete="RESTRICT"), nullable=False
    )
    total_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    # Per-component scores, e.g. {"geographic_proximity": 0.92, ...}
    component_scores: Mapped[dict] = mapped_column(JSONBType, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
