# K-BRAIN branch workflow — initial implementation

## Goal
Keep one primary AI model and one shared K-BRAIN. Route each user request through
a specialised branch instruction profile so the same model changes its reasoning
lens, context and response workflow based on the task.

Branches are not separate agents, models, products or permission boundaries.

## Implemented in this change
- Added `backend/kbrain_workflow.py` with branch definitions, router instructions,
  branch-specific operating guidance and safe fallback behaviour.
- Extended the structured K-BRAIN analysis tool to return:
  - primary branch
  - subdomain
  - response mode
  - reasoning depth
  - whether clarification is materially necessary
- Added routing instructions to the analysis system prompt so task selection
  happens before the reply is generated.
- Added the selected branch guidance to the reply system prompt.
- Saved branch, subdomain, response mode and reasoning depth as metadata on the
  assistant message for future observability and evaluation.
- Kept the existing primary model configuration for the core chat/analysis flow.
  Commitment detection now uses that same primary model rather than a separate
  fast-model choice.
- Added unit tests for branch context construction and safe fallbacks.
- Added a first K-Memory provenance safeguard: confirmed chat facts record who supplied them, when, their source type, evidence classification, visibility and verification status.
- Made memory confirmation idempotent for exact duplicate active facts, and made retrieval expose provenance while preferring recently updated entries.

## Initial branches
- `general`: ordinary conversation and explanations.
- `business`: organisation operations, management, team, business records and PCM.
- `personal`: an individual's goals, routines and personal organisation.
- `professional`: independent professional work, clients and deliverables.
- `central`: market/network intelligence, with strict privacy and capability limits.
- `analyst`: evidence, calculations, comparisons and deeper reasoning.
- `communicator`: writing, messaging and communication strategy.

Business subdomains include sales, marketing, finance, operations, people,
technology, leadership, growth, projects, documents, customer service, research
and planning.

## Runtime flow (current evidence-first implementation)
1. Receive the user's message and authorised identity, role and organisation context.
2. Retrieve member-authorised business records and assemble the live-state snapshot.
3. Bound and escape the retrieved evidence packet; mark all business records and
   attachments as data, never as instructions or authority.
4. The primary model performs structured understanding using the current request
   plus the retrieved context, then selects a branch, subdomain, response mode and
   reasoning depth.
5. Server-side action handling validates permissions and current records before
   preparing drafts or processing narrowly scoped self-service requests.
6. The same primary model generates the response using the retrieved evidence,
   live state and selected branch guidance.
7. The message stores routing metadata for later evaluation.

The model may use retrieved context to understand the request and avoid duplicates,
but retrieved records, attachments and quoted content cannot authorise an action.
Only the current user's explicit message can do that.

Most business-changing actions remain confirmation-gated. The backend currently
submits three explicit self-service/request actions immediately: a non-approver's
approval request, a member's request for access they lack, and a user's own
conversation-persona change. These are limited by server-side checks and must
never be inferred from business records or attachments.

## Important limitations
- This is the first routing/workflow and memory-provenance layer, not a completed K-Memory redesign. It does not yet perform semantic conflict detection, policy lifecycle/version approval, retention workflows or cross-source verification.
- A `user_confirmed_fact` means the user confirmed that the entry should be stored; it is not independent verification of the underlying claim. Older records without metadata are labelled as legacy/unknown during retrieval.
- Personal, Professional and CENTRAL are instruction profiles only. Their future
  product features, data models and integrations are not claimed to exist.
- Branch selection does not grant access or authority. Existing backend permission
  checks remain authoritative.
- The primary model provider/configuration has not been replaced in this change.
- No production deployment, live customer test or full end-to-end model evaluation
  has been performed.
- Run backend tests and regression checks before preview/pilot deployment.


## Intelligent reasoning workflow (expanded)
The structured understanding stage also records the objective, constraints, known
facts, unknowns, dependencies, risks and recommended next step. These are model
generated hints, not trusted records. The reply stage is instructed to validate
them against the original message and trusted server context.

The reply stage follows a common operating protocol:
1. Understand the outcome and intent.
2. Contextualise using authorised live records and relevant memory.
3. Plan dependencies and decision points for multi-step work.
4. Check user authority and available tools.
5. Act only through real tools, or create drafts where confirmation is required.
6. Verify tool results before claiming completion.
7. Respond with relevant evidence, uncertainty and next step.

The protocol explicitly separates recommendations from approvals and drafts from
sent messages. It also prohibits fabricated metrics, permissions, integrations
and completion claims.

## Verification status
The branch includes focused unit tests for branch selection and structured
reasoning-context construction. The GitHub connector has not returned a CI run
for the latest commits; these tests and backend compilation still need to be run
in the repository's normal CI or development environment. The new memory write
and retrieval paths also require database-backed integration tests before pilot use.
