"""Reference data: Forward Sortation Area (FSA) regions.

Records FSA centroids used for privacy-preserving distance matching, plus the
three major geographic clusters identified in the research (F9) for analytics.
"""

from __future__ import annotations

from sqlalchemy import CHAR, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FsaRegion(Base):
    __tablename__ = "fsa_regions"

    fsa: Mapped[str] = mapped_column(CHAR(3), primary_key=True)
    centroid_lat: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lng: Mapped[float] = mapped_column(Float, nullable=False)
    region_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # One of the three exploratory geographic clusters (F9); analytics only.
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
