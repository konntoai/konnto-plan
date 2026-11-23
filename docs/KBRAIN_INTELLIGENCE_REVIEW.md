# K-BRAIN Intelligence Review and Target Plan

**Review branch:** `phase0-reliability-audit`  
**Reviewed baseline:** `konnto-v2-foundation` plus the current Phase 0 reliability work  
**Review type:** Static source review and product-direction review. No production database, customer workspace, live integrations, or deployed environment was inspected.

## 1. Product north star

KONNTO is not intended to be another business-management interface. K-BRAIN is the additional brain for a business: it should remember authorised business knowledge, understand how the organisation works, connect people/departments/work/decisions, identify important changes and risks, recommend the next best action, coordinate within delegated authority, verify outcomes, and improve from confirmed results.

The governing principle is **K-BRAIN checks; you decide**. The intended operating loop is:

Remember → Understand → Think → Check → Detect → Suggest → Ask → Act → Verify → Learn → Brief.

The owner retains authority. PCM is the coordination and accountability capability, not a human employee and not an unrestricted autonomous agent.

## 2. Current implementation: strengths

- Two-stage LLM flow: structured understanding/action extraction followed by a natural-language response.
- One shared model with branch/context profiles; code correctly avoids claiming branches are separate agents.
- Business context includes member role, visible people, work, approvals, rules, current PCM register, knowledge facts, projects, recent documents, activity and team messages.
- Retrieval searches work, documents, knowledge facts, projects, past approvals and team messages.
- Actions are mostly represented as draft cards with server-side permission checks at creation and confirmation.
- The system distinguishes drafts from executed actions and contains strong prompt-level truthfulness, privacy and capability boundaries.
- Current source includes a business-oriented master prompt with memory, diagnostics, risk, simulation, cross-department coordination and evidence standards.
- Organisation-scoped query helpers and several backend authority checks are already present.

These are a meaningful foundation. The problem is not that the current system has no intelligence; it is that the intelligence is not yet sufficiently grounded, measurable, persistent or reliable.

## 3. Gaps and risks to correct

### P0 — Make the brain's knowledge trustworthy

1. **K-Memory is currently a collection of facts plus retrieval, not yet a complete organisational memory system.** The live context takes the newest 25 knowledge facts, while query retrieval uses keyword matching and small fixed result limits. There is no demonstrated canonical business knowledge graph linking facts to sources, people, projects, decisions, policies, versions and outcomes.
2. **Memory lifecycle is incomplete.** The prompt describes confirmation, provenance, conflict handling and correction, but source-level implementation must enforce fact status, verification, supersession, expiry, ownership and deletion—not rely on instructions alone.
3. **The current analysis step sees a narrow snapshot.** It receives up to 40 open items, visible people, approvals and rules. Deeper historical, financial, customer, supplier and project context is only available if retrieval finds it. Keyword retrieval can miss relevant context and cannot reliably resolve synonyms, relationships or time periods.
4. **The system can sound certain when context is incomplete.** There is no demonstrated evidence coverage gate or calibrated confidence mechanism that prevents unsupported business health scores, diagnoses or forecasts.

### P0 — Make decisions and actions safe

5. **Action proposals are generated before retrieval and the full live-state snapshot.** In `run_brain`, analysis and `execute_actions` happen before `retrieve` and `live_state`. Therefore action extraction can lack context that the final reply later receives. This ordering should be redesigned so the brain gathers relevant context before proposing consequential actions.
6. **The analysis output is treated as a fairly direct action plan.** It needs deterministic validation against current records, policy, authority, duplicates, dependencies and state transitions before any card or side effect is created.
7. **Some requests have immediate server-side effects during analysis handling.** For example, a non-approver's approval request is created during `execute_actions`; this is intentional in the current flow but needs explicit, tested semantics and idempotency so retries cannot create duplicate requests.
8. **A title-only duplicate check is weak.** Similar work can have different wording, and unrelated work can share a title. Use stable intent/idempotency keys plus semantic duplicate warnings—not title equality as the sole control.
9. **The system needs a durable action lifecycle.** Distinguish proposed, awaiting approval, approved, queued, executing, executed, failed, cancelled, verified and reversed where applicable. Record actor, authority, policy, inputs, result and timestamps.

