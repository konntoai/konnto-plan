"""Shared plumbing: database, time helpers, auth (Clerk + KONNTO WhatsApp sessions), org context, permissions."""
import os
import re
import uuid
import logging
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import jwt as pyjwt  # noqa: E402
import requests  # noqa: E402
from fastapi import Depends, HTTPException, Request, Header  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from starlette.concurrency import run_in_threadpool  # noqa: E402

from clerk_auth import verify_session_token  # noqa: E402

logger = logging.getLogger("konnto")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

APP_JWT_SECRET = os.environ.get("APP_JWT_SECRET", "")
ENV = "live" if os.environ.get("CLERK_PUBLISHABLE_KEY", "").startswith("pk_live_") else "preview"

# ---------------------------------------------------------------- time helpers

def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: Optional[datetime] = None) -> str:
    dt = dt or now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def parse_iso(s) -> Optional[datetime]:
    if not s:
        return None
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    try:
        s2 = str(s).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def org_tz(org: Optional[dict]) -> ZoneInfo:
    try:
        return ZoneInfo((org or {}).get("timezone") or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def local_to_utc_iso(value, org: dict, default_hour: int = 9) -> Optional[str]:
    """LLM gives local times like 2026-11-18 or 2026-11-18T09:00. Convert to UTC ISO."""
    if not value:
        return None
    v = str(value).strip()
    tz = org_tz(org)
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            dt = datetime.fromisoformat(v).replace(hour=default_hour, tzinfo=tz)
        else:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
        return iso(dt)
    except Exception:
        return None


def fmt_local(value, org: dict, with_time: bool = True) -> str:
    dt = parse_iso(value)
    if not dt:
        return ""
    loc = dt.astimezone(org_tz(org))
    return loc.strftime("%a %d %b, %H:%M") if with_time else loc.strftime("%a %d %b")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:14]}"


def short_code(n: int = 6) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(n))


def clean(doc):
    if isinstance(doc, dict):
        doc.pop("_id", None)
    return doc


