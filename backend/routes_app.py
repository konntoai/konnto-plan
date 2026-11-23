"""Customer app API: me, onboarding, chat (K-BRAIN), work, dashboard, approvals, rules, knowledge, documents, search, privacy."""
import json
import base64
import tempfile
import asyncio
from datetime import timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field

from core import (db, now, iso, parse_iso, new_id, current_user, get_ctx, has_scope, is_owner, item_scope_query, doc_scope_query,
                  redact_item, item_state, SCOPES, norm_phone, org_tz, fmt_local, audit, app_link,
                  fact_scope_query, fact_category, can_read_rules)
from channels import notify, add_notice, wa_send, wa_configured, send_email, email_html
from storage import put_object, get_object, extract_text, ext_of, DOC_TYPES, IMAGE_TYPES, AUDIO_TYPES, MAX_BYTES, APP_NAME
import brain
from kbrain_memory import build_user_confirmed_fact, build_fact_correction_metadata
from kbrain_action_policy import button_claim_query, button_claim_update, button_completion_update
import engine
import seed

router = APIRouter(prefix="/api")


def _sse(obj) -> str:
    return f"data: {json.dumps(obj, default=str)}\n\n"


SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


# ================================================================ me + onboarding
@router.get("/me")
async def me(user: dict = Depends(current_user)):
    members = await db.members.find({"user_id": user["user_id"], "status": "active"}, {"_id": 0}).to_list(50)
    orgs = {o["org_id"]: o for o in await db.orgs.find({"org_id": {"$in": [m["org_id"] for m in members]}, "deleted": {"$ne": True}}, {"_id": 0}).to_list(50)}
    members = [m for m in members if m["org_id"] in orgs]
    current = next((m for m in members if m["org_id"] == user.get("current_org_id")), members[0] if members else None)
    pending = await db.approvals.count_documents({"org_id": current["org_id"], "status": "pending"}) if current and has_scope(current, "approve") else 0
    return {
        "user": {k: user.get(k) for k in ("user_id", "name", "email", "role", "whatsapp", "image", "auth")},
        "is_admin": user.get("role") == "admin",
        "memberships": [{"org_id": m["org_id"], "org_name": orgs[m["org_id"]]["name"], "member_type": m["member_type"], "member_id": m["member_id"]} for m in members],
        "org": orgs.get(current["org_id"]) if current else None,
        "member": current,
        "needs_onboarding": not current,
        "pending_approvals": pending,
        "whatsapp_connected": wa_configured(),
        "scopes": SCOPES,
        "brain_persona": (current or {}).get("brain_persona") or brain.DEFAULT_PERSONA,
        "brain_personas": [{"id": k, "label": v["label"]} for k, v in brain.PERSONAS.items()],
    }


class OnboardIn(BaseModel):
    whatsapp: str
    consent: bool = True
    timezone: Optional[str] = None
    name: Optional[str] = None


@router.post("/onboarding")
async def onboarding(body: OnboardIn, user: dict = Depends(current_user)):
    existing = await db.members.find_one({"user_id": user["user_id"], "status": "active", "member_type": "owner"}, {"_id": 0})
    if existing:
        return {"ok": True, "org_id": existing["org_id"]}
    phone = norm_phone(body.whatsapp)
    if len(phone) < 8:
        raise HTTPException(400, "Please enter a full WhatsApp number with country code.")
    country, currency, tz = engine.guess_country(phone)
    if body.timezone:
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(body.timezone)
            tz = body.timezone
        except Exception:
            pass
    name = (body.name or user.get("name") or "").strip() or "there"
    if body.name and body.name.strip() and body.name.strip() != user.get("name"):
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"name": body.name.strip()}})
    first = name.split()[0]
    org = {"org_id": new_id("org"), "name": f"{first}'s business", "industry": None, "description": None, "country": country,
           "currency": currency, "timezone": tz, "owner_user_id": user["user_id"], "created_at": iso(), "profile_learned": False,
           "briefs": {"enabled": True, "morning_hour": 8, "evening_hour": 19}, "limits": {}}
    await db.orgs.insert_one(dict(org))
    member = {"member_id": new_id("mem"), "org_id": org["org_id"], "user_id": user["user_id"], "name": name, "job": "Owner",
              "member_type": "owner", "phone": phone, "email": user.get("email"), "access": list(SCOPES.keys()), "status": "active",
              "wa_opt_in": bool(body.consent), "wa_opt_in_at": iso() if body.consent else None, "wa_opt_in_source": "signup",
              "created_at": iso(), "joined_at": iso(), "joined_via": "signup", "manager_id": None}
    await db.members.insert_one(dict(member))
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"whatsapp": phone, "current_org_id": org["org_id"]}})
    cfg = await brain.get_brain_config()
    welcome = (cfg.get("welcome_message") or brain.DEFAULT_BRAIN["welcome_message"]).replace("{name}", first)
    await add_notice(org["org_id"], member, welcome, kind="welcome")
    rec = None
    if body.consent:
        rec = await wa_send(to_phone=phone, text=welcome, template="konnto_welcome", params=[first, "your business"], org_id=org["org_id"],
                            member_id=member["member_id"], kind="welcome", force_template=True)
    if (not rec or rec["status"] != "sent") and user.get("email"):
        await send_email(to=user["email"], subject="Welcome to KONNTO AI", html=email_html(
            f"Welcome, {first}", ["KONNTO is ready. Tell it anything about your business — a task, a promise, a reminder or a question.",
                                  "Once KONNTO's WhatsApp is live for you, you can simply chat there too."], "Open KONNTO", app_link("/app/chat")))
    await audit(org["org_id"], member["member_id"], "org_created", {})
    # Demo fixtures are opt-in. Real customer workspaces start clean by default.
    if seed.demo_seed_enabled():
        try:
            await seed.seed_demo_org(org, member)
        except Exception as e:
            engine.logger.exception("demo seed failed: %s", e)
    return {"ok": True, "org_id": org["org_id"], "whatsapp_welcome": (rec or {}).get("status")}


