"""Team: people, invites (join links), access, direct & group chats that reach WhatsApp."""
import asyncio
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from core import db, iso, new_id, current_user, get_ctx, has_scope, is_owner, SCOPES, SENSITIVE_SCOPES, SAFE_SCOPES, norm_phone, audit
from channels import wa_configured, wa_join_link
import engine

router = APIRouter(prefix="/api")


def _present_member(m: dict, viewer: dict, org: dict) -> dict:
    out = {k: m.get(k) for k in ("member_id", "name", "job", "member_type", "status", "access", "access_reason", "joined_at", "created_at",
                                 "invited_by_name", "wa_opt_in", "manager_id", "joined_via")}
    out["has_app"] = bool(m.get("user_id"))
    out["has_whatsapp"] = bool(m.get("phone"))
    if m["member_id"] == viewer["member_id"] or has_scope(viewer, "staff"):
        out["phone"] = m.get("phone")
        out["email"] = m.get("email")
    if m.get("status") == "invited" and has_scope(viewer, "manage_team") and m.get("invite_token"):
        out["links"] = engine.invite_links(org, m)
    return out


@router.get("/scopes")
async def scopes():
    return {"scopes": SCOPES, "sensitive": sorted(SENSITIVE_SCOPES), "safe": sorted(SAFE_SCOPES)}


@router.get("/members")
async def list_members(ctx: dict = Depends(get_ctx)):
    m, org = ctx["member"], ctx["org"]
    members = await db.members.find({"org_id": org["org_id"], "status": {"$in": ["active", "invited"]}}, {"_id": 0}).sort("created_at", 1).to_list(500)
    members = engine.visible_people(m, members)  # external partners only see the owner and whoever brought them in
    return {"members": [_present_member(x, m, org) for x in members], "me": m["member_id"], "can_manage": has_scope(m, "manage_team"),
            "is_owner": is_owner(m), "whatsapp_connected": wa_configured()}


class InviteIn(BaseModel):
    name: str
    job: Optional[str] = ""
    member_type: str = "team"
    phone: Optional[str] = None
    email: Optional[str] = None


@router.post("/members")
async def invite_member(body: InviteIn, ctx: dict = Depends(get_ctx)):
    m, org = ctx["member"], ctx["org"]
    if not has_scope(m, "manage_team"):
        raise HTTPException(403, "Only the owner can add people")
    if not body.name.strip():
        raise HTTPException(400, "Name is needed")
    new = await engine.create_invite(org, m, body.name, body.job or "", body.member_type, body.phone, body.email)
    return {"member": _present_member(new, m, org), "links": engine.invite_links(org, new)}


class MemberPatch(BaseModel):
    name: Optional[str] = None
    job: Optional[str] = None
    access: Optional[List[str]] = None
    manager_id: Optional[str] = None
    member_type: Optional[str] = None


@router.patch("/members/{member_id}")
async def patch_member(member_id: str, body: MemberPatch, ctx: dict = Depends(get_ctx)):
    m, org = ctx["member"], ctx["org"]
    if not has_scope(m, "manage_team"):
        raise HTTPException(403, "Only the owner can change people")
    target = await db.members.find_one({"member_id": member_id, "org_id": org["org_id"], "status": {"$in": ["active", "invited"]}}, {"_id": 0})
    if not target:
        raise HTTPException(404, "Not found")
    if is_owner(target) and not is_owner(m):
        raise HTTPException(403, "Not allowed")
    upd = {}
    if body.name:
        upd["name"] = body.name.strip()[:80]
    if body.job is not None:
        upd["job"] = body.job.strip()[:120]
    if body.member_type in ("team", "partner") and not is_owner(target):
        upd["member_type"] = body.member_type
    if body.manager_id is not None:
        upd["manager_id"] = body.manager_id or None
    if body.access is not None and not is_owner(target):
        new_access = [s for s in body.access if s in SCOPES]
        if not is_owner(m) and set(new_access) & SENSITIVE_SCOPES - set(target.get("access") or []):
            raise HTTPException(403, "Only the owner can give sensitive access")
        if "own_work" not in new_access:
            new_access.insert(0, "own_work")
        upd["access"] = new_access
        upd["access_reason"] = f"Access set by {m['name']}."
    if upd:
        await db.members.update_one({"member_id": member_id}, {"$set": upd})
        await audit(org["org_id"], m["member_id"], "member_updated", {"member_id": member_id, "fields": list(upd.keys())})
    target = await db.members.find_one({"member_id": member_id}, {"_id": 0})
    return _present_member(target, m, org)


