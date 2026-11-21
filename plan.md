# KONNTO AI — Phase 1 MVP Plan (UPDATED)

## 1) Objectives

### Status update
- **Phase 1 MVP is complete.** Backend is implemented and verified; frontend is fully built and wired.
- **Testing:** Backend passed **24/24 tests (100%)**. Frontend smoke + navigation verification passed. Core integrations verified end-to-end.
- **Visual redesign (“AI feel”) is in progress.** The new design foundations are in place (tokens + dark/light toggle + brand components), and bulk page rewrites are underway.
- **Frontend compilation:** Latest redesign batch compiles cleanly (`npx esbuild src/ --bundle --outfile=/dev/null` ✅).

### Current objectives (post-MVP)
1. Keep Phase 1 MVP stable and production-ready.
2. Deliver the **premium, futuristic AI-native UI** (dark default + light mode toggle) across public + app + admin pages.
3. Upgrade KONNTO’s **conversation quality** to match the user’s previous K-BRAIN experience: decisive, context-aware, proactive but controlled, and capable of turning operational instructions into confirmable actions.

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
5. As an admin, I can edit Brain draft, test it, publish it, and see version history. ✅

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

### Phase 4 — Complete Visual Redesign (“AI feel”) 🔄 IN PROGRESS
A full **visual overhaul** across **all pages** (public + app + admin) to match the KONNTO brand and feel like a modern AI product.

**Brand inputs (provided by user)**
- Use KONNTO logo (royal blue gradient background, white wordmark, red chevron mark).
- **Logo asset URL (reference):**
  - https://customer-assets-lqy194kg.emergentagent.net/job_konnto-plan--87psd4r7/artifacts/fa88f4351d22efae_KONNTO%20Logo%20on%20Blue%20Gradient.png
- Recreate the mark as a **crisp SVG component** for all backgrounds and sizes.

**User choices**
- Theme support: **BOTH dark + light** with a **toggle**
  - Dark (default): midnight blue + soft blue glows
  - Light: white surfaces + royal blue highlights + red accents
- Motion: combine
  - **Subtle + premium** (default): gentle glows, soft pulsing KONNTO orb, smooth fades
  - **Bold + futuristic** (accent moments): animated gradient orb, shimmer borders, light trails
- Respect `prefers-reduced-motion`.

**Scope constraints**
- **Do not change any functionality.** Keep API wiring, behavior, routes, and `data-testid` attributes intact.
- Only visuals: design tokens, components, layout polish, animation, iconography and branding.

**User stories (Redesign)**
1. As a user, the product instantly feels like a premium AI assistant (not a generic SaaS dashboard).
2. As a user, I can switch between dark/light instantly, and the UI remains readable and accessible.
3. As a user with reduced-motion enabled, the app remains elegant without motion overload.
4. As a user, the Chat experience feels “alive” (AI presence) while other screens remain calm.

**Implementation steps**
1. **Design exploration** (design_agent) ✅
   - Extract brand palette from logo: primary royal blues + accent red + neutrals.
   - Define: background gradients, surface hierarchy, border treatments, typography rules.

2. **Token + theme system rebuild** ✅
   - Updated `index.css` + Tailwind CSS variables for Dark/Light palettes.
   - Ensured shadcn primitives inherit tokens.

3. **Theme Provider + Toggle** ✅
   - Added theme provider (via `next-themes`) and a topbar toggle.
   - Prevented FOUC by defaulting `<html class="dark">`.

4. **Brand components** ✅
   - Added `Logo.jsx` and `KonntoOrb.jsx` under `/app/frontend/src/components/brand/` and wired into core UI.

5. **Restyle layouts (no behavior changes)** 🔄
   - AppShell + Chat redesigned with glassmorphism + AI orb presence. ✅
   - Remaining pages being rewritten to new tokens/components. 🔄

6. **Motion system** ✅/🔄
   - Orb + streaming presence animations implemented.
   - Continue verifying motion consistency across pages; respect `prefers-reduced-motion`. 🔄

7. **Compile + screenshots + review** 🔄
   - Compilation check complete (esbuild) ✅
   - Pending: screenshot sweep across both themes for public/app/admin pages. 🔄

