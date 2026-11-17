"""Official WhatsApp Business Platform: signed webhook (text, voice, photos, documents, buttons), statuses, opt-in/out, and WhatsApp sign-in codes."""
import hmac
import json
import base64
import hashlib
import secrets
import tempfile
import logging
from datetime import timedelta

import httpx
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from core import db, now, iso, parse_iso, new_id, norm_phone, digits, make_app_token, app_link, ENV
from channels import wa_cfg, wa_configured, wa_send
from storage import AUDIO_TYPES, IMAGE_TYPES, DOC_TYPES, ext_of
import brain
import engine

logger = logging.getLogger("konnto.wa")
router = APIRouter(prefix="/api")


@router.get("/webhooks/whatsapp", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    q = request.query_params
    verify = wa_cfg()["verify"]
    if verify and q.get("hub.mode") == "subscribe" and hmac.compare_digest(q.get("hub.verify_token", ""), verify):
        return q.get("hub.challenge", "")
    raise HTTPException(403, "verification failed")


def _valid_signature(raw: bytes, header) -> bool:
    secret = wa_cfg()["app_secret"]
    if not secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[7:])


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request, background: BackgroundTasks):
    raw = await request.body()
    if not _valid_signature(raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(401, "bad signature")
    payload = json.loads(raw)
    if payload.get("object") != "whatsapp_business_account":
        return {"ok": True}
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for m in value.get("messages", []):
                try:
                    await db.wa_events.insert_one({"event_id": m["id"], "kind": "message", "received_at": iso()})
                except Exception as e:
                    if "duplicate" in str(e).lower():
                        continue
                    raise
                background.add_task(handle_inbound, m, value)
            for s in value.get("statuses", []):
                await db.outbox.update_one({"wamid": s.get("id")}, {"$set": {"status": s.get("status"), "status_at": iso(), "errors": s.get("errors", [])}})
    return {"ok": True}


async def _download_media(media_id: str) -> tuple:
    c = wa_cfg()
    headers = {"Authorization": f"Bearer {c['token']}"}
    async with httpx.AsyncClient(timeout=60) as cl:
        meta = (await cl.get(f"https://graph.facebook.com/{c['version']}/{media_id}", headers=headers)).json()
        r = await cl.get(meta["url"], headers=headers)
        r.raise_for_status()
        return r.content, meta.get("mime_type", "")


async def _reply(phone: str, text: str, org_id=None, member_id=None, buttons=None):
    await wa_send(to_phone=phone, text=text, buttons=buttons, org_id=org_id, member_id=member_id, kind="reply")


async def _member_for(wa_id: str):
    phone = f"+{wa_id}"
    members = await db.members.find({"phone": phone, "status": "active"}, {"_id": 0}).sort("joined_at", -1).to_list(20)
    if not members:
        return None, None
    member = members[0]
    for m in members:
        if m.get("user_id"):
            u = await db.users.find_one({"user_id": m["user_id"]})
            if u and u.get("current_org_id") == m["org_id"]:
                member = m
                break
    org = await db.orgs.find_one({"org_id": member["org_id"], "deleted": {"$ne": True}}, {"_id": 0})
    return (member, org) if org else (None, None)


async def handle_inbound(m: dict, value: dict):
    try:
        await _handle_inbound(m, value)
    except Exception as e:
        logger.exception("inbound failed: %s", e)


async def _handle_inbound(m: dict, value: dict):
    wa_id = m["from"]
    typ = m.get("type")
    profile = ((value.get("contacts") or [{}])[0].get("profile") or {}).get("name")
    await db.wa_contacts.update_one({"wa_id": wa_id}, {"$set": {"wa_id": wa_id, "last_inbound_at": iso(), "profile_name": profile}}, upsert=True)
    text = ""
    if typ == "text":
        text = (m.get("text") or {}).get("body", "").strip()
    upper = text.upper()

    if upper in ("STOP", "UNSUBSCRIBE", "OPT OUT"):
        await db.wa_contacts.update_one({"wa_id": wa_id}, {"$set": {"opted_out": True, "opted_out_at": iso()}})
        await db.members.update_many({"phone": f"+{wa_id}"}, {"$set": {"wa_opt_in": False, "wa_opt_out_at": iso()}})
        from channels import wa_post, _session_payload
        await wa_post(_session_payload(wa_id, "You won't get KONNTO messages here any more. Reply START to turn them back on.", None))
        return
    if upper in ("START", "UNSTOP"):
        await db.wa_contacts.update_one({"wa_id": wa_id}, {"$set": {"opted_out": False, "opted_in_at": iso()}})
        await db.members.update_many({"phone": f"+{wa_id}", "status": "active"}, {"$set": {"wa_opt_in": True, "wa_opt_in_at": iso(), "wa_opt_in_source": "whatsapp_start"}})
        await _reply(wa_id, "KONNTO messages are back on. Just message me any time.")
        return
    if upper.startswith("JOIN "):
        code = upper.split()[1] if len(upper.split()) > 1 else ""
        inv = await db.members.find_one({"invite_code": code, "status": "invited"}, {"_id": 0})
        if not inv:
            await _reply(wa_id, "That join code isn't valid any more. Ask for a new invite link.")
            return
        org = await db.orgs.find_one({"org_id": inv["org_id"]}, {"_id": 0})
        await db.wa_contacts.update_one({"wa_id": wa_id}, {"$set": {"opted_out": False, "opted_in_at": iso()}})
        linked_user = await db.users.find_one({"whatsapp": f"+{wa_id}", "whatsapp_verified": True})
        await engine.activate_member(org, inv, user_id=(linked_user or {}).get("user_id"), phone=f"+{wa_id}", consent=True, via="whatsapp_join")
        return

    member, org = await _member_for(wa_id)
    if not member:
        await _reply(wa_id, f"Hi{(' ' + profile.split()[0]) if profile else ''}! I'm KONNTO AI. To start, sign up here: {app_link('/sign-up')} — or ask your business for an invite link.")
        return

    # button replies (session interactive or template quick reply)
    reply_id = None
    if typ == "interactive":
        r = (m.get("interactive") or {}).get("button_reply") or (m.get("interactive") or {}).get("list_reply")
        reply_id = (r or {}).get("id")
    elif typ == "button":
        reply_id = (m.get("button") or {}).get("payload")
    if reply_id:
        txt = await engine.handle_button(org, member, reply_id, via="whatsapp")
        await _reply(wa_id, txt, org["org_id"], member["member_id"])
        return

    if upper == "UNDO":
        ap = await engine.last_undoable_decision(member)
        if ap:
            await engine.undo_decision(org, member, ap)
            await _reply(wa_id, f"Undone. '{ap['title']}' is waiting for your decision again.", org["org_id"], member["member_id"])
        else:
            await _reply(wa_id, "There's nothing to undo.", org["org_id"], member["member_id"])
        return

    # replying to a forwarded team message -> goes back into that chat
    ctx_id = (m.get("context") or {}).get("id")
    if ctx_id and text:
        out = await db.outbox.find_one({"wamid": ctx_id, "kind": "team_message"})
        if out and out.get("thread_id"):
            thread = await db.threads.find_one({"thread_id": out["thread_id"], "member_ids": member["member_id"]}, {"_id": 0})
            if thread:
                await engine.post_thread_message(org, member, thread, text)
                return

    if text:
        state = await engine.pop_pending_state(member)
        if state:
            txt = await engine.handle_pending_reply(org, member, state, text)
            await _reply(wa_id, txt, org["org_id"], member["member_id"])
            return

    attachments, extra = [], ""
    try:
        if typ == "audio":
            data, mime = await _download_media(m["audio"]["id"])
            ext = "ogg" if "ogg" in mime else ("mp3" if "mpeg" in mime else "m4a")
            with tempfile.NamedTemporaryFile(suffix=f".{ext}") as tmp:
                tmp.write(data)
                tmp.flush()
                text = await brain.transcribe_audio(org["org_id"], tmp.name)
            attachments.append({"type": "audio", "transcript": text})
            extra = "[This message was a voice note, transcribed]"
        elif typ == "image":
            data, mime = await _download_media(m["image"]["id"])
            desc = await brain.describe_image(org, base64.b64encode(data).decode(), (m["image"].get("caption") or ""))
            text = m["image"].get("caption") or "(sent a photo)"
            attachments.append({"type": "image", "description": desc})
            extra = f"[Photo sent] {desc}"
        elif typ == "document":
            data, mime = await _download_media(m["document"]["id"])
            fname = m["document"].get("filename") or "document.pdf"
            if ext_of(fname) in DOC_TYPES:
                from routes_app import create_document
                doc = await create_document(org, member, data, fname, "org")
                attachments.append({"type": "document", "doc_id": doc["doc_id"], "filename": fname, "summary": doc.get("summary")})
                extra = f"[Document '{fname}' uploaded] {doc.get('summary', '')}"
            text = m["document"].get("caption") or f"(sent a document: {fname})"
    except Exception as e:
        logger.error("media handling failed: %s", e)
        await _reply(wa_id, "I couldn't open that file. Please try again or send it in the app.", org["org_id"], member["member_id"])
        return
    if not text:
        await _reply(wa_id, "I can read text, voice notes, photos and documents. Please try one of those.", org["org_id"], member["member_id"])
        return

    final = await engine.run_brain_collect(org, member, text, channel="whatsapp", attachments=attachments, extra_context=extra)
    if not final:
        return
    reply = final["text"] or "Okay."
    for c in final.get("cards", []):
        if c["type"] == "invite" and c["data"].get("invite_url"):
            reply += f"\n\nInvite link for {c['data']['name']}: {c['data']['invite_url']}"
    pending = [c for c in final.get("cards", []) if c["type"] == "proposal" and c["status"] == "pending"]
    drafts = [c for c in final.get("cards", []) if c["status"] == "draft" or (c["type"] == "handover" and c["status"] == "pending")]
    buttons = None
    if drafts and not pending:
        reply += "\n\nWaiting for your confirmation:\n" + "\n".join(f"- {engine.draft_line(c)}" for c in drafts[:4])
        buttons = [{"id": f"confirm:{final['msg_id']}", "label": "Confirm"}, {"id": f"dismiss:{final['msg_id']}", "label": "Dismiss"}]
    elif pending:
        lines = "\n".join(f"- {c['data']['kind'].title()}: {c['data']['title']}" for c in pending[:4])
        reply += f"\n\n{lines}"
        buttons = [{"id": f"save:{final['msg_id']}", "label": "Save"}, {"id": f"skip:{final['msg_id']}", "label": "Skip"}]
    await _reply(wa_id, reply, org["org_id"], member["member_id"], buttons=buttons)


# ---------------------------------------------------------------- WhatsApp sign-in (authentication template code)
class OtpRequest(BaseModel):
    phone: str


class OtpVerify(BaseModel):
    phone: str
    code: str


@router.post("/auth/whatsapp/request")
async def otp_request(body: OtpRequest):
    phone = norm_phone(body.phone)
    if len(phone) < 8:
        raise HTTPException(400, "Enter your full WhatsApp number with country code.")
    if not wa_configured():
        raise HTTPException(503, "WhatsApp sign-in isn't switched on yet. Please continue with email or Google.")
    recent = await db.otp.count_documents({"phone": phone, "created_at": {"$gt": iso(now() - timedelta(hours=1))}})
    if recent >= 5:
        raise HTTPException(429, "Too many codes. Please wait a while and try again.")
    code = f"{secrets.randbelow(1_000_000):06d}"
    await db.otp.insert_one({"otp_id": new_id("otp"), "phone": phone, "code_hash": hashlib.sha256(code.encode()).hexdigest(), "attempts": 0,
                             "used": False, "created_at": iso(), "expires_at": iso(now() + timedelta(minutes=10))})
    rec = await wa_send(to_phone=phone, text=f"{code} is your verification code.", template="konnto_login_code", params=[code], kind="login_code", force_template=True)
    if rec["status"] != "sent":
        raise HTTPException(502, "We couldn't send the code on WhatsApp. Please try email or Google.")
    return {"ok": True}


@router.post("/auth/whatsapp/verify")
async def otp_verify(body: OtpVerify):
    phone = norm_phone(body.phone)
    rec = await db.otp.find_one({"phone": phone, "used": False}, sort=[("created_at", -1)])
    if not rec or parse_iso(rec["expires_at"]) < now() or rec.get("attempts", 0) >= 5:
        raise HTTPException(401, "This code has expired. Ask for a new one.")
    if not hmac.compare_digest(rec["code_hash"], hashlib.sha256(body.code.strip().encode()).hexdigest()):
        await db.otp.update_one({"otp_id": rec["otp_id"]}, {"$inc": {"attempts": 1}})
        raise HTTPException(401, "That code isn't right.")
    await db.otp.update_one({"otp_id": rec["otp_id"]}, {"$set": {"used": True}})
    user = await db.users.find_one({"whatsapp": phone, "whatsapp_verified": True}, {"_id": 0})
    if not user:
        contact = await db.wa_contacts.find_one({"wa_id": digits(phone)}) or {}
        user = {"user_id": f"wa_{digits(phone)}", "auth": "whatsapp", "whatsapp": phone, "whatsapp_verified": True, "email": None,
                "name": contact.get("profile_name") or "", "role": "member", "env": ENV, "created_at": iso()}
        await db.users.update_one({"user_id": user["user_id"]}, {"$setOnInsert": user}, upsert=True)
    await db.members.update_many({"phone": phone, "user_id": None, "status": "active"}, {"$set": {"user_id": user["user_id"]}})
    await db.wa_contacts.update_one({"wa_id": digits(phone)}, {"$set": {"wa_id": digits(phone), "opted_out": False}}, upsert=True)
    return {"token": make_app_token(user["user_id"]), "user_id": user["user_id"]}