@router.delete("/members/{member_id}")
async def remove_member(member_id: str, ctx: dict = Depends(get_ctx)):
    m, org = ctx["member"], ctx["org"]
    if not has_scope(m, "manage_team"):
        raise HTTPException(403, "Only the owner can remove people")
    target = await db.members.find_one({"member_id": member_id, "org_id": org["org_id"]}, {"_id": 0})
    if not target or is_owner(target):
        raise HTTPException(404, "Not found")
    await db.members.update_one({"member_id": member_id}, {"$set": {"status": "removed", "removed_at": iso()}, "$unset": {"invite_token": ""}})
    await audit(org["org_id"], m["member_id"], "member_removed", {"member_id": member_id})
    return {"ok": True}


# ---------------------------------------------------------------- joining
@router.get("/public/invites/{token}")
async def public_invite(token: str):
    m = await db.members.find_one({"invite_token": token, "status": "invited"}, {"_id": 0})
    if not m:
        raise HTTPException(404, "This invite link has been used or has expired.")
    org = await db.orgs.find_one({"org_id": m["org_id"], "deleted": {"$ne": True}}, {"_id": 0})
    if not org:
        raise HTTPException(404, "This invite link has expired.")
    return {"business": org["name"], "name": m["name"], "job": m.get("job"), "member_type": m["member_type"], "invited_by": m.get("invited_by_name"),
            "access_reason": m.get("access_reason"), "wa_join_url": wa_join_link(m["invite_code"]), "invite_code": m["invite_code"],
            "whatsapp_connected": wa_configured()}


class AcceptIn(BaseModel):
    phone: Optional[str] = None
    consent: bool = True


@router.post("/invites/{token}/accept")
async def accept_invite(token: str, body: AcceptIn, user: dict = Depends(current_user)):
    m = await db.members.find_one({"invite_token": token, "status": "invited"}, {"_id": 0})
    if not m:
        raise HTTPException(404, "This invite link has been used or has expired.")
    already = await db.members.find_one({"org_id": m["org_id"], "user_id": user["user_id"], "status": "active"})
    if already:
        raise HTTPException(409, "You're already part of this business.")
    org = await db.orgs.find_one({"org_id": m["org_id"], "deleted": {"$ne": True}}, {"_id": 0})
    if not org:
        raise HTTPException(404, "This invite link has expired.")
    phone = norm_phone(body.phone) if body.phone else (user.get("whatsapp") or m.get("phone"))
    if user.get("email") and not m.get("email"):
        await db.members.update_one({"member_id": m["member_id"]}, {"$set": {"email": user["email"]}})
    if user.get("name") and not m.get("name"):
        await db.members.update_one({"member_id": m["member_id"]}, {"$set": {"name": user["name"]}})
    if phone:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"whatsapp": phone}})
    m = await db.members.find_one({"member_id": m["member_id"]}, {"_id": 0})
    member = await engine.activate_member(org, m, user_id=user["user_id"], phone=phone, consent=body.consent, via="app_link")
    return {"ok": True, "org_id": org["org_id"], "member_id": member["member_id"]}


# ---------------------------------------------------------------- chats (direct + group)
async def _thread_for(member: dict, thread_id: str) -> dict:
    t = await db.threads.find_one({"thread_id": thread_id, "org_id": member["org_id"], "member_ids": member["member_id"]}, {"_id": 0})
    if not t:
        raise HTTPException(404, "Not found")
    return t