class ProfileIn(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    wa_opt_in: Optional[bool] = None
    email: Optional[str] = None


@router.put("/me/profile")
async def update_profile(body: ProfileIn, ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    upd = {}
    if body.name:
        upd["name"] = body.name.strip()[:80]
        await db.users.update_one({"user_id": ctx["user"]["user_id"]}, {"$set": {"name": upd["name"]}})
    if body.phone is not None:
        upd["phone"] = norm_phone(body.phone) or None
    if body.wa_opt_in is not None:
        upd["wa_opt_in"] = body.wa_opt_in
        upd["wa_opt_in_at" if body.wa_opt_in else "wa_opt_out_at"] = iso()
        upd["wa_opt_in_source"] = "settings"
    if body.email is not None:
        upd["email"] = body.email.strip().lower() or None
    if upd:
        await db.members.update_one({"member_id": m["member_id"]}, {"$set": upd})
    return await db.members.find_one({"member_id": m["member_id"]}, {"_id": 0})


class PersonaIn(BaseModel):
    persona: str


@router.put("/me/brain-persona")
async def set_brain_persona(body: PersonaIn, ctx: dict = Depends(get_ctx)):
    if body.persona not in brain.PERSONAS:
        raise HTTPException(400, "Unknown style")
    await db.members.update_one({"member_id": ctx["member"]["member_id"]}, {"$set": {"brain_persona": body.persona}})
    return {"ok": True, "brain_persona": body.persona, "label": brain.PERSONAS[body.persona]["label"]}


class SwitchIn(BaseModel):
    org_id: str


@router.post("/me/switch-org")
async def switch_org(body: SwitchIn, user: dict = Depends(current_user)):
    m = await db.members.find_one({"user_id": user["user_id"], "org_id": body.org_id, "status": "active"})
    if not m:
        raise HTTPException(404, "Not found")
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"current_org_id": body.org_id}})
    return {"ok": True}


# ================================================================ org settings
class OrgIn(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    briefs_enabled: Optional[bool] = None
    morning_hour: Optional[int] = Field(None, ge=0, le=23)
    evening_hour: Optional[int] = Field(None, ge=0, le=23)


@router.get("/org")
async def get_org(ctx: dict = Depends(get_ctx)):
    return ctx["org"]


@router.put("/org")
async def update_org(body: OrgIn, ctx: dict = Depends(get_ctx)):
    if not is_owner(ctx["member"]):
        raise HTTPException(403, "Only the owner can change business settings")
    upd = {k: v for k, v in body.model_dump().items() if v is not None and k in ("name", "industry", "description", "country", "currency", "timezone")}
    if "timezone" in upd:
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(upd["timezone"])
        except Exception:
            raise HTTPException(400, "Unknown timezone")
    if body.briefs_enabled is not None:
        upd["briefs.enabled"] = body.briefs_enabled
    if body.morning_hour is not None:
        upd["briefs.morning_hour"] = body.morning_hour
    if body.evening_hour is not None:
        upd["briefs.evening_hour"] = body.evening_hour
    if upd:
        await db.orgs.update_one({"org_id": ctx["org"]["org_id"]}, {"$set": upd})
    return await db.orgs.find_one({"org_id": ctx["org"]["org_id"]}, {"_id": 0})


# ================================================================ chat with KONNTO
@router.get("/chat/messages")
async def chat_messages(before: Optional[str] = None, limit: int = Query(60, le=200), ctx: dict = Depends(get_ctx)):
    q = {"org_id": ctx["org"]["org_id"], "member_id": ctx["member"]["member_id"], "archived": {"$ne": True}}
    if before:
        q["created_at"] = {"$lt": before}
    msgs = await db.brain_messages.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)
    msgs.reverse()
    return {"messages": msgs}


@router.post("/chat/reset")
async def chat_reset(ctx: dict = Depends(get_ctx)):
    """Start a fresh conversation. Old messages are archived (kept), business data is untouched."""
    r = await db.brain_messages.update_many({"org_id": ctx["org"]["org_id"], "member_id": ctx["member"]["member_id"], "archived": {"$ne": True}},
                                            {"$set": {"archived": True, "archived_at": iso()}})
    return {"ok": True, "archived": r.modified_count}


class Attachment(BaseModel):
    type: str
    file_id: Optional[str] = None
    doc_id: Optional[str] = None
    filename: Optional[str] = None
    description: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None


class ChatIn(BaseModel):
    text: str = ""
    attachments: List[Attachment] = []


def _attachment_context(atts: list) -> str:
    parts = []
    for a in atts:
        if a.get("type") == "image" and a.get("description"):
            parts.append(f"[Photo sent] {a['description']}")
        elif a.get("type") == "document":
            parts.append(f"[Document '{a.get('filename')}' uploaded] {a.get('summary') or ''}")
        elif a.get("type") == "audio" and a.get("transcript"):
            # Include the actual transcription so K-BRAIN can understand the voice note.
            parts.append(f"[Voice note transcript] {a['transcript']}")
    return "\n".join(parts)


@router.post("/chat/stream")
async def chat_stream(body: ChatIn, ctx: dict = Depends(get_ctx)):
    atts = [a.model_dump() for a in body.attachments]
    text = body.text.strip()
    if not text and not atts:
        raise HTTPException(400, "Say something first")
    if not text:
        text = "(sent an attachment)"
    extra = _attachment_context(atts)

    state = await engine.pop_pending_state(ctx["member"]) if not atts else None

    async def gen():
        try:
            if state:  # the person is answering a question KONNTO just asked (delay reason, "always allow" amount ...)
                reply = await engine.handle_pending_reply(ctx["org"], ctx["member"], state, text, via="app")
                u, a = await _chat_pair(ctx["org"], ctx["member"], text, reply)
                yield _sse({"type": "user", "message": u})
                yield _sse({"type": "cards", "cards": []})
                yield _sse({"type": "delta", "text": reply})
                yield _sse({"type": "done", "message": a})
                return
            async for ev in engine.run_brain(ctx["org"], ctx["member"], text, channel="app", attachments=atts, extra_context=extra):
                yield _sse(ev)
        except Exception as e:
            engine.logger.exception("chat stream failed: %s", e)
            yield _sse({"type": "error", "message": "Something went wrong. Please try again."})

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/chat/upload")
async def chat_upload(file: UploadFile = File(...), ctx: dict = Depends(get_ctx)):
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File is too large (max 20 MB)")
    name = file.filename or "file"
    ext = ext_of(name)
    ctype = (file.content_type or "").split(";")[0]
    org, member = ctx["org"], ctx["member"]
    if ext in AUDIO_TYPES or ctype.startswith("audio/"):
        if ext not in AUDIO_TYPES:
            ext = "webm"
        rec = await _store_file(org, member, data, f"voice.{ext}", AUDIO_TYPES.get(ext, "audio/webm"), "audio")
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=True) as tmp:
            tmp.write(data)
            tmp.flush()
            try:
                transcript = await brain.transcribe_audio(org["org_id"], tmp.name)
            except Exception as e:
                engine.logger.error("transcribe failed: %s", e)
                raise HTTPException(502, "Couldn't understand the voice note. Please try again.")
        return {"type": "audio", "file_id": rec["file_id"], "transcript": transcript}
    if ext in IMAGE_TYPES or ctype.startswith("image/"):
        rec = await _store_file(org, member, data, name, IMAGE_TYPES.get(ext, ctype or "image/jpeg"), "image")
        desc = await brain.describe_image(org, base64.b64encode(data).decode())
        await db.files.update_one({"file_id": rec["file_id"]}, {"$set": {"description": desc}})
        return {"type": "image", "file_id": rec["file_id"], "description": desc, "filename": name}
    if ext in DOC_TYPES:
        doc = await create_document(org, member, data, name, "org")
        return {"type": "document", "doc_id": doc["doc_id"], "filename": name, "summary": doc.get("summary", "")}
    raise HTTPException(415, "Please send a photo, voice note, PDF, Word, Excel, CSV or text file.")


