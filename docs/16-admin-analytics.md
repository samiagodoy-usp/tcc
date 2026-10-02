# Admin Analytics Dashboard (M14)

Aggregate, privacy-preserving community & platform analytics for administrators,
and for the PertoApp MBA Data Science & Analytics project. Built entirely on the
**existing** PostgreSQL models — no analytics database, no mock data, no new
tables.

## Access control

All endpoints live under `GET /api/v1/admin/analytics/...` and require an
authenticated **administrator** via the existing `AdminUser` dependency
(`app/core/deps.py`):

- **401 Unauthorized** — missing/invalid token (`get_current_user`).
- **403 Forbidden** — authenticated but `role != admin` (`require_admin`).

Regular users can never reach these endpoints.

## Privacy rules (privacy-by-design)

- Every response is **aggregate-only**. No passwords, tokens, message content,
  display names, emails, residential addresses, exact user coordinates, or full
  postal codes are ever returned.
- Location is exposed only at **city** or **FSA** granularity.
- The map uses **FSA-region shared centroids** (`fsa_regions`), never a user's
  `Profile.centroid_lat/lng`.
- **Minimum group size = 3** (`analytics_service.MIN_GROUP_SIZE`). Geographic
  groups with fewer than 3 users are folded into an `"Other (fewer than 3 users
  each)"` bucket in the city distribution, and omitted from the map, to reduce
  re-identification risk. (Totals still reconcile because small groups are
  aggregated, not dropped.)
- Community metrics exclude admin/test accounts and soft-deleted / suspended
  users (`is_active = true AND deleted_at IS NULL AND role != admin`).

## Endpoints & metric definitions

| Endpoint | Returns |
|---|---|
| `GET /admin/analytics/overview` | total users, active users (GAP), connections, meetups |
| `GET /admin/analytics/family-profile` | users with vs. without children |
| `GET /admin/analytics/children-age-groups` | children per age group |
| `GET /admin/analytics/geographic-distribution` | users per city (thresholded) |
| `GET /admin/analytics/geographic-map` | per-FSA counts at FSA centroids (thresholded) |
| `GET /admin/analytics/interests` | interests by user count, desc |
| `GET /admin/analytics/interest-groups` | interests grouped by category; % sums to 100 |
| `GET /admin/analytics/meetup-frequency` | preferred-frequency distribution |
| `GET /admin/analytics/engagement` | requests, accepted, declined, messages, meetups, participations |
| `GET /admin/analytics/connection-acceptance-rate` | acceptance rate over resolved requests |
| `GET /admin/analytics/dashboard` | all of the above in one response |

### 1. Overview
- `total_users` = live members (excludes admins, suspended, soft-deleted).
- `total_connections` = `ConnectionRequest` rows with status `accepted`.
- `total_meetups` = all `Meetup` rows.
- **`active_users`** = live users whose `last_active_at` is within the last
  **30 days** (`ACTIVE_WINDOW_DAYS`). `last_active_at` is stamped (throttled to
  once / 15 min per user) by the auth dependency on authenticated requests, so it
  reflects real activity — not `updated_at`. It is `NULL` until a user's first
  authenticated request after this field shipped, so the count starts low and
  grows (historical activity is not backfilled).

### 2. Family profile
A user "has children" iff their profile has ≥ 1 `Child` row
(`Profile.children.any()` — mirrors the derived `HouseholdType`). Counted over
live profiled users. Percentages are of that population.

### 3. Children age groups
**Interpretation: counts CHILDREN per age group** — one row per child in the
`children` table — NOT users. A user with two children in different groups
contributes to two groups. This matches the model (children are individual rows
each with an `age_group`). All six enum buckets (infant/toddler/preschool/child/
preteen/teen) are always returned (0 when none) for a stable chart axis.

### 4. Geographic distribution
`GROUP BY Profile.city` over live users, most populous first, with the
min-group-size threshold applied.