### P1 — Improve reasoning quality

10. **The two LLM calls do not yet form a verifiable reasoning pipeline.** The analysis output is not checked against an independent evidence/consistency validator before action creation. Add deterministic checks first; use a second model critique only for high-impact decisions where its value justifies cost.
11. **No demonstrated outcome-learning loop.** The product prompt says Learn, but the reviewed pipeline does not yet show a systematic process that compares recommendations with actual outcomes, captures owner corrections, and updates trusted memory or decision heuristics with provenance.
12. **Business diagnostics and health scores need a real data model.** Scores must be calculated from defined indicators, periods, data coverage and evidence; the LLM should explain the result, not invent the score.
13. **No explicit task/dependency planning layer.** The brain can extract individual items and see dependencies, but should build a plan graph for multi-step goals with blockers, responsible roles, due dates, approvals and verification criteria.
14. **Proactivity is not equivalent to intelligence.** Scheduled briefs and follow-ups exist, but monitoring should be driven by explicit signals, freshness, thresholds, severity, deduplication and a clear next action. Avoid noisy generic alerts.

### P1 — Reliability and privacy

15. The Phase 0 audit's PCM multi-write consistency, recovery and idempotency concerns remain relevant; do not treat the current atomic PCM instruction update as proof that the linked Work item and side effects are fully consistent.
16. Daily brief retry logic has been improved, but external-send crash windows still mean at-least-once delivery rather than exactly-once delivery.
17. Pending chat state can be consumed before the streamed response completes.
18. Voice upload can leave an unreferenced stored file if transcription fails.
19. Frontend SSE failure/retry handling, end-to-end integration tests, tenant isolation coverage, timezone boundaries and production configuration still need verification.
20. Historical credential exposure identified in the earlier audit requires rotation/revocation by the appropriate owner; this review did not perform those actions.

## 4. Target K-BRAIN architecture

Build one central K-BRAIN with explicit internal stages. Do not create multiple autonomous agents yet.

1. **Identity and authority context** — identify user, organisation, role, permissions, business constitution, active delegations and applicable policies. Backend access controls remain authoritative.
2. **Intent and outcome understanding** — identify desired outcome, request type, constraints, urgency, affected entities and whether the user is asking, informing, deciding or authorising.
3. **Context retrieval** — retrieve relevant current and historical facts, work, projects, documents, decisions, conversations and outcomes. Use keyword plus structured relationship retrieval; semantic retrieval may be added only with evaluation and access filtering.
4. **Evidence ledger** — attach source, author, timestamp, period, freshness, verification state and confidence to each material claim. Surface conflicts and missing data.
5. **Business model / relationship layer** — connect organisation, departments, people, roles, customers, suppliers, projects, assets, policies, work, decisions and financial/operational indicators. Start with entities already supported by the product; expand incrementally.
6. **Reasoning and planning** — analyse causes, dependencies, scenarios, risks, trade-offs and possible actions. Produce a structured plan with owners, prerequisites, deadlines and success criteria.
7. **Policy and authority gate** — deterministic server-side validation of access, delegated authority, approvals, spending limits, business rules, duplicate intent and current record state.
8. **Action orchestration** — create a durable proposal or execution job. Every action has an idempotency key, explicit status, actor, authority and auditable result.
9. **Verification** — check the resulting record or external confirmation. A task marked done is not automatically proof the real-world outcome occurred.
10. **Learning and memory maintenance** — capture corrections and outcomes; promote only confirmed information; version and supersede old facts; preserve provenance and retention rules.
11. **Briefing and monitoring** — deliver prioritised, evidence-backed insights with urgency, impact, confidence, owner and next action. Suppress duplicates and stale alerts.

