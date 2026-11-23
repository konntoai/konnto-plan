import sys
import asyncio
import logging
from contextlib import suppress
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402
from pymongo import ASCENDING, DESCENDING, IndexModel  # noqa: E402
import os  # noqa: E402

from core import db, client, remember_base, load_base  # noqa: E402

try:  # launched as `backend.server` (the default)
    from backend.clerk_auth import clerk_router, require_user  # noqa: F401
except ModuleNotFoundError:  # launched from inside backend/ as `server`
    from clerk_auth import clerk_router, require_user  # noqa: F401

import routes_app  # noqa: E402
import routes_team  # noqa: E402
import routes_admin  # noqa: E402
import routes_wa  # noqa: E402
import routes_cron  # noqa: E402
import routes_pcm  # noqa: E402
from storage import init_storage  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# One entry per collection: every field a route filters, sorts or dedupes on.
INDEXES: dict = {
    "users": [IndexModel([("user_id", ASCENDING)], name="user_id", unique=True), IndexModel([("whatsapp", ASCENDING)], name="whatsapp")],
    "orgs": [IndexModel([("org_id", ASCENDING)], name="org_id", unique=True, sparse=True)],
    "members": [IndexModel([("member_id", ASCENDING)], name="member_id", unique=True),
                IndexModel([("org_id", ASCENDING), ("status", ASCENDING)], name="org_status"),
                IndexModel([("user_id", ASCENDING)], name="user_id"), IndexModel([("phone", ASCENDING)], name="phone"),
                IndexModel([("invite_token", ASCENDING)], name="invite_token", sparse=True),
                IndexModel([("invite_code", ASCENDING)], name="invite_code", sparse=True)],
    "items": [IndexModel([("item_id", ASCENDING)], name="item_id", unique=True),
              IndexModel([("org_id", ASCENDING), ("status", ASCENDING), ("due_at", ASCENDING)], name="org_status_due"),
              IndexModel([("remind_at", ASCENDING), ("reminded_at", ASCENDING)], name="remind"),
              IndexModel([("depends_on", ASCENDING)], name="depends_on")],
    "brain_messages": [IndexModel([("msg_id", ASCENDING)], name="msg_id", unique=True),
                       IndexModel([("member_id", ASCENDING), ("created_at", DESCENDING)], name="member_created"),
                       IndexModel([("cards.card_id", ASCENDING)], name="card_id")],
    "threads": [IndexModel([("thread_id", ASCENDING)], name="thread_id", unique=True), IndexModel([("org_id", ASCENDING), ("member_ids", ASCENDING)], name="org_members")],
    "thread_messages": [IndexModel([("msg_id", ASCENDING)], name="msg_id", unique=True), IndexModel([("thread_id", ASCENDING), ("created_at", DESCENDING)], name="thread_created")],
    "approvals": [IndexModel([("approval_id", ASCENDING)], name="approval_id", unique=True), IndexModel([("org_id", ASCENDING), ("status", ASCENDING)], name="org_status")],
    "rules": [IndexModel([("rule_id", ASCENDING)], name="rule_id", unique=True), IndexModel([("org_id", ASCENDING), ("active", ASCENDING)], name="org_active")],
    "documents": [IndexModel([("doc_id", ASCENDING)], name="doc_id", unique=True), IndexModel([("org_id", ASCENDING), ("created_at", DESCENDING)], name="org_created")],
    "files": [IndexModel([("file_id", ASCENDING)], name="file_id", unique=True)],
    "knowledge": [IndexModel([("fact_id", ASCENDING)], name="fact_id", unique=True), IndexModel([("org_id", ASCENDING)], name="org")],
    "usage": [IndexModel([("org_id", ASCENDING), ("month", ASCENDING), ("feature", ASCENDING)], name="org_month_feature"), IndexModel([("created_at", ASCENDING)], name="created")],
    "outbox": [IndexModel([("wamid", ASCENDING)], name="wamid", sparse=True), IndexModel([("created_at", ASCENDING)], name="created")],
    "wa_events": [IndexModel([("event_id", ASCENDING)], name="event_id", unique=True)],
    "wa_contacts": [IndexModel([("wa_id", ASCENDING)], name="wa_id", unique=True)],
    "otp": [IndexModel([("phone", ASCENDING), ("created_at", DESCENDING)], name="phone_created")],
    "cron_runs": [IndexModel([("run_id", ASCENDING)], name="run_id", unique=True)],
    "briefs_sent": [IndexModel([("key", ASCENDING)], name="key", unique=True)],
    "pending_states": [IndexModel([("member_id", ASCENDING)], name="member_id", unique=True)],
    "feedback": [IndexModel([("created_at", DESCENDING)], name="created")],
    "projects": [IndexModel([("project_id", ASCENDING)], name="project_id", unique=True), IndexModel([("org_id", ASCENDING)], name="org")],
    "pcm_instructions": [IndexModel([("instruction_id", ASCENDING)], name="instruction_id", unique=True),
                         IndexModel([("org_id", ASCENDING), ("status", ASCENDING), ("updated_at", DESCENDING)], name="org_status_updated"),
                         IndexModel([("org_id", ASCENDING), ("assignee_id", ASCENDING), ("status", ASCENDING)], name="org_assignee_status"),
                         IndexModel([("status", ASCENDING), ("due_at", ASCENDING), ("followup_level", ASCENDING)], name="pcm_due_followup")],
}


async def ensure_indexes() -> None:
    for collection, models in INDEXES.items():
        for model in models:
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)


app = FastAPI(title="KONNTO AI")


@app.middleware("http")
async def track_base(request: Request, call_next):
    if request.url.path.startswith("/api"):
        try:
            await remember_base(request)
        except Exception:
            pass
    return await call_next(request)


@app.get("/api/")
async def root():
    return {"message": "KONNTO AI is running"}


app.include_router(clerk_router)
app.include_router(routes_app.router)
app.include_router(routes_team.router)
app.include_router(routes_admin.router)
app.include_router(routes_wa.router)
app.include_router(routes_cron.router)
app.include_router(routes_pcm.router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    app.state.index_task = asyncio.create_task(ensure_indexes())
    await load_base()
    try:
        await asyncio.get_event_loop().run_in_executor(None, init_storage)
        logger.info("Storage initialized")
    except Exception as e:
        logger.error("Storage init failed: %s", e)


@app.on_event("shutdown")
async def shutdown_db_client():
    app.state.index_task.cancel()
    with suppress(asyncio.CancelledError):
        await app.state.index_task
    client.close()
