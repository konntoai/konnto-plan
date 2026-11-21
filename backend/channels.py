"""Outbound channels: WhatsApp (Meta Cloud API, official), email backup (Emergent managed), and in-app notices."""
import os
import re
import ipaddress
import logging
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse
from typing import Optional

import httpx

from core import db, iso, now, new_id, parse_iso, app_link, digits, log_usage
from datetime import timedelta

logger = logging.getLogger("konnto.channels")

# ============================================================== EMAIL (backup channel)
EMAIL_BASE_URL = "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY", "")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "KONNTO AI")
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO")

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} != real link host {real!r} (G3)")


async def send_email(*, to: str, subject: str, html: str) -> tuple:
    """Internal helper; html always comes from server-side templates. Returns (ok, id_or_error)."""
    if not EMAIL_KEY or not to:
        return False, "email_not_configured"
    try:
        _assert_safe_email(subject, html)
    except ValueError as e:
        logger.error("Email blocked by guardrail: %s", e)
        return False, "blocked"
    payload = {"to": [to], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME}
    if EMAIL_REPLY_TO:
        payload["contact_email"] = EMAIL_REPLY_TO
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.post(f"{EMAIL_BASE_URL}/api/v1/email/send", headers={"X-Email-Key": EMAIL_KEY}, json=payload)
        if resp.status_code >= 400:
            try:
                code = resp.json().get("code", "")
            except ValueError:
                code = ""
            if code in ("insufficient_credits", "integration_disabled", "daily_limit_reached"):
                logger.warning("Email paused: %s (%s)", code, resp.status_code)
                return False, code
            logger.error("Email send failed: %s %s", resp.status_code, resp.text[:200])
            return False, f"http_{resp.status_code}"
        return True, resp.json().get("id")
    except Exception as e:
        logger.error("Email send error: %s", e)
        return False, "error"


def email_html(title: str, lines: list, cta_text: Optional[str] = None, cta_url: Optional[str] = None) -> str:
    body = "".join(f'<p style="margin:0 0 12px;font-size:15px;line-height:22px;color:#1F2937">{escape(str(line))}</p>' for line in lines if line)
    cta = ""
    if cta_text and cta_url and cta_url.startswith("https://"):
        cta = (f'<p style="margin:20px 0"><a href="{escape(cta_url)}" style="background:#0F766E;color:#ffffff;'
               f'text-decoration:none;padding:12px 18px;border-radius:10px;font-weight:600;display:inline-block">{escape(cta_text)}</a></p>')
    return (f'<table role="presentation" width="100%" style="background:#F7FAFB;padding:24px 0"><tr><td align="center">'
            f'<table role="presentation" width="560" style="background:#ffffff;border:1px solid #E3E8EF;border-radius:14px">'
            f'<tr><td style="padding:28px;font-family:Arial,Helvetica,sans-serif">'
            f'<p style="margin:0 0 6px;font-size:13px;font-weight:700;letter-spacing:1px;color:#0F766E">KONNTO AI</p>'
            f'<h1 style="margin:0 0 16px;font-size:20px;color:#1F2937">{escape(title)}</h1>{body}{cta}'
            f'<p style="margin:24px 0 0;font-size:12px;color:#5B6776">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password or payment details by email.</p>'
            f'</td></tr></table></td></tr></table>')


# ============================================================== WHATSAPP (official Meta Cloud API)

def wa_cfg() -> dict:
    return {
        "token": os.environ.get("META_ACCESS_TOKEN", ""),
        "phone_id": os.environ.get("META_PHONE_NUMBER_ID", ""),
        "app_secret": os.environ.get("META_APP_SECRET", ""),
        "verify": os.environ.get("META_WEBHOOK_VERIFY_TOKEN", ""),
        "display": digits(os.environ.get("META_DISPLAY_NUMBER", "")),
        "version": os.environ.get("META_GRAPH_VERSION", "v23.0"),
        "waba_id": os.environ.get("META_WABA_ID", ""),
    }


