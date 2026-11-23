# KONNTO AI v2 — Emergent implementation instructions

## Long-term product direction
KONNTO is a universal AI platform for individuals, businesses, professionals and
organisations. Design the shared identity, memory, intelligence, permission and
execution foundations to support these experiences without creating separate
applications or duplicate AI engines.

The first complete production-grade experience is KONNTO Business OS: K-BRAIN,
KONNTO Chat, PCM, K-Memory, backend-enforced authority and data-backed business
intelligence. Personal and Professional experiences are subsequent product phases.
KONNTO CENTRAL/global intelligence remains deferred until the foundation is proven.

## Mission
Upgrade the existing KONNTO AI application in this repository. Do not create a replacement app. Work only on the `konnto-v2-foundation` branch until reviewed. Keep `main` unchanged.

## Product truth
- K-BRAIN is the single shared intelligence engine.
- KONNTO Chat is the conversational workspace.
- KONNTO PCM is the AI-powered business coordination authority immediately below the owner, within backend-enforced delegated authority.
- K-Memory is structured, source-aware organisational knowledge.
- Existing Work, Team, Approvals, Documents and Knowledge modules remain the canonical records where suitable.
- Departmental intelligence are eight business domains powered by K-BRAIN, not eight separate AI models.
- The initial product is for one business workspace at a time. No KONNTO CENTRAL, global intelligence or multi-business portfolio layer now.
- WhatsApp, email, Tally, Zoho, banking and other external integrations are deferred. Do not claim they work or spend time connecting them.

## Non-negotiable safety rules
1. Do not deploy or merge to main.
2. Preserve existing working features and demo experience.
3. Demo seed data is intentional. Keep it available in demo mode, but make sure real customer onboarding never receives demo records.
4. Never delete customer data or perform destructive migrations without a reviewed migration and backup/rollback plan.
5. Do not expose, copy or commit credentials. The baseline contains a JWT-like test artifact under tests/.tmp; it has been removed from this branch and ignored. Check main/history and rotate/revoke the associated test session/credential if it is still valid.
6. Do not claim features work without running relevant tests.
7. Backend authorization, tenant isolation and approval checks are mandatory. Prompt text is not a security boundary.
8. Avoid broad refactors. Make small, reviewable commits with tests.

## Current prompt change
`backend/kbrain_prompt_v2.py` contains the upgraded K-BRAIN/PCM behavioural prompt. `backend/brain.py` has been changed on this branch to load it and no longer tells the model PCM does not exist. Review import paths, prompt construction and admin-config interactions before further work.

## Phase 0 — baseline (do this before coding)
- Inspect every tracked file, route, frontend page, model/collection, index, scheduled job, test and deployment config.
- Map current features to existing code and API endpoints.
- Verify which branch Emergent deploys and which environment is preview/live.
- Run current backend and frontend test suites; record baseline results.
- Review test_reports as historical evidence only.
- Reproduce each known audit lead below before fixing it.
- Produce a file-by-file change register: retain, fix, extend, add, deprecate.
- Report blockers and data migration risks.

## Known audit leads to verify
- Existing app has FastAPI, MongoDB, React and Clerk.
- Existing features include K-BRAIN chat, dashboard, tasks/projects, team, approvals, conversations, documents, business facts/rules, reminders, scheduled briefs and admin.
- The old prompt explicitly denied PCM existence; that contradiction is corrected on this branch for the reply prompt. Also inspect the separate analysis prompt and any admin-published prompt overrides.
- Voice transcript may not reach K-BRAIN context.
- Reminder and daily brief state may be marked before delivery succeeds.
- Cron work may be in-process and not durable across restart.
- Frontend SSE error event may not end the failed assistant stream cleanly.
- Cancelled voice recording may still upload captured chunks.
- Pending-state handling may consume unrelated user messages.
- Project/item and related-record visibility need consistent scoping.
- Export/deletion may omit organisation-linked collections.
- Approval expense type and concurrent duplicate actions need review.
- Frontend/backend timezone handling may differ.
- Temporary permission expiry and permission rollback need review.
- AI usage/cost accounting may omit some model calls.
- WhatsApp credentials and live delivery have not been verified; integration is deferred.