def digits(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def norm_phone(phone: str) -> str:
    d = digits(phone)
    return f"+{d}" if d else ""


# ---------------------------------------------------------------- public base url (for links in WhatsApp / email)
PUBLIC = {"base": os.environ.get("APP_PUBLIC_URL", "").rstrip("/")}


async def remember_base(request: Request):
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").split(",")[0].strip()
    if not host or host.startswith(("localhost", "127.", "0.0.0.0")) or ":" in host and host.split(":")[0] in ("localhost", "127.0.0.1"):
        return
    base = f"https://{host}"
    if PUBLIC["base"] != base:
        PUBLIC["base"] = base
        await db.settings.update_one({"_id": "public_base"}, {"$set": {"value": base}}, upsert=True)


async def load_base():
    if not PUBLIC["base"]:
        doc = await db.settings.find_one({"_id": "public_base"})
        if doc:
            PUBLIC["base"] = doc["value"]


def app_link(path: str) -> str:
    base = PUBLIC["base"] or ""
    return f"{base}{path}"


# ---------------------------------------------------------------- auth

def make_app_token(user_id: str, days: int = 30) -> str:
    return pyjwt.encode({"sub": user_id, "iss": "konnto", "exp": now() + timedelta(days=days)}, APP_JWT_SECRET, algorithm="HS256")


def _decode_app_token(token: str) -> Optional[dict]:
    try:
        return pyjwt.decode(token, APP_JWT_SECRET, algorithms=["HS256"], issuer="konnto")
    except pyjwt.PyJWTError:
        return None


def admin_emails() -> set:
    return {e.strip().lower() for e in os.environ.get("ADMIN_EMAIL", "").split(",") if e.strip()}


def _clerk_user_info(user_id: str) -> dict:
    r = requests.get(f"https://api.clerk.com/v1/users/{user_id}", timeout=10,
                     headers={"Authorization": f"Bearer {os.environ['CLERK_SECRET_KEY']}", "User-Agent": "konnto-app"})
    r.raise_for_status()
    data = r.json()
    emails = data.get("email_addresses") or []
    primary = next((e for e in emails if e.get("id") == data.get("primary_email_address_id")), emails[0] if emails else None)
    email = (primary or {}).get("email_address", "").lower()
    admins = admin_emails()
    is_admin = any(e["email_address"].lower() in admins and (e.get("verification") or {}).get("status") == "verified" for e in emails)
    name = " ".join(x for x in [data.get("first_name"), data.get("last_name")] if x) or (email.split("@")[0] if email else "")
    return {"email": email, "name": name, "admin": is_admin, "image": data.get("image_url")}


async def current_user(request: Request) -> dict:
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="Not signed in")
    claims = _decode_app_token(token) if APP_JWT_SECRET else None
    if claims:
        user = await db.users.find_one({"user_id": claims["sub"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="Session ended")
        return user
    if not os.environ.get("CLERK_SECRET_KEY"):
        raise HTTPException(status_code=503, detail="Sign-in is not configured")
    claims = verify_session_token(token)
    uid = claims["sub"]
    user = await db.users.find_one({"user_id": uid}, {"_id": 0})
    if user is None or not user.get("role"):
        info = await run_in_threadpool(_clerk_user_info, uid)
        role = "admin" if info["admin"] else "member"
        await db.users.update_one(
            {"user_id": uid},
            {"$setOnInsert": {"user_id": uid, "created_at": iso(), "auth": "clerk"},
             "$set": {"email": info["email"], "name": (user or {}).get("name") or info["name"], "role": role, "env": ENV, "image": info.get("image")}},
            upsert=True)
        user = await db.users.find_one({"user_id": uid}, {"_id": 0})
    if user.get("env") != ENV:
        await db.users.update_one({"user_id": uid}, {"$set": {"env": ENV}})
    return user


async def require_admin(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return user


# ---------------------------------------------------------------- org context & permissions
SCOPES = {
    "own_work": "Their own tasks and promises",
    "team_work": "Everyone's tasks and promises",
    "documents": "Business documents",
    "money": "Amounts, orders and payments",
    "staff": "Staff contact details",
    "approve": "Approve requests",
    "manage_team": "Add and manage people",
}
SENSITIVE_SCOPES = {"money", "staff", "approve", "manage_team"}
SAFE_SCOPES = {"own_work", "team_work", "documents"}


def has_scope(member: dict, scope: str) -> bool:
    if not member:
        return False
    if member.get("member_type") == "owner":
        return True
    if scope == "own_work":
        return True
    return scope in (member.get("access") or [])


def is_owner(member: dict) -> bool:
    return (member or {}).get("member_type") == "owner"


async def get_ctx(user: dict = Depends(current_user), x_org_id: Optional[str] = Header(None)) -> dict:
    org_id = x_org_id or user.get("current_org_id")
    member = None
    if org_id:
        member = await db.members.find_one({"org_id": org_id, "user_id": user["user_id"], "status": "active"}, {"_id": 0})
        # An explicitly selected organisation is a security boundary. Never silently
        # switch the request to another membership when that organisation is not accessible.
        if x_org_id and not member:
            raise HTTPException(status_code=403, detail="You do not have access to this organisation.")
    if not member:
        member = await db.members.find_one({"user_id": user["user_id"], "status": "active"}, {"_id": 0}, sort=[("joined_at", -1)])
        if not member:
            raise HTTPException(status_code=409, detail="needs_onboarding")
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"current_org_id": member["org_id"]}})
    org = await db.orgs.find_one({"org_id": member["org_id"], "deleted": {"$ne": True}}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=409, detail="needs_onboarding")
    return {"user": user, "member": member, "org": org}


def item_scope_query(member: dict) -> dict:
    """Mongo filter for the items a member may see (always org-scoped)."""
    mid = member["member_id"]
    base = {"org_id": member["org_id"], "deleted": {"$ne": True}}
    private_ok = {"$or": [{"visibility": {"$ne": "private"}}, {"created_by": mid}]}
    if has_scope(member, "team_work"):
        return {**base, **private_ok}
    return {**base, "$and": [private_ok, {"$or": [{"assignee_id": mid}, {"created_by": mid}, {"watchers": mid}]}]}