8. **Regression testing** 🔄
   - Pending: rerun `testing_agent_v3` after final page rewrites + screenshot sign-off. 🔄

---

### Phase 5 — “K-BRAIN Conversational Upgrade” ✅ COMPLETED (testing iteration_2: backend 11/11, frontend 7/7)
Upgrade KONNTO AI to speak and behave like the user’s previous K-BRAIN (chief-of-staff / CEO-level assistant vibe).

**Goal (from user reference screenshots/videos)**
KONNTO should:
- Address the user by first name when appropriate.
- Pull **live state** (pending approvals with amounts + who raised them; open work highlights).
- Prioritize with judgment (“what actually needs a decision from you today”).
- Be proactive but controlled: volunteer **1–2 extra signals that matter**.
- Close with a crisp next action (“tell me which ones to approve and I’ll queue them up”).
- Respond with **empathy** for personal situations.
- Turn operational instructions (handover/delegation/temporary restrictions) into a **confirmable ‘K-BRAIN PROPOSES’** card.

**User stories (Conversational upgrade)**
1. As an owner, when I ask “what needs my attention today?”, I get a prioritized, decision-oriented rundown (not generic advice).
2. As a user, I can choose a conversation style (Chief of Staff / Executive Assistant / Senior Advisor / Sharp Operator) and KONNTO adapts.
3. As a user, when I give an instruction like “Ask Priya to manage today, no financial decisions”, KONNTO drafts a message + a temporary rule and asks me to confirm.
4. As an owner, after I confirm, KONNTO actually sends the message, logs it, and enforces the temporary restriction until it expires.
5. As a user, I can reset/clean the chat session if needed without losing business data.

**Backend implementation (planned changes)**
1. **Personas**
   - Add a PERSONAS map in `backend/brain.py`.
   - Add a member-level persona setting (stored on member, default **Chief of Staff**).
   - Allow inline change via chat (interpreted as an action), and via explicit endpoint.

2. **Live-state reply system**
   - Extend `reply_system()` to include a **LIVE STATE** block:
     - Pending approvals summary (amounts + requester + short reason)
     - Open items highlights (overdue/due/stuck)
     - Rules currently in effect (especially temporary restrictions)
   - Preserve existing safety rules: never invent figures; cite sources when used; never claim something is completed.

3. **New analysis actions**
   - Extend analysis tool schema to support:
     - `set_persona` action
     - `handover` action (delegate authority for today; include restrictions like “no financial decisions”)

4. **Handover proposal card + lifecycle**
   - Add a new card type (e.g. `handover`) generated by engine:
     - Card shows drafted instruction + proposed restrictions + expiry.
     - Actions: **Confirm / Dismiss** (distinct from Save/Skip/Undo proposal cards).
   - On confirm:
     - Send message to the target person (via direct thread/in-app; WhatsApp/email fallback as applicable).
     - Create a temporary behaviour rule / restriction that **expires end of local day**.
     - Write an audit log entry.
   - On dismiss: no action taken.

5. **Temporary rule expiry**
   - Ensure expired rules are filtered out when applying behaviour rules.

6. **New routes**
   - Extend card ops to support confirm/dismiss for relevant cards.
   - Add `PUT /api/me/brain-persona` (or similar) to set persona.
   - Add `POST /api/chat/reset` to archive/soft-reset chat history for the current member.

7. **Seed updates for realistic “CEO assistant” responses**
   - Add a “cash on hand” fact into seed knowledge so the assistant can reference it (with citations) when giving sequencing advice.

**Frontend implementation (planned changes)**
1. **Shared chat engine**
   - Introduce `useBrainChat` hook to reuse streaming logic for:
     - `/app/chat`
     - floating K-BRAIN panel

2. **Floating K-BRAIN Panel**
   - A glassmorphism overlay panel available on every app page except `/app/chat`:
     - Collapsed pill composer
     - Expanded panel header: **“K-BRAIN · KONNTO INTELLIGENCE LAYER”**
     - Persona picker (dropdown)
     - Expand-to-full-page + minimize
     - Footer: **“POWERED BY K-BRAIN · KONNTO INTELLIGENCE”**
     - Reset button