def wa_configured() -> bool:
    c = wa_cfg()
    return bool(c["token"] and c["phone_id"])


def wa_join_link(code: str) -> Optional[str]:
    c = wa_cfg()
    if not (wa_configured() and c["display"]):
        return None
    return f"https://wa.me/{c['display']}?text=JOIN%20{code}"


# Standard messages that must be approved by Meta (names are fixed; admin console lists them).
WA_TEMPLATES = {
    "konnto_welcome": {"category": "UTILITY", "body": "Hi {{1}}, welcome to KONNTO AI for {{2}}. Reply here any time with tasks, promises or questions.", "buttons": []},
    "konnto_reminder": {"category": "UTILITY", "body": "KONNTO reminder for {{1}}: {{2}}", "buttons": ["Done", "Delayed", "Need help"]},
    "konnto_task": {"category": "UTILITY", "body": "{{1}} from {{2}} needs this from you: {{3}}. Due: {{4}}", "buttons": ["Done", "Delayed", "Need help"]},
    "konnto_message": {"category": "UTILITY", "body": "New message from {{1}} ({{2}}): {{3}}", "buttons": []},
    "konnto_approval": {"category": "UTILITY", "body": "{{1}} asks for approval at {{2}}: {{3}}", "buttons": ["Allow once", "Always allow", "Don't allow"]},
    "konnto_brief": {"category": "UTILITY", "body": "Your KONNTO update for {{1}}: {{2}}", "buttons": []},
    "konnto_login_code": {"category": "AUTHENTICATION", "body": "{{1}} is your verification code.", "buttons": ["Copy code"]},
}


async def wa_post(payload: dict) -> tuple:
    c = wa_cfg()
    if not wa_configured():
        return False, None, "not_connected"
    try:
        async with httpx.AsyncClient(timeout=20) as cl:
            r = await cl.post(f"https://graph.facebook.com/{c['version']}/{c['phone_id']}/messages",
                              headers={"Authorization": f"Bearer {c['token']}"}, json=payload)
        if r.is_error:
            logger.warning("WhatsApp send failed %s: %s", r.status_code, r.text[:300])
            return False, None, f"http_{r.status_code}"
        data = r.json()
        wamid = ((data.get("messages") or [{}])[0]).get("id")
        return True, wamid, None
    except Exception as e:
        logger.error("WhatsApp error: %s", e)
        return False, None, "error"


async def wa_window_open(wa_id: str) -> bool:
    contact = await db.wa_contacts.find_one({"wa_id": wa_id})
    last = parse_iso((contact or {}).get("last_inbound_at"))
    return bool(last and last > now() - timedelta(hours=23, minutes=30))


async def wa_opted_out(wa_id: str) -> bool:
    contact = await db.wa_contacts.find_one({"wa_id": wa_id})
    return bool((contact or {}).get("opted_out"))


def _session_payload(to: str, text: str, buttons: Optional[list]) -> dict:
    if buttons:
        return {"messaging_product": "whatsapp", "to": to, "type": "interactive",
                "interactive": {"type": "button", "body": {"text": text[:1024]},
                                "action": {"buttons": [{"type": "reply", "reply": {"id": b["id"][:256], "title": b["label"][:20]}} for b in buttons[:3]]}}}
    return {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text[:4096], "preview_url": True}}


def _template_payload(to: str, name: str, params: list, buttons: Optional[list]) -> dict:
    comps = [{"type": "body", "parameters": [{"type": "text", "text": str(p)[:900]} for p in params]}]
    if name == "konnto_login_code":
        comps.append({"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": str(params[0])}]})
    else:
        for i, b in enumerate((buttons or [])[:3]):
            comps.append({"type": "button", "sub_type": "quick_reply", "index": str(i), "parameters": [{"type": "payload", "payload": b["id"]}]})
    return {"messaging_product": "whatsapp", "to": to, "type": "template",
            "template": {"name": name, "language": {"code": "en"}, "components": comps}}