def doc_scope_query(member: dict) -> dict:
    mid = member["member_id"]
    base = {"org_id": member["org_id"], "is_deleted": {"$ne": True}}
    if has_scope(member, "documents"):
        return {**base, "$or": [{"visibility": {"$ne": "private"}}, {"uploaded_by": mid}]}
    return {**base, "uploaded_by": mid}


FINANCE_WORDS = re.compile(r"\b(cash|bank|revenue|profit|margin|margins|loan|loans|salary|salaries|payroll|turnover|lakh|lakhs|crore|crores|receivable|receivables|payable|payables|overdraft|ebitda|gst|tax|invoice total|balance)\b", re.I)


def fact_category(text: str, given: Optional[str] = None) -> str:
    if given:
        return given
    return "finance" if FINANCE_WORDS.search(text or "") else "other"


def fact_scope_query(member: dict) -> dict:
    """Business memory (knowledge facts) a member may read. Enforced server-side, never by the prompt."""
    base = {"org_id": member["org_id"], "deleted": {"$ne": True}}
    if member.get("member_type") == "partner":
        return {**base, "shared_with_partners": True}
    if not has_scope(member, "money"):
        return {**base, "category": {"$ne": "finance"}, "text": {"$not": FINANCE_WORDS}}
    return base


def can_read_rules(member: dict) -> bool:
    return member.get("member_type") != "partner"


def redact_item(item: dict, member: dict) -> dict:
    if item.get("amount") is not None and not has_scope(member, "money") and member["member_id"] not in (item.get("created_by"), item.get("assignee_id")):
        item = {**item, "amount": None, "amount_hidden": True}
    return item


def item_state(item: dict, ref: Optional[datetime] = None) -> str:
    ref = ref or now()
    st = item.get("status", "open")
    if st in ("done", "cancelled"):
        return st
    if st == "stuck":
        return "stuck"
    due = parse_iso(item.get("due_at"))
    if due and due < ref:
        return "overdue"
    if due and due < ref + timedelta(hours=24):
        return "due"
    return "open"


# ---------------------------------------------------------------- usage + limits
MODEL_PRICES = {  # USD per 1M tokens (in, out)
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
}


async def log_usage(org_id: Optional[str], feature: str, model: str, usage=None, units: float = 0.0, cost: Optional[float] = None):
    tin = getattr(usage, "input_tokens", 0) if usage else 0
    tout = getattr(usage, "output_tokens", 0) if usage else 0
    if cost is None:
        pin, pout = MODEL_PRICES.get(model, (3.0, 15.0))
        cost = (tin * pin + tout * pout) / 1_000_000
    await db.usage.insert_one({"usage_id": new_id("use"), "org_id": org_id, "feature": feature, "model": model,
                               "input_tokens": tin, "output_tokens": tout, "units": units, "cost_usd": round(cost, 6),
                               "created_at": iso(), "month": now().strftime("%Y-%m")})


async def platform_settings() -> dict:
    doc = await db.settings.find_one({"_id": "platform"}) or {}
    doc.pop("_id", None)
    return {"default_monthly_ai_messages": 3000, "default_monthly_whatsapp": 3000, "show_pricing": False, **doc}


async def ai_limit_reached(org: dict) -> bool:
    settings = await platform_settings()
    limit = ((org.get("limits") or {}).get("monthly_ai_messages")) or settings["default_monthly_ai_messages"]
    used = await db.usage.count_documents({"org_id": org["org_id"], "month": now().strftime("%Y-%m"), "feature": {"$in": ["brain_reply", "help"]}})
    return used >= int(limit)


async def audit(org_id: str, actor: str, action: str, details: dict = None):
    await db.audit.insert_one({"audit_id": new_id("aud"), "org_id": org_id, "actor": actor, "action": action,
                               "details": details or {}, "created_at": iso()})
