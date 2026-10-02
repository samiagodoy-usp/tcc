# 00 — Research Findings (Source of Truth)

This document records the research inputs that guide PertoApp. These findings come
from an academic research project that surveyed **61 Brazilian community members**
in Metro Vancouver, British Columbia.

## Ground rules for using this document

1. These findings are **product-discovery inputs**, not validated product metrics.
2. **Do not invent** statistical conclusions that are not present below.
3. **Do not claim** that the proposed matching weights have been statistically
   validated. They are an expert-informed starting heuristic.
4. The application must be **designed to allow future empirical validation** of
   its assumptions (e.g., by logging recommendation component scores, connection
   outcomes, and algorithm versions).

## Findings

| # | Finding |
|---|---------|
| F1 | Strong demand for social connections and support networks. |
| F2 | 26 respondents reported *frequently* missing social connections; another 26 reported *sometimes*. |
| F3 | 38 respondents said they *would* use the proposed app; 16 said *maybe*. |
| F4 | 45 respondents expressed interest in joining a pilot group. |
| F5 | Important desired features: geographic proximity, shared interests, compatibility between children's age groups, meetups/playdates, community events, and communication. |
| F6 | 50 respondents expressed interest in Brazilian local services. |
| F7 | Approximately **29.5%** preferred *exclusively* Brazilian meetups. |
| F8 | Three exploratory user segments were identified using **KModes**. |
| F9 | Geographic analysis using Canadian postal-code **FSAs** identified three major geographic clusters. |
| F10 | Privacy and security were identified as important requirements. |
| F11 | The need for social connection **extends beyond users with children**. |

## Product implications (derived, non-statistical)

- **F5 → matching signals.** Geographic proximity, children's age-group
  compatibility, shared interests, meetup frequency, and cultural preference are
  first-class matching signals.
- **F11 → not children-gated.** Family/children profiles are *optional*.
  Individuals without children are full participants.
- **F7 → cultural preference is a soft signal.** A minority preference for
  exclusively-Brazilian meetups is modeled as a low-weight, user-controlled
  preference — never a hard filter that excludes people.
- **F9 → FSA-based geography.** Matching uses Forward Sortation Areas (FSA) and/or
  geographic centroids, never exact addresses.
- **F10 → privacy by design.** Exact addresses, exact locations, and child names
  are never publicly visible.
- **F8 → offline segmentation only.** KModes segments are exploratory analytics,
  kept separate from live recommendation scoring.
- **F4 → pilot readiness.** The system should support a pilot cohort and capture
  data enabling later validation.
