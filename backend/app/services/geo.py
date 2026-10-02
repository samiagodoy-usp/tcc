"""Geographic resolution for postal codes → FSA centroids.

Uses the MIT-licensed ``postalcodes-ca`` package, which ships an offline dataset
of all ~1,651 Canadian Forward Sortation Areas (FSAs) with centroid latitude /
longitude. This lets *any* Canadian postal code resolve to a real FSA centroid
for the haversine proximity scorer — instead of relying on the small, manually
seeded ``fsa_regions`` reference table.

Privacy: only the FSA (first 3 chars) and its centroid are derived here; the
exact postal code is never returned or stored in the clear (docs/06 INV-1..3).

Resolution order:
  1. ``postalcodes-ca`` (authoritative, covers all of Canada), then
  2. the ``fsa_regions`` DB table (fallback / local overrides), then
  3. FSA only, with no centroid (matching still works via same-FSA = 1.0).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.crypto import derive_fsa
from app.models import FsaRegion


@dataclass(frozen=True)
class GeoResolution:
    """The privacy-safe geographic fields derived from a postal code."""

    fsa: str
    centroid_lat: float | None = None
    centroid_lng: float | None = None
    # Raw place name from the source (e.g. "Vancouver (North Hastings-Sunrise)").
    region_name: str | None = None
    # The neighbourhood parsed out of ``region_name`` (e.g. "North
    # Hastings-Sunrise"), used to auto-fill the profile's neighbourhood field.
    neighbourhood: str | None = None
    # Best-effort city / province from the source (postalcodes-ca provides these).
    city: str | None = None
    province: str | None = None


def _split_place_name(name: str | None) -> tuple[str | None, str | None]:
    """Split a postalcodes-ca place name into (city, neighbourhood).

    postalcodes-ca names look like ``"Vancouver (North Hastings-Sunrise)"`` where
    the parenthetical is the neighbourhood/area within the city. When there is no
    parenthetical (e.g. ``"Burnaby"``), the whole thing is treated as the city and
    also used as the neighbourhood so the field still auto-fills with something
    meaningful.
    """
    if not name:
        return None, None
    text = name.strip()
    if "(" in text and text.endswith(")"):
        city, _, rest = text.partition("(")
        neighbourhood = rest[:-1].strip() or None
        city = city.strip() or None
        return city, neighbourhood
    return text or None, text or None


def _lookup_postalcodes_ca(fsa: str) -> GeoResolution | None:
    """Resolve an FSA via postalcodes-ca. Returns None if unavailable/unknown.

    Imported lazily so importing this module never hard-fails if the optional
    data package is missing, and so tests can monkeypatch it easily.
    """
    try:
        from postalcodes_ca import fsa_codes  # noqa: PLC0415
    except Exception:  # pragma: no cover - package/data not importable
        return None
    try:
        record = fsa_codes.get(fsa)
    except (KeyError, ValueError):
        return None
    if record is None:
        return None
    name = getattr(record, "name", None)
    parsed_city, neighbourhood = _split_place_name(name)
    return GeoResolution(
        fsa=fsa,
        centroid_lat=getattr(record, "latitude", None),
        centroid_lng=getattr(record, "longitude", None),
        region_name=name,
        neighbourhood=neighbourhood,
        # postalcodes-ca exposes ``province``; ``city`` is parsed from the name.
        city=parsed_city,
        province=getattr(record, "province", None),
    )


def _lookup_fsa_region_table(db: Session, fsa: str) -> GeoResolution | None:
    """Resolve an FSA from the local ``fsa_regions`` table, if present."""
    region = db.get(FsaRegion, fsa)
    if region is None:
        return None
    city, neighbourhood = _split_place_name(region.region_name)
    return GeoResolution(
        fsa=fsa,
        centroid_lat=region.centroid_lat,
        centroid_lng=region.centroid_lng,
        region_name=region.region_name,
        neighbourhood=neighbourhood,
        city=city,
    )


def resolve_postal_code(db: Session, postal_code: str) -> GeoResolution:
    """Resolve a postal code to its FSA + centroid (privacy-safe).

    Raises ``ValueError`` if the postal code can't yield a valid FSA.
    """
    fsa = derive_fsa(postal_code)  # validates + uppercases; raises on bad input

    resolved = _lookup_postalcodes_ca(fsa)
    if resolved is not None and resolved.centroid_lat is not None:
        return resolved

    # Fall back to the DB reference table (may carry local overrides/clusters).
    from_table = _lookup_fsa_region_table(db, fsa)
    if from_table is not None:
        return from_table

    # Last resort: FSA only. Same-FSA candidates still score 1.0 on proximity;
    # cross-FSA proximity is 0 without a centroid (documented behavior).
    return resolved or GeoResolution(fsa=fsa)
