"""WhatsApp go-live helpers for the admin console: check the Meta connection, submit KONNTO's templates, send a test."""
import logging
from typing import Optional

import httpx

from channels import wa_cfg, wa_configured, WA_TEMPLATES, digits

logger = logging.getLogger("konnto.wa_setup")

# Sample values Meta needs to review each template (one per {{n}}).
TEMPLATE_EXAMPLES = {
    "konnto_welcome": ["Priya", "Mehra Build Supplies"],
    "konnto_reminder": ["Priya", "Send the revised quote to Mehta Builders"],
    "konnto_task": ["Arjun", "Mehra Build Supplies", "Unload and count the cement delivery", "Thu 6:00 PM"],
    "konnto_message": ["Arjun", "Mehra Build Supplies", "Please send the delivery photos once unloaded"],
    "konnto_approval": ["Ramesh", "Mehra Build Supplies", "Spare parts for the forklift repair, Rs 8,500"],
    "konnto_brief": ["Mehra Build Supplies", "3 overdue, 2 due today, 5 approvals waiting"],
    "konnto_login_code": ["482913"],
}


def _base() -> str:
    return f"https://graph.facebook.com/{wa_cfg()['version']}"


def _headers() -> dict:
    return {"Authorization": f"Bearer {wa_cfg()['token']}"}


def _friendly(r: httpx.Response) -> str:
    try:
        err = r.json().get("error", {})
    except Exception:
        return f"Meta answered {r.status_code}"
    code, msg = err.get("code"), err.get("error_user_msg") or err.get("message") or ""
    hints = {190: "The access token has expired or is wrong — create a permanent System User token.",
             10: "The token is missing WhatsApp permissions (whatsapp_business_messaging / management).",
             200: "The token is missing WhatsApp permissions (whatsapp_business_messaging / management).",
             100: "An ID looks wrong — check the Phone Number ID and WhatsApp Business Account ID.",
             131030: "This phone isn't on the test number's allowed list — add it in Meta's API Setup.",
             131026: "That number can't receive WhatsApp messages (not on WhatsApp or app too old).",
             132000: "The template's values don't match what Meta approved.",
             132001: "That template isn't approved (or doesn't exist) yet."}
    return hints.get(code, msg or f"Meta answered {r.status_code}") + (f" (code {code})" if code else "")


async def check() -> dict:
    c = wa_cfg()
    out = {"configured": wa_configured(), "missing": [k for k, v in (("Access token", c["token"]), ("Phone Number ID", c["phone_id"]),
                                                                    ("App Secret", c["app_secret"]), ("WhatsApp Business Account ID", c["waba_id"]),
                                                                    ("Display number", c["display"])) if not v],
           "number": None, "templates": [], "errors": []}
    if not wa_configured():
        return out
    async with httpx.AsyncClient(timeout=20) as cl:
        r = await cl.get(f"{_base()}/{c['phone_id']}", headers=_headers(),
                         params={"fields": "display_phone_number,verified_name,quality_rating,code_verification_status,name_status"})
        if r.is_error:
            out["errors"].append("Number: " + _friendly(r))
        else:
            out["number"] = r.json()
        if c["waba_id"]:
            r = await cl.get(f"{_base()}/{c['waba_id']}/message_templates", headers=_headers(), params={"fields": "name,status,language,category", "limit": 200})
            if r.is_error:
                out["errors"].append("Templates: " + _friendly(r))
            else:
                found = {t["name"]: t for t in r.json().get("data", []) if t.get("language") == "en"}
                out["templates"] = [{"name": n, "category": v["category"], "body": v["body"],
                                     "status": (found.get(n) or {}).get("status", "NOT_SUBMITTED")} for n, v in WA_TEMPLATES.items()]
    return out


def _template_body(name: str, spec: dict) -> dict:
    if spec["category"] == "AUTHENTICATION":
        return {"name": name, "language": "en", "category": "AUTHENTICATION",
                "components": [{"type": "BODY", "add_security_recommendation": True}, {"type": "FOOTER", "code_expiration_minutes": 10},
                               {"type": "BUTTONS", "buttons": [{"type": "OTP", "otp_type": "COPY_CODE", "text": "Copy code"}]}]}
    comps = [{"type": "BODY", "text": spec["body"], "example": {"body_text": [TEMPLATE_EXAMPLES[name]]}}]
    if spec["buttons"]:
        comps.append({"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": b} for b in spec["buttons"]]})
    return {"name": name, "language": "en", "category": spec["category"], "components": comps}


async def submit_templates() -> dict:
    c = wa_cfg()
    if not (wa_configured() and c["waba_id"]):
        return {"ok": False, "results": [], "error": "Connect WhatsApp first (token, Phone Number ID and WhatsApp Business Account ID)."}
    status = {t["name"]: t["status"] for t in (await check()).get("templates", [])}
    results = []
    async with httpx.AsyncClient(timeout=30) as cl:
        for name, spec in WA_TEMPLATES.items():
            if status.get(name, "NOT_SUBMITTED") not in ("NOT_SUBMITTED", "REJECTED"):
                results.append({"name": name, "status": status[name], "note": "already submitted"})
                continue
            r = await cl.post(f"{_base()}/{c['waba_id']}/message_templates", headers=_headers(), json=_template_body(name, spec))
            if r.is_error:
                results.append({"name": name, "status": "FAILED", "note": _friendly(r)})
            else:
                results.append({"name": name, "status": r.json().get("status", "PENDING"), "note": "submitted"})
    return {"ok": all(x["status"] != "FAILED" for x in results), "results": results}


async def send_test(phone: str, text: Optional[str] = None) -> dict:
    """Uses Meta's pre-approved hello_world template, so it works even before KONNTO's own templates are approved."""
    c = wa_cfg()
    to = digits(phone)
    if not wa_configured():
        return {"ok": False, "error": "WhatsApp isn't connected yet."}
    if len(to) < 8:
        return {"ok": False, "error": "Enter the full number with country code."}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "template", "template": {"name": "hello_world", "language": {"code": "en_US"}}}
    if text:
        payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text[:1000]}}
    async with httpx.AsyncClient(timeout=20) as cl:
        r = await cl.post(f"{_base()}/{c['phone_id']}/messages", headers=_headers(), json=payload)
    if r.is_error:
        return {"ok": False, "error": _friendly(r)}
    return {"ok": True, "wamid": ((r.json().get("messages") or [{}])[0]).get("id")}