3. **Card UI updates**
   - Extend `BrainCard` to render new `handover` card:
     - Amber tone
     - Confirm / Dismiss buttons

4. **Visual parity with reference**
   - Ensure chat typography + spacing supports “CEO brief” formatting:
     - clean bullets, tight hierarchy, strong readability on dark background.

**Testing + QA (Conversational upgrade)**
- Add backend tests covering:
  - persona persistence
  - handover card generation + confirm path
  - expiry filtering logic
- Add UI regression checks:
  - streaming still works
  - confirm/dismiss card actions work
  - floating panel works across routes and in both themes

---

## Phase 5 delivered
- brain.py: PERSONAS (chief_of_staff default, assistant, advisor, operator) + LIVE STATE reply prompt; analysis actions handover + set_persona (roles like "PCM" map to job titles).
- engine.py: live_state() (people, approvals w/ amounts+age, work buckets, instructions in effect, facts, recent team chat); handover card confirm/dismiss/undo (sends thread msg, temp rule w/ expires_at end of local day, activity_log + audit); expired rules filtered; INR Indian grouping.
- routes: PUT /api/me/brain-persona, POST /api/chat/reset (soft archive), card ops confirm/dismiss; /me returns brain_persona(s).
- seed: 3 approvals (₹42,000 / ₹8,500 / ₹6,800) + cash-on-hand demo fact.
- Frontend: BrainChatContext (shared conversation), KBrainPanel floating dock/panel on all app pages except /app/chat, BrainComposer, BrainMessages, PersonaSelect, HandoverCard + persona card.

## Phase 6 — K-BRAIN Master System Prompt ✅ IMPLEMENTED (testing pending in iteration_3)
- `backend/kbrain_prompt.py`: MASTER_PROMPT (verbatim user spec) + APP_OPERATING_NOTES; reply_system = master prompt + style overlay (4 personas kept, tone only) + admin guidance + TRUSTED SERVER CONTEXT (workspace, user, derived role, granted/denied scopes, real capabilities) + LIVE STATE + K-MEMORY + ACTIONS.
- Permissions enforced server-side: core.fact_scope_query (finance facts need money scope; partners see none), can_read_rules (partners none), engine.visible_people (partners see owner + inviter), item/doc scope queries, re-check at confirm time; /knowledge, /rules, /search scoped.
- Draft-first (user choice): message, rule (temporary/permanent + scope), fact, approval decision, status change, business profile, invite → "draft" cards; POST /chat/cards/{id}/confirm|dismiss; apply_draft executes + audits; undo where reversible; WhatsApp Confirm/Dismiss buttons.
- Memory: live_state adds projects, 14-day decisions, recent documents, activity log, facts with source/date; retrieve adds projects + past approvals; facts have category + confirmed; untrusted attachments wrapped in <untrusted_input>.
- Frontend: react-markdown + remark-gfm rendering (BrainMarkdown), source chips, DraftCard (Confirm/Dismiss), Undo links, delivery status on sent messages.
- Tests: /app/tests/kbrain_master.py, /app/tests/kbrain_permissions.py (team + partner prompt-injection: no leaks).

## 3) Next Actions (immediate)

### Phase 4 (Design) — P0
1. Finish rewriting remaining frontend pages to new AI-native theme tokens/components.
2. Run a full screenshot sweep (desktop + mobile) in **Dark** and **Light**:
   - Landing, Auth, Onboarding
   - App: Dashboard, Chat, Work, Team, Approvals, Documents, Knowledge, Settings, Privacy, Help
   - Admin: all admin pages
3. Fix visual issues: contrast, z-index layering (dialogs/popovers), responsive overflow.

### Phase 5 (Conversation) — P0
4. Implement K-BRAIN personas + persona picker (backend storage + frontend selector).
5. Implement live-state reply block (approvals + open work + rules).
6. Implement “handover / restriction” proposal card (confirm/dismiss) end-to-end.
7. Add `/chat/reset` and UI entry point (panel + chat page).

