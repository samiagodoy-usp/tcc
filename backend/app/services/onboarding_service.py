"""Onboarding use case.

Converts the submitted postal code into: encrypted storage (INV-2), a derived FSA
(INV-3), and an FSA centroid looked up from ``fsa_regions`` for distance matching.
The raw postal code is never persisted in plaintext and never returned.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.crypto import PostalCodeCipher
from app.models import Interest, Profile, ProfileInterest, User
from app.models.profile import Child
from app.schemas.onboarding import OnboardingRequest, OnboardingStatus
from app.services.geo import GeoResolution, resolve_postal_code


def _get_or_create_profile(db: Session, user: User) -> Profile:
    profile = db.execute(
        select(Profile).where(Profile.user_id == user.id)
    ).scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user.id, display_name=user.email.split("@")[0])
        db.add(profile)
    return profile


def apply_postal_code(
    db: Session, profile: Profile, postal_code: str
) -> GeoResolution:
    """Encrypt a postal code onto ``profile`` and refresh its FSA + centroid.

    Shared by onboarding and profile edits so a postal-code change is handled
    identically everywhere: the raw code is encrypted at rest (INV-2, never
    returned), and only the derived FSA + centroid are stored for matching
    (INV-3). Returns the :class:`GeoResolution` so the caller can decide how to
    treat the parsed neighbourhood/city. Raises ``ValueError`` (via
    ``resolve_postal_code``) on a postal code that can't yield a valid FSA.
    """
    geo = resolve_postal_code(db, postal_code)  # ValueError -> caller 422
    profile.postal_code_encrypted = PostalCodeCipher().encrypt(postal_code)
    profile.fsa = geo.fsa
    profile.centroid_lat = geo.centroid_lat
    profile.centroid_lng = geo.centroid_lng
    return geo


def complete_onboarding(db: Session, user: User, payload: OnboardingRequest) -> Profile:
    profile = _get_or_create_profile(db, user)

    # Encrypt the raw postal code (never stored/returned in the clear) and
    # resolve it to a privacy-safe FSA + centroid (shared with profile edits).
    geo = apply_postal_code(db, profile, payload.postal_code)

    # Prefer a user-supplied neighbourhood label; otherwise auto-fill from the
    # postal code (the neighbourhood parsed from postalcodes-ca, falling back to
    # the raw place name).
    profile.city = payload.city
    profile.neighbourhood_label = (
        payload.neighbourhood_label or geo.neighbourhood or geo.region_name
    )
    profile.photo_url = payload.photo_url
    profile.languages = payload.languages
    profile.meetup_frequency_pref = payload.meetup_frequency_pref
    profile.cultural_pref = payload.cultural_pref
    profile.household_pref = payload.household_pref

    # Replace interests.
    set_profile_interests(db, profile, payload.interest_slugs)

    # Replace children (age groups only — F11: may be empty).
    profile.children.clear()
    for age_group in payload.child_age_groups:
        profile.children.append(Child(age_group=age_group))

    user.onboarding_completed = True
    db.add(user)
    db.commit()
    db.refresh(profile)
    return profile


def set_profile_interests(db: Session, profile: Profile, slugs: list[str]) -> None:
    """Replace a profile's interests, rejecting any unknown slug (422).

    Previously unknown slugs were silently dropped, so picking an interest the
    backend didn't recognize just lost it (e.g. 3 selected -> 2 saved). Now the
    request fails loudly, surfacing frontend/taxonomy mismatches immediately.
    """
    # De-duplicate while preserving intent; empty is allowed.
    wanted = list(dict.fromkeys(slugs))
    profile.interests.clear()
    if not wanted:
        return
    found = {
        i.slug: i
        for i in db.execute(select(Interest).where(Interest.slug.in_(wanted))).scalars()
    }
    unknown = [s for s in wanted if s not in found]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unknown interest(s): {sorted(unknown)}. "
                "Use slugs from GET /api/v1/interests."
            ),
        )
    for slug in wanted:
        profile.interests.append(ProfileInterest(interest_id=found[slug].id))


def get_status(db: Session, user: User) -> OnboardingStatus:
    profile = db.execute(
        select(Profile)
        .options(selectinload(Profile.interests))
        .where(Profile.user_id == user.id)
    ).scalar_one_or_none()
    return OnboardingStatus(
        onboarding_completed=user.onboarding_completed,
        has_profile=profile is not None,
        city=profile.city if profile else None,
        fsa=profile.fsa if profile else None,
        interest_count=len(profile.interests) if profile else 0,
    )