## 5. Build sequence — improve the brain before expanding product scope

### Phase A — Establish a measurable baseline
- Inventory every K-BRAIN prompt, tool, retrieval source, action type and API permission.
- Create a golden evaluation set from realistic KONNTO scenarios: business questions, ambiguous instructions, commitments, owner decisions, team updates, supplier/customer cases, financial questions, cross-department dependencies, document extraction, privacy boundaries and prompt injection.
- Score intent accuracy, evidence correctness, memory retrieval, action correctness, permission safety, duplicate prevention, response usefulness, latency and cost.
- Keep representative expected outputs and regression tests in version control.

### Phase B — Correct pipeline ordering and validation
- Change the flow to understand → retrieve context → assemble live state/evidence → plan → validate → create draft/action → respond.
- Ensure the model cannot create actions from stale or incomplete context without an explicit uncertainty/clarification path.
- Validate every structured output against schemas and current database state.
- Make requests idempotent; separate draft creation from side effects.
- Preserve the current confirmation-first principle and backend authority checks.

### Phase C — K-Memory v2
- Define typed records for fact, policy, SOP, decision, commitment, entity, relationship and outcome.
- Store provenance, verification status, effective dates, expiry, supersession, visibility and sensitivity.
- Add correction and conflict workflows.
- Build hybrid retrieval with access filters applied before results reach the model.
- Never automatically promote an inference or chat statement into approved policy.

### Phase D — Business reasoning and plans
- Add structured business diagnostic indicators with formulas and evidence requirements.
- Add dependency-aware planning and project/department impact analysis.
- Add scenario modelling with explicit assumptions and sensitivity ranges.
- Generate recommendations that include evidence, impact, confidence, owner, authority, cost/time, risks and verification method.

### Phase E — Execution reliability and learning
- Durable action/outbox lifecycle, retries, reconciliation and idempotency.
- Verify action completion from records or connected systems.
- Capture user corrections and outcome feedback.
- Learn only from validated, authorised outcomes; keep human approval for policy and authority changes.

### Phase F — Monitoring, daily brief and controlled proactivity
- Define measurable signals and thresholds.
- Detect changes, exceptions, overdue dependencies and anomalies.
- Rank by impact, urgency, confidence and actionability.
- Deduplicate, expire and explain every alert.
- Make each brief actionable and traceable to evidence.

## 6. Architectural decisions

- Keep one central model and specialist context profiles for now; do not market profiles as independent agents.
- Do not add disconnected ERP modules before the core intelligence works across existing records.
- Keep the user-facing navigation focused on Inbox, Projects, Insights & Reports; intelligence should connect existing work rather than multiply modules.
- Preserve role-based access and strict separation of private personal context, organisation memory and external partner visibility.
- Keep the owner as final authority for high-impact business decisions.
- Do not claim continuous monitoring, integrations or execution unless the deployed capability is verified.
- Optimise model calls and retrieval for cost: deterministic code for policy, calculations and validation; reserve deeper model reasoning for complex/high-impact work.

## 7. Acceptance standard

K-BRAIN is not considered materially improved until it can pass tests showing that it:

- recalls the right current fact and cites its source;
- notices stale or contradictory information;
- refuses to invent financial or operational metrics;
- identifies root causes and dependencies rather than listing symptoms;
- proposes a coherent multi-step plan with owners and verification;
- never exceeds the current user's permissions or delegated authority;
- does not create duplicate tasks, approvals or messages on retries;
- accurately distinguishes draft, approved, executed, delivered, acknowledged, completed and verified;
- recovers safely from partial failures;
- learns from confirmed corrections without turning guesses into policy;
- gives useful, prioritised briefs without noisy false alarms;
- improves quality without unbounded model cost or unacceptable latency.

## 8. Scope and safety

This is a source-level plan. It does not certify production behaviour. All implementation remains isolated to `phase0-reliability-audit` until separately reviewed. No changes to `main`, no merge, no deployment, no Emergent workspace edits, and no production/customer data access are included in this review.
