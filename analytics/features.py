from __future__ import annotations

from dataclasses import asdict, dataclass


SEGMENT_FEATURE_COLUMNS: tuple[str, ...] = (
    "fsa",
    "has_children",
    "child_age_band",
    "meetup_frequency_pref",
    "cultural_pref",
    "interest_bucket",
)


@dataclass(frozen=True)
class SegmentFeatures:

    user_id: str
    fsa: str
    has_children: str  # "yes" / "no"
    child_age_band: str  # coarse band or "none"
    meetup_frequency_pref: str
    cultural_pref: str
    interest_bucket: str  # coarse count bucket, e.g. "0", "1-2", "3-5", "6+"

    def as_feature_dict(self) -> dict[str, str]:
        d = asdict(self)
        d.pop("user_id")
        return d


def interest_bucket(count: int) -> str:
    if count <= 0:
        return "0"
    if count <= 2:
        return "1-2"
    if count <= 5:
        return "3-5"
    return "6+"


def child_age_band(age_group_ordinals: tuple[int, ...]) -> str:
   
    if not age_group_ordinals:
        return "none"
    youngest = min(age_group_ordinals)
    if youngest <= 1:
        return "early"  # infant/toddler
    if youngest <= 3:
        return "mid"  # preschool/child
    return "older"  # preteen/teen