async def _store_file(org, member, data: bytes, filename: str, ctype: str, kind: str) -> dict:
    ext = ext_of(filename) or "bin"
    path = f"{APP_NAME}/{org['org_id']}/{kind}/{new_id('f')}.{ext}"
    try:
        result = await put_object(path, data, ctype)
    except Exception as e:
        engine.logger.error("storage put failed: %s", e)
        raise HTTPException(502, "Couldn't store the file. Please try again.")
    rec = {"file_id": new_id("fil"), "org_id": org["org_id"], "member_id": member["member_id"], "storage_path": result["path"],
           "content_type": ctype, "size": len(data), "kind": kind, "filename": filename, "is_deleted": False, "created_at": iso()}
    await db.files.insert_one(dict(rec))
    rec.pop("_id", None)
    return rec


@router.get("/files/{file_id}")
async def get_file(file_id: str, ctx: dict = Depends(get_ctx)):
    rec = await db.files.find_one({"file_id": file_id, "org_id": ctx["org"]["org_id"], "is_deleted": False}, {"_id": 0})
    if not rec or (rec["member_id"] != ctx["member"]["member_id"] and not is_owner(ctx["member"])):
        raise HTTPException(404, "Not found")
    data, _ = await get_object(rec["storage_path"])
    return Response(content=data, media_type=rec["content_type"])


class CardIn(BaseModel):
    edits: Optional[dict] = None


@router.post("/chat/cards/{card_id}/{op}")
async def chat_card(card_id: str, op: str, body: CardIn = CardIn(), ctx: dict = Depends(get_ctx)):
    if op not in ("save", "skip", "undo", "confirm", "dismiss"):
        raise HTTPException(400, "Unknown action")
    res = await engine.card_action(ctx["org"], ctx["member"], card_id, op, body.edits)
    if res.get("error") == "not_found":
        raise HTTPException(404, "Not found")
    if res.get("error"):
        raise HTTPException(403, res.get("message") or "Not allowed")
    return res


class ActionIn(BaseModel):
    action_id: str
    msg_id: Optional[str] = None
    label: Optional[str] = None


async def _chat_pair(org: dict, member: dict, user_text: str, reply: str, kind: str = "message") -> tuple:
    """Store a tap/reply + KONNTO's answer in the member's chat so the history matches what happened."""
    u = {"msg_id": new_id("bm"), "org_id": org["org_id"], "member_id": member["member_id"], "role": "user", "kind": kind,
         "text": user_text, "channel": "app", "attachments": [], "created_at": iso()}
    a = {"msg_id": new_id("bm"), "org_id": org["org_id"], "member_id": member["member_id"], "role": "assistant", "kind": "message",
         "text": reply, "cards": [], "citations": [], "channel": "app", "reply_to": u["msg_id"], "created_at": iso()}
    await db.brain_messages.insert_many([dict(u), dict(a)])
    return u, a


@router.post("/chat/actions")
async def chat_action(body: ActionIn, ctx: dict = Depends(get_ctx)):
    org, m = ctx["org"], ctx["member"]
    claimed = False
    if body.msg_id:
        # Claim the button before executing it. The old read-then-write sequence
        # allowed two concurrent taps to pass the check and execute the same action.
        claim = await db.brain_messages.update_one(
            button_claim_query(body.msg_id, m["member_id"], body.action_id),
            button_claim_update(body.action_id, body.label, iso()),
        )
        if not getattr(claim, "modified_count", 0):
            src = await db.brain_messages.find_one(
                {"msg_id": body.msg_id, "member_id": m["member_id"]},
                {"_id": 0, "buttons": 1, "buttons_used": 1, "button_action_status": 1},
            )
            if not src or not any(b.get("id") == body.action_id for b in (src.get("buttons") or [])):
                raise HTTPException(404, "That button is no longer available")
            raise HTTPException(409, "This action has already been claimed or completed")
        claimed = True
    try:
        text = await engine.handle_button(org, m, body.action_id, via="app")
        if claimed:
            await db.brain_messages.update_one(
                {"msg_id": body.msg_id, "member_id": m["member_id"], "buttons_used": body.action_id},
                button_completion_update(text, iso()),
            )
    except Exception:
        # Keep the claim. Releasing it here would permit a retry to repeat a
        # side effect that may already have succeeded before the exception.
        if claimed:
            await db.brain_messages.update_one(
                {"msg_id": body.msg_id, "member_id": m["member_id"], "buttons_used": body.action_id},
                {"$set": {"button_action_status": "needs_review", "button_action_error_at": iso()}},
            )
        raise
    u, a = await _chat_pair(org, m, body.label or body.action_id.split(":")[0], text, kind="button")
    return {"text": text, "user_message": u, "message": a}


# ================================================================ work items
def _present(item: dict, member: dict) -> dict:
    item = redact_item(item, member)
    item["state"] = item_state(item)
    return item


