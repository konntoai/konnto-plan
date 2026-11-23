# KONNTO v2 — implementation log

## Product direction
KONNTO is being developed as a universal AI platform for individuals, businesses,
professionals and organisations. The first production-grade experience is the
complete KONNTO Business OS. Personal and Professional experiences are subsequent
phases on the same shared foundation. KONNTO CENTRAL remains a later expansion.

## Changes committed on `konnto-v2-foundation`

### K-BRAIN and product behaviour
- Added the K-BRAIN v2 master prompt for one shared business intelligence engine,
  permission-aware memory, eight departmental intelligence contexts, transparent
  diagnostics, cross-department reasoning, authority boundaries and truthful
  execution reporting.
- Added a 20-case behaviour evaluation set covering privacy, role permissions,
  memory, approvals, PCM, diagnostics and truthfulness.
- Updated stale WhatsApp FAQ wording to be configuration-aware.
- Removed an obsolete legacy prompt instruction claiming PCM did not exist.

### KONNTO PCM
- Added `backend/routes_pcm.py` with an organisation-scoped instruction register,
  issuance, role/reporting-line checks, acknowledgement, progress, blocker reports,
  completion evidence and cancellation.
- PCM instructions reuse the existing Work item engine; no second task engine was
  introduced.
- Added a PCM workspace in the frontend and navigation route.
- Added live PCM instruction context to K-BRAIN, filtered by the current member's
  permissions.
- Added a two-stage scheduled follow-up: assignee reminder after a 30-minute
  overdue grace period, then issuer escalation after a further 24 hours. Delivery
  must be confirmed by an available channel before the follow-up stage advances.
- Added pure authorization policy helpers and isolated unit tests. An initial test
  caught and corrected a partner-role privilege edge case.

### Foundation and reliability fixes
- Made demo seeding opt-in through `KONNTO_DEMO_MODE=true`; default is disabled.
- An inaccessible explicit `X-Org-Id` now returns HTTP 403 instead of silently
  falling back to another organisation.
- Passed actual voice-note transcripts into K-BRAIN context.
- Reminder processing now marks a reminder as sent only after at least one
  supported channel confirms delivery, and target lookup is organisation-scoped.
- Added GitHub Actions checks for Python compilation and isolated PCM policy tests.

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
