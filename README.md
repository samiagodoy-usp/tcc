# PertoApp — TCC Code Excerpt

A **read-only showcase** of selected PertoApp source files for the MBA Data
Science & Analytics final project (TCC). It highlights the three parts most
relevant to the project — the **recommendation engine**, the **analytics
dashboard**, and the **onboarding → profile → model-variables pipeline** — plus
the supporting data schema and written specs.

> This folder is a *curated copy* for reading and citation, not a runnable
> application. Security/privacy internals and infrastructure config are
> intentionally excluded (see "What's excluded" below), so the excerpt will not
> run on its own. The complete, runnable system lives in the private repository.

## Privacy & safety

- **Code only — no data.** There is no database, no user data, no logs, and no
  secrets in this excerpt.
- Files reference privacy primitives (e.g. `PostalCodeCipher`, `derive_fsa`) to
  show the **privacy-by-design** approach — location is handled at FSA
  granularity and postal codes are encrypted at rest — but the implementations of
  those primitives (encryption, JWT, config) are **not** included here.
- Analytics is **aggregate-only** and exposes no personal information or exact
  coordinates.

## Layout

```
tcc-excerpt/
  backend/app/
    recommendation/   # the matching algorithm (components, weights, combiner)
    services/         # matching, analytics, onboarding, geo orchestration
    api/v1/           # analytics + onboarding endpoints
    schemas/          # analytics + onboarding request/response models
    models/           # data schema: profile, interests, enums, recommendation, …
  docs/               # research → requirements → schema → algorithm → analytics
```

## Reading guide (recommended order)

1. **`docs/00-research-findings.md` → `docs/01-product-requirements.md`** — the
   survey findings and the requirements derived from them (the project's premise).
2. **`docs/03-database-schema.md`** + `backend/app/models/` — how the research
   became data: profiles, interests, children age groups, meetup/cultural
   preferences, FSA-based location.
3. **Onboarding pipeline** — `backend/app/services/onboarding_service.py`,
   `api/v1/onboarding.py`, `schemas/onboarding.py`, `services/geo.py`: how survey
   answers become the model's input variables (interests, children, preferences,
   FSA centroid).
4. **Recommendation engine** — `docs/05-matching-algorithm-spec.md` (methodology)
   alongside `backend/app/recommendation/components.py` (per-factor scoring),
   `weights.py` (parameters), `weighted.py` (combiner), `explanation.py`
   (match reasons), and `services/matching_service.py` (filtering + ranking +
   score persistence). This is the core contribution.
5. **Analytics** — `docs/16-admin-analytics.md` (metric definitions, formulas,
   privacy rules) alongside `backend/app/services/analytics_service.py`
   (aggregation logic), `api/v1/analytics.py`, `schemas/analytics.py`.

## The story this excerpt tells

```
survey findings (docs/00)
  → product requirements (docs/01)
    → data model (docs/03 + models/)
      → onboarding captures the variables (onboarding_service, geo)
        → recommendation scores compatibility (recommendation/, matching_service)
          → platform usage is measured in aggregate (analytics_service)
```

## What's excluded (and why)

To protect the live platform and its users, these are **not** in this excerpt:

- Security/auth internals: JWT handling, password/token logic, auth endpoints.
- Encryption & secret handling (postal-code cipher implementation, key loading).
- Application configuration / environment wiring (secret names, DB URL shape).
- The security & privacy specification (threat model) — kept private.
- All environment files and deployment configuration.

A full manifest of what is safe vs. not safe to publish is in the main repo at
`docs/TCC-public-files.md`.
