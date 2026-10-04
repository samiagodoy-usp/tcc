# 05 — Matching Algorithm Specification

## 1. Status and integrity statement

The weights below are an **initial, expert-informed heuristic** derived from the
research desired-features findings (F5, F7, F9). They are **NOT statistically
validated.** This spec defines how the system records the data required for
**future empirical validation**, but makes no claim of current validation.

## 2. Algorithms and weights

Total score is a weighted sum of the component scores, each normalized to
`[0, 1]`: `total = Σ (weight_i × component_i)` → range `[0, 1]`.

**Constraint:** weights must be non-negative and sum to `1.0` (validated in
`recommendation/weights.py`).

### 2.1 `v3` — active algorithm

| Component | Weight | Notes |
|---|---|---|
| Geographic proximity | **0.40** | F5, F9 |
| Shared interests | **0.30** | symmetric-mean overlap (below) |
| Children's age compatibility | **0.20** | keyed on has-children (below) |
| Meetup frequency | **0.10** | F5 |
| Cultural preference | **0.00** | not weighted |

Relative to `v2`, `v3` **swaps interests and children-age** (interests 0.20→0.30,
children-age 0.30→0.20) and changes two component behaviours:

**Shared interests** use the **symmetric mean of per-side overlap** instead of
Jaccard:

`shared_interests = ½ · ( |A ∩ B| / |A|  +  |A ∩ B| / |B| )`

- both list 3, share 2 → **≈ 0.67** (v1/v2 Jaccard gave `2/4 = 0.5`);
- one set is a subset of the other (e.g. 2 ⊂ 3) → **≈ 0.83** (not a misleading
  `1.0`); identical → `1.0`; either side empty → `0.0`.

**Children's age** is scored by whether each side has children (see §3.2):
- **both childless → `1.0`** (two users with no children are a full match on this
  dimension — "no children" is the shared trait);
- **exactly one has children → `0.0`**;
- **both have children →** best age-group overlap.

Net effect for the two symmetric cases the product cares about: two **childless**
users who match perfectly elsewhere reach a full **100%**, and two **parents**
with the same-age children do too, because children-age contributes its whole
`0.20` at score `1.0` in both.

### 2.2 `v2` — retained for comparison

| Component | Weight | Research basis |
|---|---|---|
| Geographic proximity | **0.40** | F5, F9 |
| Children's age compatibility | **0.30** | F5 |
| Shared interests | **0.20** | F5 (Jaccard) |
| Meetup frequency | **0.10** | F5 |
| Cultural preference | **0.00** | (not weighted) |

`v2` increases the emphasis on geographic proximity and removes cultural
preference from ranking. The cultural component is retained in the weight set
(weight `0.00`) so the versions stay structurally comparable, but **components
with a zero weight are omitted from the exposed `component_scores` breakdown** —
they contribute nothing to the total and would otherwise show a meaningless bar
(e.g. "Cultural fit") in the UI. So on `v2`/`v3` the breakdown contains only
location, children's-age, shared-interests, and meetup-pace.

### 2.3 `v1` — initial algorithm (retained for comparison)

| Component | Weight | Research basis |
|---|---|---|
| Geographic proximity | **0.35** | F5, F9 |
| Children's age compatibility | **0.30** | F5 |
| Shared interests | **0.20** | F5 |
| Meetup frequency | **0.10** | F5 |
| Cultural preference | **0.05** | F5, F7 |

### 2.4 Versioning rationale

`v1` is kept registered (and stored in `algorithm_versions`, inactive) so that
recommendations generated under it remain interpretable and the two versions can
be compared for **future empirical validation** (§9). Every persisted
recommendation records the `algorithm_version` used. Both weight sets are
expert-informed heuristics and are **NOT statistically validated** (§1).

## 3. Component scoring definitions

All components return a score in `[0, 1]`.

### 3.1 Geographic proximity (0.35)
- Uses FSA centroids (`centroid_lat/lng`). Distance = haversine (km) — a true
  great-circle distance.
- FSA centroids are resolved at onboarding from the **`postalcodes-ca`** package
  (MIT; offline dataset of all ~1,651 Canadian FSAs), with the `fsa_regions`
  table as a fallback/override. See `app/services/geo.py`.