@router.get("/threads")
async def list_threads(ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    threads = await db.threads.find({"org_id": m["org_id"], "member_ids": m["member_id"]}, {"_id": 0}).sort("last_message_at", -1).to_list(200)
    ids = {x for t in threads for x in t["member_ids"]}
    names = {x["member_id"]: x for x in await db.members.find({"member_id": {"$in": list(ids)}}, {"_id": 0, "member_id": 1, "name": 1, "job": 1, "member_type": 1, "status": 1}).to_list(500)}
    out = []
    for t in threads:
        others = [names[i] for i in t["member_ids"] if i != m["member_id"] and i in names]
        last_read = (t.get("reads") or {}).get(m["member_id"]) or ""
        unread = await db.thread_messages.count_documents({"thread_id": t["thread_id"], "created_at": {"$gt": last_read}, "sender_id": {"$ne": m["member_id"]}})
        out.append({**{k: t.get(k) for k in ("thread_id", "kind", "name", "last_message_at", "last_message_preview", "member_ids")},
                    "title": t.get("name") or ", ".join(o["name"] for o in others) or "Just you", "others": others, "unread": unread})
    return {"threads": out}


class ThreadIn(BaseModel):
    member_ids: List[str]
    name: Optional[str] = None


@router.post("/threads")
async def create_thread(body: ThreadIn, ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    ids = [i for i in dict.fromkeys(body.member_ids) if i != m["member_id"]]
    others = await db.members.find({"member_id": {"$in": ids}, "org_id": m["org_id"], "status": {"$in": ["active", "invited"]}}, {"_id": 0}).to_list(100)
    others = [o for o in engine.visible_people(m, others) if o["member_id"] != m["member_id"]]
    if not others:
        raise HTTPException(400, "Pick at least one person")
    if len(others) == 1 and not body.name:
        return await engine.get_or_create_direct_thread(m["org_id"], m, others[0])
    t = {"thread_id": new_id("thr"), "org_id": m["org_id"], "kind": "group", "member_ids": sorted([m["member_id"]] + [o["member_id"] for o in others]),
         "name": (body.name or ", ".join(o["name"].split()[0] for o in others))[:60], "created_by": m["member_id"], "created_at": iso(),
         "last_message_at": iso(), "last_message_preview": "", "reads": {}}
    await db.threads.insert_one(dict(t))
    t.pop("_id", None)
    return t


@router.get("/threads/{thread_id}/messages")
async def thread_messages(thread_id: str, after: Optional[str] = None, ctx: dict = Depends(get_ctx)):
    m = ctx["member"]
    t = await _thread_for(m, thread_id)
    q = {"thread_id": thread_id}
    if after:
        q["created_at"] = {"$gt": after}
    msgs = await db.thread_messages.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    msgs.reverse()
    await db.threads.update_one({"thread_id": thread_id}, {"$set": {f"reads.{m['member_id']}": iso()}})
    members = await db.members.find({"member_id": {"$in": t["member_ids"]}}, {"_id": 0, "member_id": 1, "name": 1, "job": 1, "member_type": 1, "phone": 1, "wa_opt_in": 1, "user_id": 1}).to_list(100)
    people = [{"member_id": x["member_id"], "name": x["name"], "job": x.get("job"), "member_type": x.get("member_type"),
               "on_whatsapp": bool(x.get("phone") and x.get("wa_opt_in")), "has_app": bool(x.get("user_id"))} for x in members]
    item_ids = [x["item_id"] for x in msgs if x.get("item_id")]
    items = {i["item_id"]: i for i in await db.items.find({"item_id": {"$in": item_ids}}, {"_id": 0, "item_id": 1, "status": 1, "title": 1, "due_at": 1}).to_list(200)}
    for x in msgs:
        if x.get("item_id") in items:
            x["item"] = items[x["item_id"]]
    return {"thread": {**{k: t.get(k) for k in ("thread_id", "kind", "name", "member_ids")}}, "people": people, "messages": msgs}


class ThreadMsgIn(BaseModel):
    text: str


@router.post("/threads/{thread_id}/messages")
async def send_thread_message(thread_id: str, body: ThreadMsgIn, background: BackgroundTasks, ctx: dict = Depends(get_ctx)):
    m, org = ctx["member"], ctx["org"]
    t = await _thread_for(m, thread_id)
    if not body.text.strip():
        raise HTTPException(400, "Write a message")
    msg = await engine.post_thread_message(org, m, t, body.text)
    background.add_task(engine.spot_and_attach, org, m, msg)
    return msg


@router.post("/threads/{thread_id}/messages/{msg_id}/cards/{card_id}/{op}")
async def thread_card(thread_id: str, msg_id: str, card_id: str, op: str, ctx: dict = Depends(get_ctx)):
    m, org = ctx["member"], ctx["org"]
    await _thread_for(m, thread_id)
    msg = await db.thread_messages.find_one({"msg_id": msg_id, "thread_id": thread_id}, {"_id": 0})
    if not msg:
        raise HTTPException(404, "Not found")
    card = next((c for c in msg.get("cards", []) if c["card_id"] == card_id), None)
    if not card or card["status"] != "pending":
        raise HTTPException(404, "Not found")
    if op == "save":
        people = await engine.org_people(org["org_id"])
        sender = next((p for p in people if p["member_id"] == msg["sender_id"]), m)
        data = engine._proposal_data(org, card["data"], people, sender)
        item = await engine.save_proposal(org, m, data, {"type": "team_chat", "thread_id": thread_id, "msg_id": msg_id})
        card["status"], card["item_id"] = "saved", item["item_id"]
    elif op == "skip":
        card["status"] = "skipped"
    else:
        raise HTTPException(400, "Unknown action")
    await db.thread_messages.update_one({"msg_id": msg_id}, {"$set": {"cards": msg["cards"]}})
    return {"card": card}
