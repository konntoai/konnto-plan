# KONNTO AI — Phase 1 MVP Plan (UPDATED)

## 1) Objectives

### Status update
- **Phase 1 MVP is complete.** Backend is implemented and verified; frontend is fully built and wired.
- **Testing:** Backend passed **24/24 tests (100%)**. Frontend smoke + navigation verification passed. Core integrations verified end-to-end.

### Current objectives (post-MVP)
- Keep the Phase 1 MVP stable and production-ready.
- Ensure graceful behavior when WhatsApp is not configured (current environment uses placeholders): **in-app + email fallback** remain the primary channels.
- Optional: improve polish (UX hardening, optimistic UI, global search, deeper UI interaction tests) before broader rollout.

---

## 2) Implementation Steps

### Phase 1 — Core POC (isolation) ✅ COMPLETED
Core pieces (SSE streaming + uploads + card actions + approvals + invites/notifications) were proven in isolation.

**User stories (POC)**
1. As a user, I can send a message and see a streaming AI reply render progressively. ✅
2. As a user, I can upload a voice note/photo/PDF and see the extracted context used in the reply. ✅
3. As a user, I can tap **Save** on a proposal card and see it appear as a Work item. ✅
4. As an approver, I can receive an approval request and decide once/always/deny (and undo). ✅
5. As an owner, I can invite a teammate and the invite email is sent (or clearly fails with a reason). ✅ (email fallback when WhatsApp not configured)

**Completed steps**
1. Implemented SSE streaming parsing and integration patterns (backend + frontend). ✅
2. Implemented Python verification scripts and ran comprehensive backend coverage. ✅
   - Added test utilities under `/app/tests/`:
     - `/app/tests/backend_test.py`
     - `/app/tests/test_chat_stream.py`
     - `/app/tests/test_card_actions.py`
3. Fixed/verified payload shapes, SSE event sequences, and error handling until stable. ✅

---

### Phase 2 — V1 App Development (customer app + admin console) ✅ COMPLETED
Built the full UI in one pass using shadcn/ui and `/app/design_guidelines.md`.

**User stories (App V1)**
1. As a signed-in user, I land in Chat and can complete my work without navigating complex menus. ✅
2. As a user, I can view my Work list, filter by state, and update status with a reason when required. ✅
3. As an owner, I can manage Team members (invite, view access, remove) and start a direct thread. ✅
4. As an approver, I can review approvals quickly and respond with one tap (or in words). ✅
5. As an admin, I can edit Brain draft, test it, publish it, and see version history. ✅ (wired)

**Completed steps**
1. **Created all missing frontend files referenced in `App.js`** ✅
   - App shell:
     - `/app/frontend/src/components/AppShell.jsx` (responsive: bottom tabs on mobile, left rail on desktop)
   - App pages (12):
     - `/app/frontend/src/pages/app/Chat.jsx`
     - `/app/frontend/src/pages/app/Dashboard.jsx`
     - `/app/frontend/src/pages/app/Work.jsx`
     - `/app/frontend/src/pages/app/Team.jsx`
     - `/app/frontend/src/pages/app/Thread.jsx`
     - `/app/frontend/src/pages/app/Approvals.jsx`
     - `/app/frontend/src/pages/app/Documents.jsx`
     - `/app/frontend/src/pages/app/Knowledge.jsx`
     - `/app/frontend/src/pages/app/Settings.jsx`
     - `/app/frontend/src/pages/app/Privacy.jsx`
     - `/app/frontend/src/pages/app/Help.jsx`
   - Admin pages (6):
     - `/app/frontend/src/pages/admin/AdminLayout.jsx`
     - `/app/frontend/src/pages/admin/AdminBrain.jsx`
     - `/app/frontend/src/pages/admin/AdminSite.jsx`
     - `/app/frontend/src/pages/admin/AdminPlans.jsx`
     - `/app/frontend/src/pages/admin/AdminCustomers.jsx`
     - `/app/frontend/src/pages/admin/AdminFeedback.jsx`
     - `/app/frontend/src/pages/admin/AdminSettings.jsx`

2. **Chat page (highest priority)** ✅
   - History: `GET /api/chat/messages`
   - Uploads: `POST /api/chat/upload` (voice/image/doc)
   - Streaming: `POST /api/chat/stream` (SSE)
   - Proposal cards with **exactly 3 actions**: Save / Edit / Skip
   - Card actions wired: `POST /api/chat/cards/{card_id}/{save|skip|undo}`
   - Proposal card UI component:
     - `/app/frontend/src/components/cards/BrainCard.jsx`

3. **Dashboard page** ✅
   - `GET /api/dashboard` counters + lists (overdue/due/stuck/waiting/upcoming) + morning brief card.

4. **Work page** ✅
   - List + filters: `GET /api/items`
   - Detail sheet: `GET /api/items/{item_id}`
   - Status changes: `POST /api/items/{item_id}/status`
   - Edit: `PATCH /api/items/{item_id}`
   - Delete is a soft delete: `DELETE /api/items/{item_id}` sets `deleted: True`.

