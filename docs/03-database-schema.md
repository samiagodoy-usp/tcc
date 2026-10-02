# 03 — Database Schema

PostgreSQL via SQLAlchemy. All tables use UUID primary keys and
`created_at` / `updated_at` timestamps (via a `TimestampMixin`). Soft-delete via
`deleted_at` where account/data retention matters.

> **Privacy constraint (enforced at schema + serialization):** exact street
> addresses and postal codes are stored **encrypted / hashed at rest**, never
> exposed via any read schema. Matching uses `fsa` (Forward Sortation Area) and
> `centroid_lat/centroid_lng` only. Children carry an **age group**, never a
> public name or exact birthdate.

## Entity overview

```
users ──1:1── profiles ──1:N── children
  │                │
  │                └─1:N── profile_interests ──N:1── interests
  │
  ├─1:N── connection_requests (sender/recipient = users)
  ├─1:N── messages (within a connection)
  ├─1:N── meetups (organizer) ──1:N── meetup_attendees
  ├─1:N── notifications
  ├─1:N── reports (reporter) / blocks (blocker/blocked)
  └─1:N── recommendations (for_user) ──N:1── algorithm_versions

fsa_regions (reference)   services_directory   user_segments (offline analytics)
```

## Tables

### users
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| email | citext unique | login identity |
| password_hash | text | bcrypt/argon2 hash only |
| role | enum(user, admin) | authz |
| is_active | bool | |
| onboarding_completed | bool | gates matching |
| created_at / updated_at | timestamptz | |
| deleted_at | timestamptz null | soft delete for account deletion |

### profiles
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| user_id | uuid FK → users unique | |
| display_name | text | public |
| bio | text null | public |
| languages | text[] | e.g. {pt, en} |
| **postal_code_encrypted** | bytea | encrypted at rest, never serialized |
| **fsa** | char(3) | matching key (e.g. `V5K`) |
| centroid_lat / centroid_lng | double precision | FSA centroid, for distance |
| city | text null | service-area city (validated against the canonical list); public |
| neighbourhood_label | text | coarse public label |
| meetup_frequency_pref | enum(rarely, monthly, weekly, often) | matching signal |
| cultural_pref | enum(mixed, prefers_brazilian, brazilian_only) | soft signal (F7) |
| visibility | jsonb | per-field visibility controls |

### children
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| profile_id | uuid FK → profiles | |
| **age_group** | enum(infant, toddler, preschool, child, preteen, teen) | **no name, no birthdate** |

### interests
| id uuid PK | slug text unique | label text | category text |

### profile_interests
| profile_id FK | interest_id FK | (PK composite) |

### fsa_regions (reference data)
| fsa char(3) PK | centroid_lat | centroid_lng | cluster_id int null | region_name text |
- `cluster_id` records the three major geographic clusters (F9) for analytics.

### connection_requests
| id uuid PK | sender_id FK users | recipient_id FK users | status enum(pending, accepted, declined, cancelled) | message text null | responded_at ts null |
- Unique partial index on (sender_id, recipient_id) where status = pending.

### messages
| id uuid PK | connection_id FK connection_requests | sender_id FK users | body text | read_at ts null |
- Only allowed when the referenced connection is `accepted`.

### meetups
| id uuid PK | organizer_id FK users | title | description | starts_at ts | fsa char(3) | centroid_lat/lng | is_brazilian_focused bool | status enum(open, cancelled, completed) |

### meetup_attendees
| meetup_id FK | user_id FK | status enum(going, maybe, declined) | (PK composite) |

### services_directory
| id uuid PK | name | category | description | contact | url | fsa char(3) null | approved bool | submitted_by FK users null |

### notifications
| id uuid PK | user_id FK | type enum(...) | payload jsonb | read_at ts null |

### reports
| id uuid PK | reporter_id FK users | target_user_id FK users null | target_message_id FK messages null | reason enum | details text | status enum(open, reviewing, actioned, dismissed) |

### blocks
| blocker_id FK users | blocked_id FK users | (PK composite) | created_at |
- Enforced in matching, messaging, and visibility (mutual invisibility).

### refresh_tokens
| column | type | notes |
|---|---|---|
| id | uuid PK | |
| jti | text unique | the refresh token's JWT id |
| user_id | uuid FK → users | owner |
| expires_at | timestamptz | token expiry |
| revoked_at | timestamptz null | set on rotation, logout, or account deletion |
- Enables refresh-token **rotation and revocation** (docs/06 §2). A refresh token
  whose `jti` is unknown, expired, or revoked is rejected.

### algorithm_versions
| id uuid PK | version text unique (e.g. `v1`) | description | weights jsonb | is_active bool | created_at |
- Stores the configurable weight set per version. Enables versioning + config.

### recommendations
| id uuid PK | for_user_id FK users | candidate_user_id FK users | algorithm_version_id FK | total_score numeric | **component_scores jsonb** | explanation text | generated_at ts |
- **Persists per-component scores** for every recommendation → enables **future
  empirical validation** (correlate scores with connection outcomes). No claim of
  validation is made by storing them.

### user_segments (offline analytics — separate from scoring)
| id uuid PK | user_id FK | segment_label int | model_run_id text | features_snapshot jsonb | created_at |
- Written **only** by the offline KModes pipeline. Never read by the scorer.

## Notes on retention & deletion
- Account deletion: set `users.deleted_at`, purge/anonymize PII (profile,
  children, messages) per retention policy; keep aggregate analytics rows
  anonymized. See [`06-security-privacy-spec.md`](06-security-privacy-spec.md).
