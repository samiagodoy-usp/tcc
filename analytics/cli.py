from __future__ import annotations

import argparse

from sqlalchemy import select

from app.analytics.segmentation.features import (
    SegmentFeatures,
    child_age_band,
    interest_bucket,
)
from app.analytics.segmentation.kmodes_pipeline import DEFAULT_N_CLUSTERS, run_kmodes
from app.db.session import SessionLocal
from app.models import Profile, UserSegment


def _load_features(session) -> list[SegmentFeatures]:
    rows: list[SegmentFeatures] = []
    profiles = session.execute(select(Profile)).scalars().all()
    for profile in profiles:
        ordinals = tuple(child.age_group.ordinal for child in profile.children)
        rows.append(
            SegmentFeatures(
                user_id=str(profile.user_id),
                fsa=profile.fsa or "unknown",
                has_children="yes" if profile.children else "no",
                child_age_band=child_age_band(ordinals),
                meetup_frequency_pref=profile.meetup_frequency_pref.value,
                cultural_pref=profile.cultural_pref.value,
                interest_bucket=interest_bucket(len(profile.interests)),
            )
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline KModes segmentation.")
    parser.add_argument("--clusters", type=int, default=DEFAULT_N_CLUSTERS)
    parser.add_argument(
        "--dry-run", action="store_true", help="Compute labels but do not persist."
    )
    args = parser.parse_args()

    session = SessionLocal()
    try:
        rows = _load_features(session)
        result = run_kmodes(rows, n_clusters=args.clusters)
        print(f"Run {result.model_run_id}: {len(result.labels)} users, k={result.n_clusters}")
        if args.dry_run:
            return
        for user_id, label in result.labels.items():
            feats = next(r for r in rows if r.user_id == user_id)
            session.add(
                UserSegment(
                    user_id=user_id,
                    segment_label=label,
                    model_run_id=result.model_run_id,
                    features_snapshot=feats.as_feature_dict(),
                )
            )
        session.commit()
        print("Segments persisted.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
