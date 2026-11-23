# Phase 0 Reliability and Security Audit

**Audit base:** `konnto-v2-foundation`  
**Audit branch:** `phase0-reliability-audit`  
**Status:** Static source review in progress; no production or database-backed verification performed.

## Scope inspected

- `backend/core.py`: authentication, organisation context, permissions, scoped query helpers, time helpers.
- `backend/routes_app.py`: chat streaming, uploads, file access, item listing and creation.
- `backend/routes_pcm.py`: PCM issue, progress and cancellation lifecycle.
- `backend/routes_cron.py`: reminder, late-work chase, PCM follow-up and daily brief jobs.
- `backend/engine.py`: work-item creation and shared work engine.
- `backend/brain.py`: K-BRAIN analysis/reply model configuration and prompt flow.
- `backend/clerk_auth.py`: Clerk token verification and proxy.
- `frontend/src/App.js`, `frontend/package.json`: route composition and available frontend scripts.
- `.github/workflows/quality.yml`: current CI checks.

## Confirmed source-level findings

### P0 — Security and release hygiene

1. **Public Git history contains credential-shaped historical material.** The earlier baseline identified a JWT-shaped test artifact and demo credentials in historical commit metadata. Removing current-tree files does not revoke credentials or erase historical exposure. Revoke/rotate any affected credentials and sessions. History rewriting is deliberately excluded from this branch.
2. **CORS and deployment configuration require live verification.** The source review did not establish the deployed allowed-origin configuration. Do not infer production safety from source defaults alone.
3. **Cross-tenant access requires systematic route coverage.** Shared helpers scope work, documents and facts, but a full endpoint-by-endpoint audit and adversarial integration tests have not yet been completed.

### P1 — Data consistency and retry safety

4. **Daily brief deduplication can suppress retries.** In `backend/routes_cron.py::send_briefs`, the `briefs_sent` key is inserted before the notification is sent. A later notification failure leaves the key present, and the same day's run skips that member. Redesign as a claim/delivery state machine with retryable failure state and an atomic lease. Preserve one successful delivery per member, brief type and local date.
5. **PCM creation is a multi-write workflow without a transaction/compensation path.** `backend/routes_pcm.py::create_instruction` creates the shared Work item before inserting the PCM instruction. If the second write fails, the Work item can be orphaned. Design an idempotent creation workflow or safe compensation, with an audit record and tests for failure between writes.
6. **PCM progress updates are also multi-write.** The instruction status/history, linked Work item status, notifications and audit log are separate operations. Concurrent updates or partial failures can make the two records disagree. Add conditional state transitions, idempotency and reconciliation tests before changing this flow.

### P1 — CI coverage

7. **CI does not build or test the frontend.** The workflow compiles Python and runs K-BRAIN/PCM policy tests only. The frontend declares `build` and `test` scripts in `frontend/package.json`, but no lockfile was found at the expected frontend paths during this audit. Do not add a non-reproducible dependency install; first establish the actual package manager and committed lockfile.
8. **No full application integration suite is currently evidenced.** Existing checks do not establish live MongoDB behaviour, auth, storage, channel delivery, end-to-end browser behaviour or deployment correctness.

### P2 — Lifecycle and UX reliability

9. **Voice upload can leave an unreferenced stored file on transcription failure.** `backend/routes_app.py::chat_upload` stores audio before transcription. On transcription exception it returns 502 but does not mark the stored file deleted or schedule cleanup. Add bounded cleanup and tests; do not delete files that may already be referenced.
10. **Pending chat state is consumed before the streamed operation finishes.** `backend/routes_app.py::chat_stream` calls `engine.pop_pending_state` before response generation. An interrupted request can consume a pending state without a completed reply. Add a claim/ack/release lifecycle and concurrency tests.
11. **SSE error handling needs a frontend trace.** Backend sends a terminal `error` event on generator exceptions. The matching frontend parser and cancellation/retry behaviour still need inspection and tests.
12. **Timezone behaviour needs boundary tests.** Server helpers normalise ISO datetimes and organisation timezones, but cron windows, local dates, daylight-saving transitions and frontend date entry require end-to-end coverage.

## Positive controls observed

- `get_ctx` rejects an explicitly requested organisation when the user has no active membership in it.
- Item, document and fact query helpers include organisation scoping.
- PCM checks issuer authority, reporting-line limits, active internal assignees and reserved authority classes on the backend.
- Chat file reads scope by organisation and restrict non-owner access to the uploader.
- Real onboarding does not seed demo data unless the demo flag is enabled.
- K-BRAIN structured actions are drafts; backend tools remain responsible for permission checks.

## Implementation plan and acceptance criteria

### A. Daily brief delivery retry safety
- Define unique delivery identity: member + brief kind + organisation-local date.
- Use atomic claim with lease expiry; only one worker may deliver at a time.
- Persist attempts and delivery result; failed/unknown outcomes must be retryable without concurrent duplicate sends.
- Mark complete only after at least one channel confirms delivery.
- Unit tests: initial success, failure then retry, stale lease recovery, concurrent claims, local-date boundary, separate morning/evening keys.

### B. PCM lifecycle consistency
- Add a stable idempotency key for instruction creation.
- Ensure retry returns the original instruction rather than creating a second Work item.
- Use conditional state transitions so closed instructions cannot be reopened by races.
- Keep linked Work status consistent; record and surface reconciliation failures.
- Tests: failure after Work creation, duplicate request, simultaneous completion/cancel, cross-org IDs, linked item missing, notification failure.

### C. Frontend and CI
- Identify the actual frontend package manager and lockfile location.
- Add deterministic dependency installation and frontend production build.
- Add frontend unit tests where the existing test suite supports them.
- Keep CI branch filters aligned with the eventual permanent `main` workflow only when the owner approves the branch transition.

### D. Security regression coverage
- Build an endpoint inventory and verify org/member scoping for each route.
- Test cross-org IDs, private item/document access, finance redaction, partner visibility, and role/scope boundaries.
- Verify live CORS, auth keys, webhook secrets, storage permissions and environment separation in the deployment environment.

## Explicitly not done

- No production database was accessed or mutated.
- No customer data was read.
- No secrets were printed, revoked or rotated by this audit.
- No git history was rewritten.
- No deployment or Emergent workspace changes were made.
- `main` was not modified.
- No claim is made that any issue has been reproduced in production.
