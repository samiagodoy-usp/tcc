# 01 — Product Requirements Specification (PRS)

## 1. Vision

PertoApp helps Brazilian families and individuals in Metro Vancouver find and
build **local social connections** — playdates, friendships, community events,
and access to Brazilian local services — in a **privacy-first** way.

Grounded in research findings F1–F11 (see
[`00-research-findings.md`](00-research-findings.md)).

## 2. Goals and non-goals

### Goals
- Enable users to discover nearby, compatible people and families (F1, F5).
- Support connection requests, messaging, and meetups (F5).
- Provide a Brazilian local services directory (F6).
- Preserve privacy of exact location and children (F10).
- Capture data that enables **future empirical validation** of matching quality.

### Non-goals
- Not a dating app.
- Not a public social feed.
- No exact-location sharing, ever.
- The matching weights are **not** presented as validated science.

## 3. Personas (grounded in research, illustrative)

- **Parent seeking playdates** — wants children of compatible age groups nearby.
- **Newcomer individual** — wants social connection and support networks; may
  have no children (F11).
- **Community-oriented member** — interested in Brazilian events and services (F6).

> The three exploratory KModes segments (F8) inform analytics and future
> personalization but do **not** define product access tiers.

## 4. Functional requirements by module

Each requirement has an ID `FR-<module>-<n>`.

### 4.1 Authentication (M1)
- FR-AUTH-1: Users register with email + password.
- FR-AUTH-2: Passwords stored only as salted hashes.
- FR-AUTH-3: Login issues short-lived JWT access token + refresh token.
- FR-AUTH-4: Authenticated endpoints require a valid access token.

### 4.2 Onboarding (M2)
- FR-ONB-1: Guided onboarding captures FSA (from postal code), interests, meetup
  preference, and optional family info.
- FR-ONB-2: Onboarding completion flag gates access to matching.

### 4.3 User profiles (M3)
- FR-PROF-1: Profile stores display name, bio, languages, and neighbourhood label
  (FSA-level, never exact address).
- FR-PROF-2: Users control which profile fields are visible.

### 4.4 Family / children profiles (M4)
- FR-FAM-1: Family profiles are **optional** (F11).
- FR-FAM-2: Children are represented by **age group only**; no public child names
  and no birthdates exposed publicly (F10).

### 4.5 Interests (M5)
- FR-INT-1: Curated interest taxonomy; users select multiple interests.

### 4.6 Matching (M6)
- FR-MATCH-1: Given a requesting user, return ranked candidate matches.
- FR-MATCH-2: Every match carries a **total score**, **per-component scores**, an
  **algorithm version**, and a **human-readable explanation**.
- FR-MATCH-3: Cultural preference is a soft signal, never a hard exclusion (F7).

### 4.7 Connection requests (M7)
- FR-CONN-1: A user can send a connection request to another user.
- FR-CONN-2: Recipient can accept/decline. Messaging unlocks only after acceptance.

### 4.8 Messaging (M8)
- FR-MSG-1: 1:1 messaging between connected users only.
- FR-MSG-2: Messages can be reported.

### 4.9 Meetups (M9)
- FR-MEET-1: Users create meetups/playdates and community events (F5).
- FR-MEET-2: Meetups expose an FSA-level location, never an exact address to
  non-attendees.

### 4.10 Brazilian services directory (M10)
- FR-SVC-1: Browsable/searchable directory of Brazilian local services (F6).
- FR-SVC-2: Listings are moderated (admin-approved).

### 4.11 Notifications (M11)
- FR-NOTIF-1: In-app notifications for connection requests, messages, meetups.

### 4.12 Reporting / blocking (M12)
- FR-REP-1: Users can block other users (mutual invisibility).
- FR-REP-2: Users can report users/content; reports queue for admin review.

### 4.13 Admin (M13)
- FR-ADM-1: Admins review reports, moderate services, manage users.

### 4.14 Analytics (M14)
- FR-ANL-1: Aggregate, privacy-preserving analytics (e.g., match acceptance rate
  by component score) to enable **future validation** of the algorithm.
- FR-ANL-2: KModes segmentation results are stored as offline analytics artifacts.

## 5. Non-functional requirements
- **Privacy** (see [`06-security-privacy-spec.md`](06-security-privacy-spec.md)).
- **Independently deployable** frontend and backend.
- **Maintainability**: clean architecture, no single-file monolith.
- **Testability**: each module has tests.
- **Configurability**: matching weights configurable without code changes.

## 6. Success signals for a pilot (F4)
- Pilot cohort can register, be matched, connect, and meet up.
- Recommendation component scores + connection outcomes are logged for later
  analysis. (No claim of validated effectiveness is made pre-analysis.)
