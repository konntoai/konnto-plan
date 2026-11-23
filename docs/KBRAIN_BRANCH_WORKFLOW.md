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

## Runtime flow
1. Receive the user's message and authorised context.
2. The primary model performs structured understanding and selects a branch,
   subdomain, response mode and reasoning depth.
3. Existing server-side action validation creates only permitted draft/action cards.
4. Existing retrieval and live-state functions provide authorised records.
5. The same primary model generates the response under the selected branch guidance.
6. The message stores routing metadata for later evaluation.

## Important limitations
- This is the first routing/workflow layer, not a completed K-Memory redesign.
- Personal, Professional and CENTRAL are instruction profiles only. Their future
  product features, data models and integrations are not claimed to exist.
- Branch selection does not grant access or authority. Existing backend permission
  checks remain authoritative.
- The primary model provider/configuration has not been replaced in this change.
- No production deployment, live customer test or full end-to-end model evaluation
  has been performed.
- Run backend tests and regression checks before preview/pilot deployment.