5. **Approvals page** ✅
   - `GET /api/approvals?status=pending|decided`
   - Decide: `POST /api/approvals/{approval_id}/decide`
   - Undo: `POST /api/approvals/{approval_id}/undo`
   - Decide-in-words: `POST /api/approvals/{approval_id}/reply`

6. **Team + Thread pages** ✅
   - Members: `GET /api/members`, invite `POST /api/members`, patch `PATCH /api/members/{id}`, remove `DELETE /api/members/{id}`
   - Threads: `GET /api/threads`, create `POST /api/threads`, messages `GET /api/threads/{id}/messages`, send `POST /api/threads/{id}/messages`

7. **Documents + Knowledge** ✅
   - Documents: upload/list/detail/download/delete wired to `/api/documents*`
   - Knowledge: `/api/knowledge` add/delete; Rules: `/api/rules` add/delete.

8. **Settings + Privacy + Help** ✅
   - Settings: `/api/me/profile`, `/api/org` (including briefs schedule)
   - Privacy: `/api/privacy/summary`, `/api/privacy/export`, `/api/privacy/delete`
   - Help: `/api/help/chat` (SSE) + feedback `/api/feedback`.

9. **Admin console** ✅
   - Brain: `/api/admin/brain` + test + publish + versions + restore
   - Site: `/api/admin/site` + restore
   - Plans: `/api/admin/plans` CRUD + `/api/admin/plan-settings`
   - Customers/usage: `/api/admin/customers`, `/api/admin/usage`
   - Feedback: `/api/admin/feedback`
   - Settings: `/api/admin/settings` (shows WA webhook URL + verify token)

10. **Demo seed** ✅
   - Implemented `/app/backend/seed.py` and wired into `POST /api/onboarding`.
   - Behavior: **new owners land in a populated workspace**:
     - 3 sample people: **Priya**, **Ramesh**, **Gupta Cement**
     - **8 work items** across states (overdue/due/stuck/done/open/promise/reminder/note)
     - **1 pending approval**
     - Direct thread with Priya (sample messages)
     - **3 knowledge facts**
     - A KONNTO **morning brief** in brain_messages
   - Seed is **idempotent** (runs only if org has no items).

11. **Notifications + WhatsApp fallbacks** ✅
   - WhatsApp is currently **not connected** (placeholder tokens): UI reflects this.
   - Backend notification flow works with **in-app notices + email fallback**.

12. Conclude Phase 2 with E2E run ✅
   - `testing_agent_v3` run completed; **backend 24/24 passed** and frontend pages verified.

---

### Phase 3 — Hardening + UX completeness (Optional polish)
This phase is now **optional** and focuses on usability and long-term stability.

**User stories (Hardening)**
1. As a user on poor network, I see clear retry states and never lose typed text.
2. As a user, I can undo a saved card action quickly (already supported; improve discoverability).
3. As a team member, I can see unread counts and last message previews (partially implemented; polish).
4. As an owner, I can understand why a person has specific access (already shown via access_reason; improve UI clarity).
5. As an admin, I can audit changes via version histories and usage charts (wired; enhance visualization).

**Next steps (optional)**
1. Add more optimistic UI updates where safe (work status, approvals decide, thread sends).
2. Add global search UI hooked to `GET /api/search`.
3. Add consistent toasts (sonner) coverage for all create/update/delete interactions.
4. Extend Playwright-based UI testing beyond page-load smoke tests:
   - Chat: Save/Edit/Undo proposal card
   - Work: status transitions requiring reason
   - Approvals: decide + undo + reply-in-words
   - Documents: upload + download
5. WhatsApp go-live checklist:
   - Provide real Meta credentials (verify token, graph version, phone number ID, app secret)
   - Validate template availability and message delivery
   - Validate morning/evening brief cron behavior

---

## 3) Next Actions (immediate)
1. **Optional**: Expand automated UI tests to cover interactions (not just navigation).
2. **Optional**: Implement Global Search UI (`/api/search`).
3. If WhatsApp should be live: add real Meta credentials and run WA validation tests (webhook, templates, outbound sends).
4. Prepare for pilot rollout: add basic monitoring/telemetry and verify monthly usage limits behavior.

---

## 4) Success Criteria

### Phase 1 Success Criteria ✅ Met
- User can: sign up → onboard → chat with streaming reply → save a proposal → see it in Work → decide approvals → invite teammate (email fallback works) → send team message.
- WhatsApp briefs: UI and backend behave gracefully when WhatsApp is not configured; email/in-app flows remain functional.
- Admin console functional and wired: brain/site/plans/customers/usage/feedback/settings.
- Seeded demo org appears immediately for new owners.
- App routes are complete (no missing imports). Core interactive elements have `data-testid`.

### Optional hardening success criteria (future)
- Reliable offline/poor-network behavior and better recovery UX.
- Interaction-level E2E tests cover all critical UI flows.
- WhatsApp credentials configured and verified end-to-end (webhook + templates + briefs).
