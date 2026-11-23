# KONNTO AI — implementation baseline

## Long-term product direction
KONNTO is intended to become a universal AI platform serving individuals, businesses,
professionals and organisations. The shared foundation should support multiple
permissioned experiences without splitting into independent products or duplicating
the intelligence, memory, identity or execution layers.

Initial production focus: complete KONNTO Business OS (K-BRAIN, Chat, PCM, K-Memory,
authority controls and data-backed business intelligence). Personal and Professional
experiences follow on the same foundation. KONNTO CENTRAL/global intelligence remains
a later expansion and is not part of the initial release scope.

This branch is the controlled upgrade path for the existing KONNTO application.
Do not deploy this branch or merge it to main until its tests and review pass.

## Product scope
- K-BRAIN: one shared, permission-aware business intelligence engine.
- KONNTO Chat: conversational workspace.
- KONNTO PCM: AI-powered business coordination and execution authority, bounded by backend permissions.
- K-Memory: structured, source-aware organisational memory.
- Existing Work, Team, Approvals, Documents and Knowledge modules remain the source of truth for their records.

## Explicitly deferred
KONNTO CENTRAL/global portfolio intelligence, Tally, Zoho, banking integrations, global market intelligence and external
marketplace functionality. WhatsApp and email must be treated as available only
when their integration configuration and delivery status are verified. Do not claim these are available.

## Implementation principles
1. Preserve working functionality; do not rebuild the application from scratch.
2. Backend permissions and tenant isolation are authoritative.
3. One shared K-BRAIN; departmental intelligence are contexts, not separate agents.
4. PCM actions require real tools, audit records and authority checks.
5. Reuse existing task/project/approval records; do not create duplicate systems.
6. Demo seed data is intentional in the demo environment. Isolate it from real
   customer onboarding rather than deleting the demo.
7. No UI-only feature is complete without backend behaviour and tests.
8. Never report a feature as working without executing its tests.

## Known baseline findings to verify
- The legacy prompt contained a contradictory no-PCM instruction; updated to reflect the PCM workspace.
- Voice transcript context was fixed; verify with an end-to-end voice test.
- Reminder delivery now waits for a confirmed channel; daily brief deduplication still needs retry-safe redesign.
- Frontend SSE error event handling may leave a streaming response unresolved.
- Cancelled voice recordings may still upload.
- Pending-state consumption may consume unrelated next messages.
- Item/project visibility and related-record scoping require a consistent review.
- Export/deletion coverage requires a collection inventory.
- Approval expense kind and duplicate action handling require correction.
- Timezone handling differs between frontend and backend.
- A JWT-shaped test artifact was removed from the working tree; review git history and revoke the associated test credential if it remains valid.
These are audit leads, not permission to assume a live production defect. Reproduce
and verify each issue before changing behaviour.

## Delivery gates
Each phase must include code review, automated tests, regression tests, migration
safety review and an explicit list of limitations. Keep main untouched until
the owner approves the completed changes.