### Regression — P0
8. Run `testing_agent_v3` after Phase 4 + Phase 5 changes to ensure no functional regressions.

---

## 4) Success Criteria

### Phase 1 Success Criteria ✅ Met
- User can: sign up → onboard → chat with streaming reply → save a proposal → see it in Work → decide approvals → invite teammate (email fallback works) → send team message.
- WhatsApp briefs: UI and backend behave gracefully when WhatsApp is not configured; email/in-app flows remain functional.
- Admin console functional and wired: brain/site/plans/customers/usage/feedback/settings.
- Seeded demo org appears immediately for new owners.
- App routes are complete (no missing imports). Core interactive elements have `data-testid`.

### Phase 4 Success Criteria (Redesign) ✅ when complete
- Entire product (public + app + admin) uses the new KONNTO brand look.
- Dark + Light themes work everywhere with an easy toggle.
- Chat and AI-touchpoints feel alive (orb/glow/streaming) without making business screens noisy.
- `prefers-reduced-motion` is respected.
- No functional regressions: all tests and key flows still pass (chat streaming, cards, approvals, invites, work updates).

### Phase 5 Success Criteria (K-BRAIN Conversational Upgrade) ✅ when complete
- KONNTO consistently produces “chief-of-staff” style responses:
  - name-based addressing where appropriate
  - decision-first prioritization
  - 1–2 meaningful proactive signals
  - clear next step
- Persona can be changed per member (settings + inline), persists across sessions.
- Handover instructions produce a **confirmable** card and, on confirm, actually:
  - messages the right person
  - applies a temporary restriction with correct expiry
  - logs an audit event
- Floating K-BRAIN panel works on all app pages (dark/light) and does not break existing flows.
- No regressions in streaming, card actions, approvals, and work updates.

---

## Phase — Demo workspace + "what works / what doesn't" pass ✅ COMPLETED
- `/app/backend/demo_account.py`: demo business "Mehra Build Supplies" with 3 sign-ins (owner / team lead / supplier); 8 people, 4 projects, 22 work items (overdue, stuck, delayed, dependencies, private note, done, cancelled), 9 approvals (pending + all decision types), 5 rules, 9 facts (finance + partner-shared), 4 documents (1 private), 5 team chats, K-BRAIN history with saved/draft/handover cards and notice buttons. Dates pinned to fixed IST times. Rebuild: `python demo_account.py` or admin `POST /api/admin/demo/reset`. Demo org never sends email.
- Fixes found while using the demo: notice buttons now render & work in app chat (`POST /api/chat/actions` with msg_id, one answer only); Delayed/Need-help reason typed in app chat is captured; Today brief renders markdown; mobile brief overflow; partners no longer see all project names, the full staff list, or can open chats with arbitrary staff; open work/approvals are citable → source chips appear on live answers; inline [n] markers render as chips.
- Tested: iteration_3 (73/74 → fixed) and iteration_4 (100%).

## Phase — WhatsApp Go-Live (Status: IN PROGRESS — waiting for user's Meta keys)
- Built: Admin → Settings → WhatsApp panel (`AdminWhatsApp.jsx`): 9-step Meta setup guide, connection check (number name/quality, missing keys), one-tap "Send templates to Meta" (`wa_setup.submit_templates`, 7 templates incl. AUTH OTP), test send via Meta's hello_world; endpoints `/api/admin/whatsapp/{check,templates/submit,test}` (admin only).
- Team: owner/manager sets each person's WhatsApp number (`PATCH /members/{id}` phone; resets opt-in). Badge "WhatsApp · waiting" until the person messages KONNTO first → `wa_opt_in` set on first inbound (user's default choice).
- Demo people have NO made-up numbers anymore; real numbers added via Team survive `demo_account.py` rebuilds.
- Needed secrets: META_ACCESS_TOKEN, META_PHONE_NUMBER_ID, META_WABA_ID, META_APP_SECRET, META_DISPLAY_NUMBER (verify token + graph version already set). Webhook URL = <preview>/api/webhooks/whatsapp.
- Tested: iteration_5 (100%). After keys: check connection → submit templates → test send → each person sends "hi".
