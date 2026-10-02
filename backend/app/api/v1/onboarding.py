"""Onboarding endpoints (M2)."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.onboarding import OnboardingRequest, OnboardingStatus
from app.services import onboarding_service

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("", response_model=OnboardingStatus)
def submit_onboarding(
    payload: OnboardingRequest, current_user: CurrentUser, db: DbSession
) -> OnboardingStatus:
    onboarding_service.complete_onboarding(db, current_user, payload)
    return onboarding_service.get_status(db, current_user)


@router.get("/status", response_model=OnboardingStatus)
def onboarding_status(current_user: CurrentUser, db: DbSession) -> OnboardingStatus:
    return onboarding_service.get_status(db, current_user)
