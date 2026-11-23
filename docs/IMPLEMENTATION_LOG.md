# KONNTO v2 — implementation log

## Product direction
KONNTO is being developed as a universal AI platform for individuals, businesses,
professionals and organisations. The first production-grade experience is the
complete KONNTO Business OS. Personal and Professional experiences are subsequent
phases on the same shared foundation. KONNTO CENTRAL remains a later expansion.

## Changes committed on `konnto-v2-foundation`

- Added the v2 K-BRAIN/PCM behavioural prompt and baseline implementation documents.
- Updated the brain prompt wiring and removed contradictory product claims.
- Made demo seeding opt-in through `KONNTO_DEMO_MODE=true`; default is disabled.
  This preserves the demo seeder but prevents fictional demo records from being
  inserted into ordinary customer onboarding by default.
- Changed explicit organisation selection so an inaccessible `X-Org-Id` returns
  HTTP 403 instead of silently falling back to another organisation.
- Passed the actual audio transcript into K-BRAIN attachment context.
- Changed reminder processing to mark a reminder as sent only after at least one
  supported channel confirms delivery. The target-member lookup is also scoped to
  the reminder's organisation.

## Verification status

- GitHub branch and commit state were checked.
- The branch is ahead of `main`; `main` has not been modified.
- No local runtime, database or production-like environment was available in this
  work session. Automated tests, Python compilation, frontend build, migrations,
  and end-to-end flows have NOT been run after these changes.
- The GitHub repository does not provide evidence in this work session that these
  changes passed CI. Treat them as implemented but unverified.

## Remaining high-priority work

1. Full route-by-route and collection-by-collection tenant isolation audit.
2. Regression tests for explicit organisation selection and customer onboarding.
3. Validate the demo flag in isolated preview/demo deployment configuration.
4. Approval authority, state transitions, idempotency and duplicate-action review.
5. Durable scheduled jobs and retry-safe daily brief delivery.
6. Voice upload cancellation and chat SSE error handling.
7. Pending-state relevance and safe consumption.
8. Complete privacy export/deletion collection inventory.
9. PCM instruction lifecycle, authority engine, owner decision queue and audit trail.
10. K-Memory provenance, permission filtering, corrections and retention.
11. Data-backed Business Intelligence with transparent formulas and confidence.
12. Personal and Professional product experiences on the shared platform foundation.
13. Production security, observability, backup/restore, performance and cost controls.

## Release rule
Do not merge to `main`, deploy, or onboard real customer data until the relevant
regression tests, security review, deployment configuration checks and controlled
pilot acceptance criteria have passed.
