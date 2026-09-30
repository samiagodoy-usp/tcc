from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.analytics.segmentation.features import SEGMENT_FEATURE_COLUMNS, SegmentFeatures

DEFAULT_N_CLUSTERS = 3  

@dataclass
class SegmentationResult:
    model_run_id: str
    n_clusters: int
    labels: dict[str, int]  # user_id -> segment label
    cluster_centroids: list[dict[str, str]]


def run_kmodes(
    rows: list[SegmentFeatures],
    n_clusters: int = DEFAULT_N_CLUSTERS,
    random_state: int = 42,
) -> SegmentationResult:

    if not rows:
        return SegmentationResult(
            model_run_id=_new_run_id(), n_clusters=n_clusters, labels={}, cluster_centroids=[]
        )

    import pandas as pd  # noqa: PLC0415
    from kmodes.kmodes import KModes  # noqa: PLC0415

    frame = pd.DataFrame([r.as_feature_dict() for r in rows], columns=list(SEGMENT_FEATURE_COLUMNS))
    matrix = frame.to_numpy()

    distinct_rows = len({tuple(row) for row in matrix.tolist()})
    effective_k = max(1, min(n_clusters, distinct_rows))
    model = KModes(n_clusters=effective_k, init="Huang", n_init=5, random_state=random_state)
    labels = model.fit_predict(matrix)

    centroids = [
        dict(zip(SEGMENT_FEATURE_COLUMNS, centroid, strict=False))
        for centroid in model.cluster_centroids_
    ]
    return SegmentationResult(
        model_run_id=_new_run_id(),
        n_clusters=effective_k,
        labels={row.user_id: int(label) for row, label in zip(rows, labels, strict=True)},
        cluster_centroids=centroids,
    )


def _new_run_id() -> str:
    return f"kmodes-{uuid.uuid4().hex[:12]}"