## Phase 1 — stabilise current product
Prioritise in this order:
1. Tenant isolation and all API/data visibility checks, including related/dependent records.
2. Organisation, project and assignee ownership validation.
3. Approval authorization, status transitions, idempotency and expense-kind correctness.
4. Demo-vs-real onboarding isolation while preserving demo.
5. Comprehensive privacy export/deletion inventory and implementation.
6. Voice transcript context and cancellation correctness.
7. SSE failure recovery.
8. Reliable reminder/brief delivery with retry-safe state transitions.
9. Durable scheduling/queue strategy appropriate to current deployment.
10. Pending-state handling and timezone consistency.
11. Permission expiry and safe rollback.
12. AI usage/cost accounting review.

Each item needs regression tests and a clear acceptance result.

## Phase 2 — K-BRAIN
- Keep one shared brain for Chat and PCM.
- Use trusted server context for organisation, role and permissions.
- Retrieve only relevant authorised business records.
- Improve source-aware, date-aware and confidence-aware analysis.
- Separate verified facts, user claims, inferences, drafts, approved policies and forecasts.
- Preserve memory provenance and allow authorised corrections.
- Never turn ordinary conversation into permanent policy without confirmation.
- Keep platform admin separate from business owner roles.
- Keep admin-published configuration from overriding safety, permissions or product truth.
- Ensure all actions use validated backend tools.

## Phase 3 — PCM core
Implement a dedicated PCM experience and real backend capability:
- Configurable organisation hierarchy and department ownership.
- Instruction records with unique ID, issuer, assignee, department, priority, due date, authority, status and audit history.
- Instruction lifecycle: draft, approval required, approved, assigned, sent, delivered (if supported), acknowledged, in progress, blocked, overdue, rejected, completed, evidence verified, closed or cancelled.
- Follow-up and explanation requests through supported in-app channels.
- Escalation rules based on urgency, delays and impact.
- Owner decision queue.
- Backend authority levels: independent, delegated within configured limits, owner approval.
- Explicitly reserve payments, bank transfers, loans, contracts, legal commitments, hiring/termination, compensation changes, major purchases and strategic commitments unless a specific approved workflow grants narrow authority.
- Link instructions to existing tasks/projects; do not create duplicate work records.
- Record actual action outcomes. Never claim an action happened without confirmed tool result.
- PCM is an AI system, not a human; disclose this in business communications.

Do not add an independent task engine if existing items/projects can be extended safely.

## Phase 4 — departments and coordination
Implement department metadata and ownership without requiring every small business to have eight formal departments. Use the eight domains: Sales, Marketing, Finance, Operations, HR/People, Systems/Technology, Leadership/Management, Expansion/Growth.
Connect shared objectives, tasks, dependencies and evidence.

## Phase 5 — business intelligence
Build data-backed assessments:
- Business Health.
- Owner Dependency.
- Expansion Readiness.
- Revenue leakage opportunities.
- Risk register.
- Scenario simulation.
- Reusable playbooks from confirmed outcomes.
- Proactive alerts only when scheduled jobs and data support them.
Scores require transparent formulas, coverage, period, source, confidence and missing-data disclosures. No fabricated scores or savings.

## Phase 6 — production readiness
- End-to-end tests for owner, director, manager, accountant, employee and external participant scopes.
- Cross-tenant isolation tests.
- Approval and action replay/concurrency tests.
- Data export/deletion tests.
- Failure/retry/restart tests.
- Voice, documents and chat streaming tests.
- Security review, dependency review, backup/restore and monitoring.
- Performance and AI cost controls.
- Pilot on a controlled business workspace before release.

## Required working method
For every change:
1. State the reproduced issue and root cause.
2. Identify exact files and data collections affected.
3. Implement the smallest safe change.
4. Add or update automated tests.
5. Run tests and show actual results.
6. Review tenant/security implications.
7. Document migration and rollback where relevant.
8. Commit to this branch with a focused message.

Do not mark a phase complete based on UI appearance or historical test reports. Provide a phase report with changed files, tests run, failures, remaining risks and next steps.