### 5. Geographic map
Joins `Profile.fsa` → `fsa_regions` and returns `{fsa, area, user_count,
latitude, longitude}` where lat/lng are the **FSA's shared centroid**. FSAs with
< 3 users, or with no `fsa_regions` centroid row, are omitted (not invented).

### 6. Interests
Joins `profile_interests` → `interests`, `GROUP BY` slug/label, ordered by user
count desc. Uses the existing interest taxonomy only.

### 6b. Interest groups (`/interest-groups`)
Aggregates interests into their taxonomy **`category`** (creative / outdoors /
culture / family / social / community / sports / wellness / other) — the category
column already stored per interest; no categories invented.

- `users` = distinct live users with **≥ 1** interest in the category
  (`COUNT(DISTINCT profile_id)`). A user is counted once per category they touch.
- `percentage` = category `users` ÷ **sum of `users` across all categories** × 100.
  Because a multi-category user is counted in each category, the denominator is
  the total category-memberships (not distinct users) — which is exactly why the
  percentages **sum to 100%**. Each bar is that category's *share of interest*.
  (Dividing by distinct users would exceed 100%, since interests overlap.)
- Ordered by `users` desc; empty categories omitted.

### 7. Meetup frequency
`GROUP BY Profile.meetup_frequency_pref` (rarely / monthly / weekly / often),
all buckets returned with counts and percentages.

### 8. Engagement
- `connection_requests` = all `ConnectionRequest` rows.
- `accepted_connections` / `declined_connection_requests` = by status.
- `messages_sent` = `Message` rows with `deleted_at IS NULL` (excludes
  soft-deleted tombstones; never exposes body).
- `meetups_created` = all `Meetup` rows.
- `meetup_participations` = `MeetupAttendee` rows with status `going`.

### 9. Connection acceptance rate

```
acceptance_rate = accepted / (accepted + declined)
```

**Denominator = resolved requests (accepted + declined).** Pending requests are
excluded (no decision yet) and cancelled requests are excluded (withdrawn by the
sender, not a recipient decision). The response includes the raw
accepted/declined/pending/cancelled/resolved counts so the denominator is
transparent. `acceptance_rate` is `null` when there are no resolved requests.

This is an **engagement** metric. It is **not** a claim that the recommendation
algorithm is effective, and no causality is inferred.

## Backend gaps (documented, not invented)

1. **Recommendation impressions / click-through / "request came from a rec"** —
   `Recommendation` rows persist `total_score`/`component_scores` (see the
   existing `GET /admin/analytics/match-quality`), so *average compatibility
   score* and *recs-that-became-accepted-connections* are available. But there is
   **no** impression/view table and **no** origin link on `ConnectionRequest`, so
   "recommendations displayed" and "requests originating from a recommendation"
   are only rough proxies. *Future fix:* an impression/click event table and/or a
   nullable `source_recommendation_id` on `ConnectionRequest`.
2. **RSVP over time** — `MeetupAttendee` has no timestamp, so participation
   counts are available but not a participation time series.

## Performance
All metrics use database-level aggregation (`COUNT` / `GROUP BY` / conditional
aggregation / `HAVING`) — no loading rows into Python, no N+1. For the current
MVP dataset this is ample; if the dataset grows, caching or materialized views
can be layered on without changing the API.

## Frontend contract
Backend-only in this repo. The dashboard should call `GET
/admin/analytics/dashboard` once and render:
- KPI cards: Registered Users, Active Users (last 30 days), Connections, Meetups.
- Donut: users with/without children.
- Bar: children age groups, geographic distribution, popular interests.
- Donut/bar: meetup frequency.
- KPI cards: engagement counters.
- Aggregated Metro Vancouver map from `geographic_map` (FSA centroids).
- Privacy notice: "Aggregated data — personal information and exact user
  locations are not displayed." (also returned as `privacy_notice`).