async def wa_send(*, to_phone: str, text: str, buttons: Optional[list] = None, template: Optional[str] = None,
                  params: Optional[list] = None, org_id: Optional[str] = None, member_id: Optional[str] = None,
                  kind: str = "message", force_template: bool = False, extra: Optional[dict] = None) -> dict:
    """Send a WhatsApp message: session message inside the 24h window, approved template otherwise."""
    wa_id = digits(to_phone)
    rec = {"out_id": new_id("out"), "org_id": org_id, "member_id": member_id, "channel": "whatsapp", "kind": kind,
           "to": wa_id, "text": text[:500], "created_at": iso(), "status": "queued", **(extra or {})}
    if not wa_id:
        rec["status"] = "skipped_no_number"
    elif await wa_opted_out(wa_id):
        rec["status"] = "skipped_opted_out"
    elif not wa_configured():
        rec["status"] = "not_connected"
    else:
        use_session = (not force_template) and await wa_window_open(wa_id)
        if use_session:
            ok, wamid, err = await wa_post(_session_payload(wa_id, text, buttons))
            rec["mode"] = "session"
        elif template:
            ok, wamid, err = await wa_post(_template_payload(wa_id, template, params or [], buttons))
            rec["mode"] = "template"
            rec["template"] = template
        else:
            ok, wamid, err = False, None, "window_closed_no_template"
        rec["status"] = "sent" if ok else "failed"
        rec["wamid"] = wamid
        rec["error"] = err
        if ok:
            await log_usage(org_id, "whatsapp", "whatsapp", units=1, cost=0.0)
    await db.outbox.insert_one(dict(rec))
    rec.pop("_id", None)
    return rec


# ============================================================== NOTIFY (in-app + WhatsApp + email backup)

async def add_notice(org_id: str, member: dict, text: str, *, kind: str = "notice", buttons: Optional[list] = None,
                     link_path: Optional[str] = None, cards: Optional[list] = None) -> Optional[dict]:
    """Post a KONNTO message into a member's in-app chat (the same conversation as WhatsApp)."""
    msg = {"msg_id": new_id("bm"), "org_id": org_id, "member_id": member["member_id"], "role": "assistant",
           "kind": kind, "text": text, "buttons": buttons or [], "link_path": link_path, "cards": cards or [],
           "channel": "app", "created_at": iso(), "citations": []}
    await db.brain_messages.insert_one(dict(msg))
    return msg


async def notify(member: dict, *, org: dict, kind: str, text: str, buttons: Optional[list] = None,
                 template: Optional[str] = None, params: Optional[list] = None, email_subject: Optional[str] = None,
                 link_path: Optional[str] = None, in_app: bool = True, email_fallback: bool = True) -> dict:
    result = {"in_app": False, "whatsapp": None, "email": None}
    if in_app and member.get("user_id"):
        await add_notice(org["org_id"], member, text, kind=kind, buttons=buttons, link_path=link_path)
        result["in_app"] = True
    wa_status = None
    if member.get("phone") and member.get("wa_opt_in"):
        rec = await wa_send(to_phone=member["phone"], text=text, buttons=buttons, template=template, params=params,
                            org_id=org["org_id"], member_id=member["member_id"], kind=kind)
        wa_status = rec["status"]
    result["whatsapp"] = wa_status
    if org.get("is_demo"):  # the demo business never sends real email
        email_fallback = False
    if wa_status != "sent" and email_fallback and member.get("email"):
        url = app_link(link_path or "/app/chat")
        html = email_html(email_subject or "An update from KONNTO", [text], "Open KONNTO", url if url.startswith("https://") else None)
        ok, ref = await send_email(to=member["email"], subject=email_subject or f"KONNTO: {text[:60]}", html=html)
        await db.outbox.insert_one({"out_id": new_id("out"), "org_id": org["org_id"], "member_id": member["member_id"],
                                    "channel": "email", "kind": kind, "to": member["email"], "text": text[:500],
                                    "status": "sent" if ok else "failed", "error": None if ok else ref, "created_at": iso()})
        result["email"] = "sent" if ok else "failed"
    return result