- Score decays with distance: `score = max(0, 1 - distance_km / MAX_KM)` with
  `MAX_KM` configurable (default 25 km, covering Metro Vancouver).
- Same FSA → 1.0. Beyond `MAX_KM` → 0.
- **Never uses exact address**; only the FSA + its centroid are derived/stored.

### 3.2 Children's age compatibility (0.30)
- Both users' children are compared by **age group** only (F10 privacy).
- Score = best overlap across age-group pairs, where adjacent age groups get
  partial credit (e.g., toddler↔preschool = 0.5).
- **F11 handling:**
  - `v1`/`v2`: if *either* side has no children, the component is *neutralized*
    (neutral 0.5) rather than penalized.
  - `v3` (active): scored by whether each side has children —
    **both childless → `1.0`** (a full match; "no children" is the shared trait),
    **exactly one has children → `0.0`** (no children to be compatible with),
    **both have children →** best age-group overlap. This replaces v1/v2's neutral
    0.5, which misleadingly read as a partial match for both childless-vs-childless
    and parent-vs-childless pairs.

### 3.3 Shared interests (0.20)
- `v1`/`v2`: Jaccard similarity `|A ∩ B| / |A ∪ B|`.
- `v3` (active): symmetric mean of per-side overlap
  `½·(|A∩B|/|A| + |A∩B|/|B|)` — 2 of 3-and-3 → ~0.67, subsets → ~0.83, identical
  → 1.0.
- Empty on either side → 0.

### 3.4 Meetup frequency (0.10)
- Ordinal preference (rarely=0, monthly=1, weekly=2, often=3).
- Score = `1 - |a - b| / 3` (closer cadence = higher score).

### 3.5 Cultural preference (0.05) — soft signal (F7)
- `brazilian_only` ↔ `brazilian_only` → 1.0.
- Any `mixed` involved → 1.0 (mixed is compatible with everyone).
- Mismatched strict preferences → reduced score (e.g., 0.4), **never 0**, and
  **never a hard filter**. Cultural preference does not exclude candidates from
  the result set; it only nudges ranking.

## 4. Explanations (required per recommendation)

Every recommendation includes a human-readable explanation built from the
component scores, e.g.:
> "You're both near V5K, your children are in compatible age groups, and you
> share 2 interests."

The explanation is generated deterministically from component scores by
`recommendation/explanation.py`, so it always matches the stored scores.

## 5. Versioning

- Each algorithm is registered under a version string (`v1`, `v2`, …) in
  `recommendation/registry.py`. The active default is **`v3`**
  (`registry.DEFAULT_VERSION`).
- A version bundles: its `Recommender` implementation + its default weight set.
- Recommendations persist the `algorithm_version` used. This makes results
  reproducible and comparable across versions.

## 6. Configurability

- Default weights per version are defined in code (`DEFAULT_V1_WEIGHTS`,
  `DEFAULT_V2_WEIGHTS`).
- Deployments may override weights via the `algorithm_versions.weights` JSONB
  column without a code change. `weights.py` validates any override
  (non-negative, sums to 1.0).

## 7. Extensibility (future ML replacement)

- The API/service layer depends only on the `Recommender` **protocol**
  (`score(context) -> RecommendationResult`).
- A future ML model (e.g., learned ranking on logged component scores + outcomes)
  is added by implementing the protocol and registering it as `v2`. No API change
  required. This is the intended path for **empirical validation**: use the data
  captured in `recommendations` + connection outcomes to train/evaluate `v2` and
  compare against `v1`.

## 8. Separation from clustering (F8)

KModes segmentation is **offline analytics** (see
[`02-architecture-spec.md`](02-architecture-spec.md) §4). The scorer never reads
segment labels and never runs clustering. Keeping them separate avoids conflating
exploratory segmentation with per-pair scoring.

## 9. Data captured for future validation
- `recommendations.component_scores` (per-component, per-pair)
- `recommendations.total_score`, `algorithm_version`
- Connection outcomes (`connection_requests.status`) can be joined to
  recommendations by `(for_user_id, candidate_user_id)` to study whether higher
  scores correlate with acceptance — **an analysis to be performed later, not a
  claim made now.**