@router.get("/items")
async def list_items(kind: Optional[str] = None, state: Optional[str] = None, q: Optional[str] = None, project_id: Optional[str] = None,
                     mine: bool = False, ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    query = item_scope_query(m)
    if kind and kind != "all":
        query["kind"] = kind
    if project_id:
        query["project_id"] = project_id
    if mine:
        query["assignee_id"] = m["member_id"]
    if q:
        import re
        query["title"] = {"$regex": re.escape(q), "$options": "i"}
    items = await db.items.find(query, {"_id": 0, "history": 0}).sort([("status", 1), ("due_at", 1)]).to_list(500)
    items = [_present(i, m) for i in items]
    if state and state != "all":
        if state == "active":
            items = [i for i in items if i["state"] not in ("done", "cancelled")]
        else:
            items = [i for i in items if i["state"] == state]
    order = {"overdue": 0, "due": 1, "stuck": 2, "open": 3, "done": 4, "cancelled": 5}
    items.sort(key=lambda i: (order.get(i["state"], 9), i.get("due_at") or "9999"))
    projects = await db.projects.find({"org_id": ctx["org"]["org_id"]}, {"_id": 0}).to_list(200)
    return {"items": items, "projects": projects}


class ItemIn(BaseModel):
    kind: str = "task"
    title: str
    details: Optional[str] = ""
    assignee_id: Optional[str] = None
    due_at: Optional[str] = None
    remind_at: Optional[str] = None
    depends_on: List[str] = []
    project_id: Optional[str] = None
    project: Optional[str] = None
    counterparty: Optional[str] = None
    amount: Optional[float] = None
    is_request: bool = False
    private: bool = False


@router.post("/items")
async def create_item(body: ItemIn, ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    if body.assignee_id and body.assignee_id != m["member_id"]:
        target = await db.members.find_one({"member_id": body.assignee_id, "org_id": ctx["org"]["org_id"], "status": {"$in": ["active", "invited"]}})
        if not target:
            raise HTTPException(404, "Person not found")
    data = body.model_dump()
    data["due_at_utc"] = iso(parse_iso(body.due_at)) if body.due_at else None
    data["remind_at_utc"] = iso(parse_iso(body.remind_at)) if body.remind_at else None
    data.pop("due_at")
    data.pop("remind_at")
    item = await engine.create_item(ctx["org"], m, data, source={"type": "app"})
    return _present(item, m)


@router.get("/items/{item_id}")
async def get_item(item_id: str, ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    item = await engine.get_item_for(m, item_id)
    if not item:
        raise HTTPException(404, "Not found")
    deps = await db.items.find({"item_id": {"$in": item.get("depends_on") or []}, "org_id": m["org_id"]}, {"_id": 0, "item_id": 1, "title": 1, "status": 1, "assignee_name": 1}).to_list(20)
    dependents = await db.items.find({"depends_on": item_id, "org_id": m["org_id"], "deleted": {"$ne": True}}, {"_id": 0, "item_id": 1, "title": 1, "status": 1, "assignee_name": 1}).to_list(20)
    project = await db.projects.find_one({"project_id": item.get("project_id")}, {"_id": 0}) if item.get("project_id") else None
    out = _present(item, m)
    out.update({"depends_on_items": deps, "dependents": dependents, "project": project, "can_edit": engine.can_edit_item(m, item)})
    src = item.get("source") or {}
    if src.get("type") in ("app", "chat") and src.get("msg_id"):
        out["source_link"] = "/app/chat"
    elif src.get("thread_id"):
        out["source_link"] = f"/app/team/thread/{src['thread_id']}"
    elif src.get("doc_id"):
        out["source_link"] = f"/app/documents?doc={src['doc_id']}"
    return out


class ItemPatch(BaseModel):
    title: Optional[str] = None
    details: Optional[str] = None
    assignee_id: Optional[str] = None
    due_at: Optional[str] = None
    remind_at: Optional[str] = None
    depends_on: Optional[List[str]] = None
    project_id: Optional[str] = None
    kind: Optional[str] = None


@router.patch("/items/{item_id}")
async def patch_item(item_id: str, body: ItemPatch, ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    item = await engine.get_item_for(m, item_id)
    if not item or not engine.can_edit_item(m, item):
        raise HTTPException(404, "Not found")
    upd = {}
    changes = []
    if body.title:
        upd["title"] = body.title.strip()[:160]
        changes.append("title")
    if body.details is not None:
        upd["details"] = body.details[:2000]
    if body.kind in ("task", "promise", "reminder", "decision", "note"):
        upd["kind"] = body.kind
    if body.due_at is not None:
        upd["due_at"] = iso(parse_iso(body.due_at)) if body.due_at else None
        upd["chase_level"] = 0
        changes.append(f"due {fmt_local(upd['due_at'], ctx['org']) or 'cleared'}")
    if body.remind_at is not None:
        upd["remind_at"] = iso(parse_iso(body.remind_at)) if body.remind_at else None
        upd["reminded_at"] = None
    if body.depends_on is not None:
        upd["depends_on"] = [d for d in body.depends_on if d != item_id]
    if body.project_id is not None:
        upd["project_id"] = body.project_id or None
    new_assignee = None
    if body.assignee_id and body.assignee_id != item.get("assignee_id"):
        new_assignee = await db.members.find_one({"member_id": body.assignee_id, "org_id": m["org_id"], "status": {"$in": ["active", "invited"]}}, {"_id": 0})
        if not new_assignee:
            raise HTTPException(404, "Person not found")
        upd.update({"assignee_id": new_assignee["member_id"], "assignee_name": new_assignee["name"]})
        changes.append(f"assigned to {new_assignee['name']}")
    upd["updated_at"] = iso()
    await db.items.update_one({"item_id": item_id}, {"$set": upd, "$push": {"history": engine._hist(m["name"], "Edited: " + (", ".join(changes) or "details"))}})
    item = await db.items.find_one({"item_id": item_id}, {"_id": 0})
    if new_assignee and new_assignee["member_id"] != m["member_id"]:
        await engine.deliver_task(ctx["org"], m, new_assignee, item)
    return _present(item, m)


class StatusIn(BaseModel):
    status: str
    reason: Optional[str] = None
    new_due_at: Optional[str] = None


@router.post("/items/{item_id}/status")
async def item_status(item_id: str, body: StatusIn, ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    if body.status not in ("done", "in_progress", "delayed", "stuck", "open", "cancelled"):
        raise HTTPException(400, "Unknown status")
    if body.status in ("delayed", "stuck") and not (body.reason or "").strip():
        raise HTTPException(400, "Please give a quick reason")
    item = await engine.get_item_for(m, item_id)
    if not item or not engine.can_edit_item(m, item):
        raise HTTPException(404, "Not found")
    new_due = iso(parse_iso(body.new_due_at)) if body.new_due_at else None
    res = await engine.set_item_status(ctx["org"], m, item, body.status, body.reason, new_due)
    return _present(res["item"], m)


@router.delete("/items/{item_id}")
async def delete_item(item_id: str, ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    item = await engine.get_item_for(m, item_id)
    if not item or not (is_owner(m) or item.get("created_by") == m["member_id"]):
        raise HTTPException(404, "Not found")
    await db.items.update_one({"item_id": item_id}, {"$set": {"deleted": True, "updated_at": iso()}})
    return {"ok": True}


class ProjectIn(BaseModel):
    name: str
    description: Optional[str] = ""


@router.get("/projects")
async def list_projects(ctx: dict = Depends(get_ctx)):
    projects = await db.projects.find({"org_id": ctx["org"]["org_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    for p in projects:
        q = {**item_scope_query(ctx["member"]), "project_id": p["project_id"]}
        p["total"] = await db.items.count_documents(q)
        p["done"] = await db.items.count_documents({**q, "status": "done"})
    if not has_scope(ctx["member"], "team_work"):
        projects = [p for p in projects if p["total"] or p.get("created_by") == ctx["member"]["member_id"]]
    return {"projects": projects}


@router.post("/projects")
async def create_project(body: ProjectIn, ctx: dict = Depends(get_ctx)):
    pid = await engine.ensure_project(ctx["org"]["org_id"], body.name, ctx["member"])
    if body.description:
        await db.projects.update_one({"project_id": pid}, {"$set": {"description": body.description[:500]}})
    return await db.projects.find_one({"project_id": pid}, {"_id": 0})


# ================================================================ dashboard
@router.get("/dashboard")
async def dashboard(ctx: dict = Depends(get_ctx)):
    m, org = ctx["member"], ctx["org"]
    items = await db.items.find(item_scope_query(m), {"_id": 0, "history": 0}).to_list(2000)
    ref = now()
    tz = org_tz(org)
    local_today = ref.astimezone(tz).date()
    week_ago = ref - timedelta(days=7)
    for i in items:
        i["state"] = item_state(i, ref)
    open_items = [i for i in items if i["state"] not in ("done", "cancelled")]
    overdue = [i for i in open_items if i["state"] == "overdue"]
    due_today = [i for i in open_items if i.get("due_at") and parse_iso(i["due_at"]).astimezone(tz).date() == local_today and i["state"] != "overdue"]
    due_soon = [i for i in open_items if i["state"] == "due" and i not in due_today]
    stuck = [i for i in open_items if i["state"] == "stuck"]
    done_week = [i for i in items if i["state"] == "done" and parse_iso(i.get("done_at")) and parse_iso(i["done_at"]) > week_ago]
    waiting = []
    for i in open_items:
        if i.get("assignee_id") and i.get("created_by") and i["assignee_id"] != i["created_by"]:
            waiting.append({"item_id": i["item_id"], "title": i["title"], "waiting": i.get("created_by_name"), "on": i.get("assignee_name"),
                            "due_at": i.get("due_at"), "state": i["state"]})
        if i.get("depends_on"):
            for d in items:
                if d["item_id"] in i["depends_on"] and d["state"] not in ("done", "cancelled"):
                    waiting.append({"item_id": i["item_id"], "title": i["title"], "waiting": i.get("assignee_name"), "on": d.get("assignee_name"),
                                    "due_at": d.get("due_at"), "state": d["state"], "blocked_by": d["title"]})
    upcoming = sorted([i for i in open_items if i.get("due_at") and i["state"] == "open"], key=lambda i: i["due_at"])[:8]
    brief = await db.brain_messages.find_one({"member_id": m["member_id"], "kind": "brief"}, {"_id": 0}, sort=[("created_at", -1)])
    pending_approvals = await db.approvals.count_documents({"org_id": org["org_id"], "status": "pending"}) if has_scope(m, "approve") else \
        await db.approvals.count_documents({"org_id": org["org_id"], "status": "pending", "requested_by": m["member_id"]})
    team = await db.members.count_documents({"org_id": org["org_id"], "status": "active"}) if m.get("member_type") != "partner" else \
        len(engine.visible_people(m, await db.members.find({"org_id": org["org_id"], "status": "active"}, {"_id": 0}).to_list(500)))
    slim = lambda lst: [redact_item({k: i.get(k) for k in ("item_id", "title", "kind", "state", "assignee_name", "due_at", "counterparty", "stuck_reason", "delay_reason", "amount", "currency", "created_by", "assignee_id")}, m) for i in lst]
    return {"counts": {"due_today": len(due_today), "overdue": len(overdue), "stuck": len(stuck), "done_week": len(done_week),
                       "open": len(open_items), "approvals": pending_approvals, "team": team},
            "overdue": slim(overdue[:10]), "due_today": slim(due_today[:10]), "due_soon": slim(due_soon[:10]), "stuck": slim(stuck[:10]),
            "waiting": waiting[:15], "upcoming": slim(upcoming), "brief": brief, "org": {"name": org["name"], "profile_learned": org.get("profile_learned")}}


# ================================================================ approvals
@router.get("/approvals")
async def list_approvals(status: str = "pending", ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    q = {"org_id": m["org_id"]}
    if not has_scope(m, "approve"):
        q["requested_by"] = m["member_id"]
    if status == "pending":
        q["status"] = "pending"
    elif status == "decided":
        q["status"] = {"$ne": "pending"}
    aps = await db.approvals.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    if not has_scope(m, "money"):
        aps = [a if a["requested_by"] == m["member_id"] else {**a, "amount": None} for a in aps]
    return {"approvals": aps, "can_decide": has_scope(m, "approve")}


class ApprovalIn(BaseModel):
    kind: str = "other"
    title: str
    details: Optional[str] = ""
    amount: Optional[float] = None


@router.post("/approvals")
async def create_approval(body: ApprovalIn, ctx: dict = Depends(get_ctx)):
    ap = await engine.create_approval(ctx["org"], ctx["member"], kind=body.kind, title=body.title, details=body.details or "", amount=body.amount)
    return ap


class DecideIn(BaseModel):
    decision: str
    max_amount: Optional[float] = None
    note: Optional[str] = None


@router.post("/approvals/{approval_id}/decide")
async def decide(approval_id: str, body: DecideIn, ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    if not has_scope(m, "approve"):
        raise HTTPException(403, "You can't decide approvals")
    if body.decision not in ("once", "always", "deny"):
        raise HTTPException(400, "Unknown decision")
    ap = await db.approvals.find_one({"approval_id": approval_id, "org_id": m["org_id"]}, {"_id": 0})
    if not ap:
        raise HTTPException(404, "Not found")
    if ap["status"] != "pending":
        raise HTTPException(409, "Already decided")
    res = await engine.decide_approval(ctx["org"], m, ap, body.decision, body.max_amount, body.note)
    return res


@router.post("/approvals/{approval_id}/undo")
async def undo(approval_id: str, ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    if not has_scope(m, "approve"):
        raise HTTPException(403, "You can't decide approvals")
    ap = await db.approvals.find_one({"approval_id": approval_id, "org_id": m["org_id"]}, {"_id": 0})
    if not ap:
        raise HTTPException(404, "Not found")
    return {"approval": await engine.undo_decision(ctx["org"], m, ap)}


class ReplyIn(BaseModel):
    text: str


@router.post("/approvals/{approval_id}/reply")
async def reply_words(approval_id: str, body: ReplyIn, ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    if not has_scope(m, "approve"):
        raise HTTPException(403, "You can't decide approvals")
    ap = await db.approvals.find_one({"approval_id": approval_id, "org_id": m["org_id"]}, {"_id": 0})
    if not ap:
        raise HTTPException(404, "Not found")
    if ap["status"] != "pending":
        raise HTTPException(409, "Already decided")
    d = await brain.interpret_decision(ctx["org"], ap, body.text)
    if d.get("decision") not in ("once", "always", "deny"):
        return {"understood": False, "summary": "I couldn't tell if that's a yes or no. Try 'yes, just this once', 'always under 15000' or 'no'."}
    res = await engine.decide_approval(ctx["org"], m, ap, d["decision"], d.get("max_amount"), d.get("note") or body.text[:200])
    return {"understood": True, **res}


# ================================================================ rules + knowledge
@router.get("/rules")
async def list_rules(ctx: dict = Depends(get_ctx)):
    rules = await engine.active_rules(ctx["org"]["org_id"]) if can_read_rules(ctx["member"]) else []
    return {"rules": rules, "can_edit": has_scope(ctx["member"], "manage_team")}


class RuleIn(BaseModel):
    text: str


@router.post("/rules")
async def create_rule(body: RuleIn, ctx: dict = Depends(get_ctx)):
    m, org = ctx["member"], ctx["org"]
    if not has_scope(m, "manage_team"):
        raise HTTPException(403, "Only the owner can set business rules")
    text = body.text.strip()
    if len(text) < 4:
        raise HTTPException(400, "Write the rule in a sentence")
    cfg = await brain.get_brain_config()
    people = await engine.org_people(org["org_id"])
    a = await brain.analyze(org, m, f"From now on: {text}", people, [], [], [], cfg)
    act = next((x for x in a.get("actions", []) if x.get("type") == "add_rule"), {})
    rule = await engine.add_rule(org, m, text, trigger=act.get("trigger") or "any", keyword=act.get("keyword"), notify_target=act.get("notify"), source="settings")
    return rule


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, ctx: dict = Depends(get_ctx)):
    if not has_scope(ctx["member"], "manage_team"):
        raise HTTPException(403, "Only the owner can remove business rules")
    r = await db.rules.update_one({"rule_id": rule_id, "org_id": ctx["org"]["org_id"]}, {"$set": {"active": False, "removed_at": iso()}})
    if not r.matched_count:
        raise HTTPException(404, "Not found")
    return {"ok": True}


@router.get("/knowledge")
async def knowledge(ctx: dict = Depends(get_ctx)):
    org = ctx["org"]
    facts = await db.knowledge.find(fact_scope_query(ctx["member"]), {"_id": 0}).sort("created_at", -1).to_list(500)
    docs = await db.documents.count_documents(doc_scope_query(ctx["member"]))
    people = await db.members.count_documents({"org_id": org["org_id"], "status": "active"})
    rules = await engine.active_rules(org["org_id"]) if can_read_rules(ctx["member"]) else []
    return {"business": {k: org.get(k) for k in ("name", "industry", "description", "country", "currency", "timezone")},
            "facts": facts, "rules": rules, "documents": docs, "people": people}


class FactIn(BaseModel):
    text: str


class FactCorrectionIn(BaseModel):
    text: str = Field(min_length=1, max_length=400)


@router.post("/knowledge")
async def add_fact(body: FactIn, ctx: dict = Depends(get_ctx)):
    if not body.text.strip():
        raise HTTPException(400, "Write something to remember")
    if ctx["member"].get("member_type") == "partner":
        raise HTTPException(403, "External users can't add to company memory")
    org_id = ctx["org"]["org_id"]
    fact_text = body.text.strip()[:400]
    existing = await db.knowledge.find_one(
        {"org_id": org_id, "text": fact_text, "deleted": {"$ne": True}},
        {"_id": 0},
    )
    if existing:
        return existing
    f = build_user_confirmed_fact(
        fact_id=new_id("fct"),
        org_id=org_id,
        text=fact_text,
        category=fact_category(fact_text),
        member=ctx["member"],
        source="manual",
        created_at=iso(),
    )
    await db.knowledge.insert_one(dict(f))
    return f




@router.post("/knowledge/{fact_id}/correct")
async def correct_fact(fact_id: str, body: FactCorrectionIn, ctx: dict = Depends(get_ctx)):
    member = ctx["member"]
    if member.get("member_type") == "partner":
        raise HTTPException(403, "External users can't change company memory")
    previous = await db.knowledge.find_one(
        {"fact_id": fact_id, "org_id": member["org_id"], "deleted": {"$ne": True}, "lifecycle_status": {"$ne": "superseded"}},
        {"_id": 0},
    )
    if not previous:
        raise HTTPException(404, "Memory fact not found")
    if not is_owner(member) and previous.get("created_by") != member["member_id"]:
        raise HTTPException(403, "Only the fact's author or an owner can correct it")
    corrected_text = body.text.strip()
    if not corrected_text:
        raise HTTPException(400, "Write the corrected fact")
    if corrected_text == previous.get("text"):
        return previous
    created_at = iso()
    corrected = build_user_confirmed_fact(
        fact_id=new_id("fct"), org_id=member["org_id"], text=corrected_text,
        category=fact_category(corrected_text), member=member,
        source="manual_correction", created_at=created_at,
    )
    corrected.update({
        "version": int(previous.get("version") or 1) + 1,
        "supersedes_fact_id": fact_id,
        "correction_reason": "User corrected a previously stored business fact",
    })
    await db.knowledge.insert_one(dict(corrected))
    closed = await db.knowledge.update_one(
        {"fact_id": fact_id, "org_id": member["org_id"], "deleted": {"$ne": True}, "lifecycle_status": {"$ne": "superseded"}},
        {"$set": build_fact_correction_metadata(previous, corrected_at=created_at, corrected_by=member)},
    )
    if not closed.matched_count:
        await db.knowledge.update_one({"fact_id": corrected["fact_id"], "org_id": member["org_id"]},
                                      {"$set": {"deleted": True, "deleted_at": iso()}})
        raise HTTPException(409, "This memory fact changed while you were correcting it. Refresh and try again.")
    corrected.pop("_id", None)
    return corrected


@router.delete("/knowledge/{fact_id}")
async def delete_fact(fact_id: str, ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    q = {"fact_id": fact_id, "org_id": m["org_id"]}
    if not is_owner(m):
        q["created_by"] = m["member_id"]
    r = await db.knowledge.update_one(q, {"$set": {"deleted": True, "deleted_at": iso()}})
    if not r.matched_count:
        raise HTTPException(404, "Not found")
    return {"ok": True}


# ================================================================ documents
async def create_document(org: dict, member: dict, data: bytes, filename: str, visibility: str) -> dict:
    ext = ext_of(filename)
    rec = await _store_file(org, member, data, filename, DOC_TYPES.get(ext, "application/octet-stream"), "document")
    text = await asyncio.get_event_loop().run_in_executor(None, extract_text, filename, data)
    summary = await brain.summarize_document(org, filename, text) if text.strip() else {"summary": "No readable text found in this file.", "doc_type": "document", "key_details": [], "items": []}
    doc = {"doc_id": new_id("doc"), "org_id": org["org_id"], "file_id": rec["file_id"], "uploaded_by": member["member_id"], "uploaded_by_name": member["name"],
           "filename": filename, "content_type": rec["content_type"], "size": len(data), "text": text[:200000], "summary": summary.get("summary", ""),
           "doc_type": summary.get("doc_type"), "key_details": summary.get("key_details", [])[:20], "found_items": summary.get("items", [])[:5],
           "visibility": visibility if visibility in ("org", "private") else "org", "is_deleted": False, "created_at": iso()}
    await db.documents.insert_one(dict(doc))
    doc.pop("_id", None)
    await audit(org["org_id"], member["member_id"], "document_uploaded", {"doc_id": doc["doc_id"]})
    return doc


@router.post("/documents")
async def upload_document(file: UploadFile = File(...), visibility: str = Form("org"), ctx: dict = Depends(get_ctx)):
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File is too large (max 20 MB)")
    if ext_of(file.filename or "") not in DOC_TYPES:
        raise HTTPException(415, "Please upload a PDF, Word, Excel, CSV or text file.")
    doc = await create_document(ctx["org"], ctx["member"], data, file.filename, visibility)
    doc.pop("text", None)
    return doc


@router.get("/documents")
async def list_documents(q: Optional[str] = None, ctx: dict = Depends(get_ctx)):
    query = doc_scope_query(ctx["member"])
    if q:
        import re
        rx = {"$regex": re.escape(q), "$options": "i"}
        query = {**query, "$and": [{"$or": [{"filename": rx}, {"summary": rx}, {"text": rx}]}]}
    docs = await db.documents.find(query, {"_id": 0, "text": 0}).sort("created_at", -1).to_list(300)
    return {"documents": docs}


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str, ctx: dict = Depends(get_ctx)):
    d = await db.documents.find_one({**doc_scope_query(ctx["member"]), "doc_id": doc_id}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Not found")
    d["text_preview"] = (d.pop("text", "") or "")[:3000]
    return d


@router.get("/documents/{doc_id}/file")
async def document_file(doc_id: str, ctx: dict = Depends(get_ctx)):
    d = await db.documents.find_one({**doc_scope_query(ctx["member"]), "doc_id": doc_id}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Not found")
    rec = await db.files.find_one({"file_id": d["file_id"]}, {"_id": 0})
    data, _ = await get_object(rec["storage_path"])
    return Response(content=data, media_type=d["content_type"], headers={"Content-Disposition": f'attachment; filename="{d["filename"]}"'})


@router.post("/documents/{doc_id}/save-items")
async def document_save_items(doc_id: str, ctx: dict = Depends(get_ctx)):
    d = await db.documents.find_one({**doc_scope_query(ctx["member"]), "doc_id": doc_id}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Not found")
    created = []
    for it in d.get("found_items") or []:
        item = await engine.create_item(ctx["org"], ctx["member"], {**it, "assignee": "me"}, source={"type": "document", "doc_id": doc_id})
        created.append(item)
    await db.documents.update_one({"doc_id": doc_id}, {"$set": {"found_items": []}})
    return {"created": len(created)}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    q = {"doc_id": doc_id, "org_id": m["org_id"]}
    if not is_owner(m):
        q["uploaded_by"] = m["member_id"]
    r = await db.documents.update_one(q, {"$set": {"is_deleted": True}})
    if not r.matched_count:
        raise HTTPException(404, "Not found")
    return {"ok": True}


# ================================================================ search (one search, permission-scoped)
@router.get("/search")
async def search(q: str = Query(..., min_length=2), ctx: dict = Depends(get_ctx)):
    import re
    m, org = ctx["member"], ctx["org"]
    rx = {"$regex": re.escape(q.strip()), "$options": "i"}
    work = await db.items.find({**item_scope_query(m), "$and": [{"$or": [{"title": rx}, {"details": rx}, {"counterparty": rx}, {"assignee_name": rx}]}]},
                               {"_id": 0, "history": 0}).limit(20).to_list(20)
    people = await db.members.find({"org_id": org["org_id"], "status": {"$in": ["active", "invited"]}, "$or": [{"name": rx}, {"job": rx}]},
                                   {"_id": 0, "member_id": 1, "name": 1, "job": 1, "member_type": 1, "status": 1}).to_list(20)
    docs = await db.documents.find({**doc_scope_query(m), "$and": [{"$or": [{"filename": rx}, {"summary": rx}, {"text": rx}]}]}, {"_id": 0, "text": 0}).limit(10).to_list(10)
    fq = fact_scope_query(m)
    fq["$and"] = [{"text": rx}] + ([{"text": fq.pop("text")}] if "text" in fq else [])
    facts = await db.knowledge.find(fq, {"_id": 0}).limit(10).to_list(10)
    rules = await db.rules.find({"org_id": org["org_id"], "active": True, "text": rx}, {"_id": 0}).limit(10).to_list(10) if can_read_rules(m) else []
    if m.get("member_type") == "partner":
        people = [p for p in people if p.get("member_type") == "owner" or p["member_id"] in (m.get("invited_by"), m.get("manager_id"))]
    threads = await db.threads.find({"org_id": org["org_id"], "member_ids": m["member_id"]}, {"_id": 0, "thread_id": 1}).to_list(300)
    chats = await db.thread_messages.find({"thread_id": {"$in": [t["thread_id"] for t in threads]}, "text": rx}, {"_id": 0}).sort("created_at", -1).limit(10).to_list(10) if threads else []
    konnto = await db.brain_messages.find({"member_id": m["member_id"], "text": rx}, {"_id": 0, "msg_id": 1, "text": 1, "role": 1, "created_at": 1}).sort("created_at", -1).limit(8).to_list(8)
    return {"work": [_present(i, m) for i in work], "people": people, "documents": docs, "knowledge": facts, "rules": rules, "chats": chats, "konnto": konnto}


# ================================================================ privacy: view, export, delete my data
@router.get("/privacy/summary")
async def privacy_summary(ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    mid = m["member_id"]
    return {
        "member": {k: m.get(k) for k in ("name", "job", "phone", "email", "member_type", "wa_opt_in", "wa_opt_in_at", "joined_at", "access")},
        "counts": {
            "konnto_messages": await db.brain_messages.count_documents({"member_id": mid}),
            "private_notes": await db.items.count_documents({"created_by": mid, "visibility": "private", "deleted": {"$ne": True}}),
            "items_created": await db.items.count_documents({"created_by": mid, "deleted": {"$ne": True}}),
            "team_messages": await db.thread_messages.count_documents({"sender_id": mid}),
            "documents": await db.documents.count_documents({"uploaded_by": mid, "is_deleted": {"$ne": True}}),
            "files": await db.files.count_documents({"member_id": mid, "is_deleted": False}),
        },
        "is_owner": is_owner(m),
    }


@router.get("/privacy/export")
async def privacy_export(ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    mid = m["member_id"]
    data = {
        "exported_at": iso(), "user": {k: ctx["user"].get(k) for k in ("user_id", "name", "email", "whatsapp", "created_at")},
        "membership": m, "business": ctx["org"]["name"],
        "konnto_chat": await db.brain_messages.find({"member_id": mid}, {"_id": 0}).sort("created_at", 1).to_list(5000),
        "items_created_or_assigned": await db.items.find({"org_id": m["org_id"], "$or": [{"created_by": mid}, {"assignee_id": mid}], "deleted": {"$ne": True}}, {"_id": 0}).to_list(5000),
        "team_messages_sent": await db.thread_messages.find({"sender_id": mid}, {"_id": 0}).to_list(5000),
        "documents": await db.documents.find({"uploaded_by": mid, "is_deleted": {"$ne": True}}, {"_id": 0, "text": 0}).to_list(1000),
        "approvals": await db.approvals.find({"org_id": m["org_id"], "$or": [{"requested_by": mid}, {"decided_by": mid}]}, {"_id": 0}).to_list(2000),
    }
    body = json.dumps(data, default=str, indent=1)
    return Response(content=body, media_type="application/json", headers={"Content-Disposition": 'attachment; filename="konnto-my-data.json"'})


class DeleteIn(BaseModel):
    confirm: str


@router.post("/privacy/delete")
async def privacy_delete(body: DeleteIn, ctx: dict = Depends(get_ctx)):
    """Explicit, user-confirmed deletion of this person's data in this business (owner: the whole business)."""
    if body.confirm.strip().upper() != "DELETE":
        raise HTTPException(400, "Type DELETE to confirm")
    m, org, user = ctx["member"], ctx["org"], ctx["user"]
    mid = m["member_id"]
    await db.brain_messages.delete_many({"member_id": mid})
    await db.items.update_many({"created_by": mid, "visibility": "private"}, {"$set": {"deleted": True, "title": "(deleted)", "details": ""}})
    await db.thread_messages.update_many({"sender_id": mid}, {"$set": {"text": "(message deleted)", "sender_name": "Former member"}})
    await db.files.update_many({"member_id": mid}, {"$set": {"is_deleted": True}})
    await db.documents.update_many({"uploaded_by": mid, "visibility": "private"}, {"$set": {"is_deleted": True}})
    await db.pending_states.delete_many({"member_id": mid})
    if is_owner(m):
        oid = org["org_id"]
        await db.items.update_many({"org_id": oid}, {"$set": {"deleted": True}})
        await db.documents.update_many({"org_id": oid}, {"$set": {"is_deleted": True}})
        await db.files.update_many({"org_id": oid}, {"$set": {"is_deleted": True}})
        await db.members.update_many({"org_id": oid}, {"$set": {"status": "removed", "phone": None, "email": None}})
        await db.orgs.update_one({"org_id": oid}, {"$set": {"deleted": True, "deleted_at": iso(), "name": "(deleted business)"}})
    else:
        await db.members.update_one({"member_id": mid}, {"$set": {"status": "removed", "phone": None, "email": None, "name": "Former member", "user_id": None}})
    remaining = await db.members.count_documents({"user_id": user["user_id"], "status": "active"})
    if not remaining:
        await db.users.delete_one({"user_id": user["user_id"]})
    else:
        await db.users.update_one({"user_id": user["user_id"]}, {"$unset": {"current_org_id": ""}})
    return {"ok": True, "account_removed": not remaining}


# ================================================================ announcements + feedback
@router.get("/announcements")
async def announcements(user: dict = Depends(current_user)):
    t = iso()
    items = await db.announcements.find({"active": True, "$or": [{"ends_at": None}, {"ends_at": {"$gt": t}}]}, {"_id": 0}).sort("created_at", -1).to_list(5)
    return {"announcements": items}


class FeedbackIn(BaseModel):
    text: str
    rating: Optional[int] = Field(None, ge=1, le=5)
    page: Optional[str] = None


@router.post("/feedback")
async def feedback(body: FeedbackIn, user: dict = Depends(current_user)):
    if not body.text.strip():
        raise HTTPException(400, "Write a few words")
    fb = {"feedback_id": new_id("fbk"), "user_id": user["user_id"], "user_name": user.get("name"), "user_email": user.get("email"),
          "org_id": user.get("current_org_id"), "text": body.text.strip()[:2000], "rating": body.rating, "page": body.page, "status": "new", "created_at": iso()}
    await db.feedback.insert_one(dict(fb))
    return {"ok": True}


@router.post("/help/chat")
async def help_chat(body: ChatIn, user: dict = Depends(current_user)):
    cfg = await brain.get_brain_config()
    hist = await db.help_messages.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(8)
    hist.reverse()
    await db.help_messages.insert_one({"user_id": user["user_id"], "role": "user", "text": body.text[:2000], "created_at": iso()})

    async def gen():
        out = []
        async for d in brain.stream_help(body.text, hist, cfg, user.get("current_org_id")):
            out.append(d)
            yield _sse({"type": "delta", "text": d})
        await db.help_messages.insert_one({"user_id": user["user_id"], "role": "assistant", "text": "".join(out), "created_at": iso()})
        yield _sse({"type": "done"})

    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)
