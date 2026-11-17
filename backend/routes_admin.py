"""KONNTO admin console (platform settings + teaching the AI) and public website content.
The admin can change all platform settings and the AI but never reads customers' business data."""
import json
import time
from datetime import timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core import db, now, iso, new_id, require_admin, platform_settings
from channels import wa_configured, wa_cfg, WA_TEMPLATES
import brain

router = APIRouter(prefix="/api")
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

SITE_DEFAULT = {
    "hero_title": "Talk to KONNTO. It remembers. It acts.",
    "hero_subtitle": "One AI brain for your whole business. Send a message on WhatsApp or in the app — KONNTO turns it into tasks, promises and reminders, tells the right people, and follows up.",
    "hero_cta": "Start free",
    "proof_points": ["WhatsApp-first", "Answers with sources", "One-tap Save"],
    "how_title": "How it works",
    "steps": [
        {"title": "Talk", "body": "Type, send a voice note in any language, or share a photo or document."},
        {"title": "K-BRAIN thinks", "body": "It understands tasks, promises, dates, people and amounts — and remembers your business."},
        {"title": "It acts", "body": "It saves, reminds, messages the right person, asks you for approvals and sends a morning brief."},
    ],
    "whatsapp_title": "Your team already lives on WhatsApp. So does KONNTO.",
    "whatsapp_body": "Short messages, at most three buttons. Done, Delayed, Need help. Suppliers and contractors never need to install anything — and they are always free.",
    "industries_title": "Built for any business, anywhere",
    "industries": ["Retail & wholesale", "Construction & contractors", "Clinics & salons", "Agencies & studios", "Logistics & transport", "Manufacturing", "Restaurants", "Services"],
    "trust_title": "Calm, private, in your control",
    "trust": [
        {"title": "Right people, right access", "body": "KONNTO starts small and asks you before anyone sees money, staff details or more."},
        {"title": "Approvals you can undo", "body": "Allow once, always allow, or don't allow — and undo any time."},
        {"title": "Private stays private", "body": "Personal notes and one-to-one chats are only for the people in them."},
        {"title": "Your data, your call", "body": "View, export or delete your data whenever you want."},
    ],
    "final_title": "Start with one number.",
    "final_body": "Sign up, add your WhatsApp number, and just start talking.",
    "footer_note": "KONNTO AI — one AI brain for every business.",
}


async def get_site() -> dict:
    doc = await db.platform_config.find_one({"_id": "site"})
    return {**SITE_DEFAULT, **((doc or {}).get("content") or {})}


@router.get("/public/site")
async def public_site():
    return {"site": await get_site(), "whatsapp_connected": wa_configured()}


@router.get("/whatsapp/status")
async def whatsapp_status():
    c = wa_cfg()
    return {"configured": wa_configured(), "display_number": c["display"] or None}


# ---------------------------------------------------------------- public help assistant (rate limited)
_RATE = {}


class HelpIn(BaseModel):
    text: str
    history: List[dict] = []


@router.post("/public/help")
async def public_help(body: HelpIn, request: Request):
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[0].strip()
    window = int(time.time() // 3600)
    key = f"{ip}:{window}"
    _RATE[key] = _RATE.get(key, 0) + 1
    if _RATE[key] > 25:
        raise HTTPException(429, "Too many questions for now. Please try again later.")
    cfg = await brain.get_brain_config()

    async def gen():
        async for d in brain.stream_help(body.text[:1500], body.history[-6:], cfg, None):
            yield f"data: {json.dumps({'type': 'delta', 'text': d})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)


# ---------------------------------------------------------------- teach the AI: draft / test / publish / undo
class BrainIn(BaseModel):
    personality: Optional[str] = None
    rules: Optional[str] = None
    knowledge: Optional[str] = None
    faqs: Optional[List[dict]] = None
    pricing_answers: Optional[str] = None
    welcome_message: Optional[str] = None


@router.get("/admin/brain")
async def admin_brain(admin: dict = Depends(require_admin)):
    doc = await db.platform_config.find_one({"_id": "brain"}) or {}
    published = {**brain.DEFAULT_BRAIN, **(doc.get("published") or {})}
    draft = {**published, **(doc.get("draft") or {})}
    return {"draft": draft, "published": published, "has_unpublished": bool(doc.get("draft")) and doc.get("draft") != doc.get("published"),
            "published_at": doc.get("published_at"), "version": doc.get("version", 0)}


@router.put("/admin/brain")
async def save_brain_draft(body: BrainIn, admin: dict = Depends(require_admin)):
    doc = await db.platform_config.find_one({"_id": "brain"}) or {}
    current = {**brain.DEFAULT_BRAIN, **(doc.get("published") or {}), **(doc.get("draft") or {})}
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if "faqs" in upd:
        upd["faqs"] = [{"q": str(f.get("q", ""))[:300], "a": str(f.get("a", ""))[:1500]} for f in upd["faqs"] if f.get("q")]
    draft = {**current, **upd}
    await db.platform_config.update_one({"_id": "brain"}, {"$set": {"draft": draft, "draft_saved_at": iso()}}, upsert=True)
    return {"draft": draft}


class TestIn(BaseModel):
    question: str
    mode: str = "help"  # help | business


@router.post("/admin/brain/test")
async def test_brain(body: TestIn, admin: dict = Depends(require_admin)):
    cfg = await brain.get_brain_config(draft=True)
    if body.mode == "business":
        fake_org = {"org_id": None, "name": "Sample Traders", "industry": "wholesale", "timezone": "Asia/Kolkata", "currency": "INR"}
        fake_member = {"name": "Priya", "member_type": "owner", "job": "Owner"}
        system = brain.reply_system(fake_org, fake_member, cfg, [], [])
    else:
        system = brain.help_system(cfg)
    text = await brain.complete_text(system, body.question[:1500], None, "admin_test")
    return {"answer": text or "No answer (the AI call failed)."}


class PublishIn(BaseModel):
    note: Optional[str] = ""


@router.post("/admin/brain/publish")
async def publish_brain(body: PublishIn, admin: dict = Depends(require_admin)):
    doc = await db.platform_config.find_one({"_id": "brain"}) or {}
    draft = doc.get("draft") or doc.get("published") or dict(brain.DEFAULT_BRAIN)
    version = int(doc.get("version", 0)) + 1
    await db.brain_versions.insert_one({"version_id": new_id("ver"), "version": version, "config": draft, "note": (body.note or "")[:200],
                                        "published_by": admin.get("email"), "published_at": iso()})
    await db.platform_config.update_one({"_id": "brain"}, {"$set": {"published": draft, "draft": draft, "version": version, "published_at": iso()}}, upsert=True)
    return {"ok": True, "version": version}


@router.get("/admin/brain/versions")
async def brain_versions(admin: dict = Depends(require_admin)):
    vs = await db.brain_versions.find({}, {"_id": 0}).sort("version", -1).to_list(100)
    return {"versions": vs}


@router.post("/admin/brain/restore/{version_id}")
async def restore_brain(version_id: str, admin: dict = Depends(require_admin)):
    v = await db.brain_versions.find_one({"version_id": version_id}, {"_id": 0})
    if not v:
        raise HTTPException(404, "Not found")
    await db.platform_config.update_one({"_id": "brain"}, {"$set": {"draft": v["config"]}}, upsert=True)
    return {"ok": True, "draft": v["config"], "message": f"Version {v['version']} loaded as draft. Publish to make it live."}


# ---------------------------------------------------------------- website text
@router.get("/admin/site")
async def admin_site(admin: dict = Depends(require_admin)):
    versions = await db.site_versions.find({}, {"_id": 0}).sort("saved_at", -1).to_list(20)
    return {"site": await get_site(), "versions": versions}


class SiteIn(BaseModel):
    content: dict


@router.put("/admin/site")
async def save_site(body: SiteIn, admin: dict = Depends(require_admin)):
    prev = await get_site()
    allowed = {k: v for k, v in body.content.items() if k in SITE_DEFAULT}
    await db.site_versions.insert_one({"version_id": new_id("sv"), "content": prev, "saved_by": admin.get("email"), "saved_at": iso()})
    await db.platform_config.update_one({"_id": "site"}, {"$set": {"content": {**prev, **allowed}, "saved_at": iso()}}, upsert=True)
    return {"site": await get_site()}


@router.post("/admin/site/restore/{version_id}")
async def restore_site(version_id: str, admin: dict = Depends(require_admin)):
    v = await db.site_versions.find_one({"version_id": version_id}, {"_id": 0})
    if not v:
        raise HTTPException(404, "Not found")
    await db.platform_config.update_one({"_id": "site"}, {"$set": {"content": v["content"]}}, upsert=True)
    return {"site": await get_site()}


# ---------------------------------------------------------------- plans & prices (hidden from customers)
class PlanIn(BaseModel):
    name: str
    category: str = "Standard"
    billing: str = "flat"  # flat | per_seat | custom
    price: Optional[float] = None
    currency: str = "USD"
    interval: str = "month"
    seats_included: Optional[int] = None
    features: List[str] = []
    limits: dict = {}
    visible: bool = False


@router.get("/admin/plans")
async def list_plans(admin: dict = Depends(require_admin)):
    plans = await db.plans.find({"archived": {"$ne": True}}, {"_id": 0}).sort("created_at", 1).to_list(200)
    s = await platform_settings()
    return {"plans": plans, "categories": s.get("plan_categories") or ["Starter", "Standard", "Business", "Partner (free)"], "show_pricing": s.get("show_pricing", False)}


@router.post("/admin/plans")
async def create_plan(body: PlanIn, admin: dict = Depends(require_admin)):
    p = {"plan_id": new_id("pln"), **body.model_dump(), "created_at": iso(), "updated_at": iso()}
    await db.plans.insert_one(dict(p))
    p.pop("_id", None)
    return p


@router.put("/admin/plans/{plan_id}")
async def update_plan(plan_id: str, body: PlanIn, admin: dict = Depends(require_admin)):
    r = await db.plans.update_one({"plan_id": plan_id}, {"$set": {**body.model_dump(), "updated_at": iso()}})
    if not r.matched_count:
        raise HTTPException(404, "Not found")
    return await db.plans.find_one({"plan_id": plan_id}, {"_id": 0})


@router.delete("/admin/plans/{plan_id}")
async def archive_plan(plan_id: str, admin: dict = Depends(require_admin)):
    await db.plans.update_one({"plan_id": plan_id}, {"$set": {"archived": True}})
    return {"ok": True}


class PlanSettingsIn(BaseModel):
    categories: List[str]


@router.put("/admin/plan-settings")
async def plan_settings(body: PlanSettingsIn, admin: dict = Depends(require_admin)):
    cats = [c.strip()[:40] for c in body.categories if c.strip()]
    await db.settings.update_one({"_id": "platform"}, {"$set": {"plan_categories": cats, "show_pricing": False}}, upsert=True)
    return {"categories": cats}


# ---------------------------------------------------------------- platform settings (limits) + whatsapp status
class SettingsIn(BaseModel):
    default_monthly_ai_messages: Optional[int] = None
    default_monthly_whatsapp: Optional[int] = None


@router.get("/admin/settings")
async def get_settings(admin: dict = Depends(require_admin)):
    s = await platform_settings()
    c = wa_cfg()
    from core import app_link
    return {"settings": s, "whatsapp": {"configured": wa_configured(), "display_number": c["display"] or None,
                                        "webhook_url": app_link("/api/webhooks/whatsapp"), "verify_token": c["verify"],
                                        "app_secret_set": bool(c["app_secret"]),
                                        "templates": [{"name": k, **v} for k, v in WA_TEMPLATES.items()]}}


@router.put("/admin/settings")
async def put_settings(body: SettingsIn, admin: dict = Depends(require_admin)):
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if upd:
        await db.settings.update_one({"_id": "platform"}, {"$set": upd}, upsert=True)
    return {"settings": await platform_settings()}


# ---------------------------------------------------------------- customers & usage (no business content)
@router.get("/admin/customers")
async def customers(admin: dict = Depends(require_admin)):
    month = now().strftime("%Y-%m")
    orgs = await db.orgs.find({"deleted": {"$ne": True}}, {"_id": 0, "org_id": 1, "name": 1, "industry": 1, "country": 1, "created_at": 1, "limits": 1, "owner_user_id": 1}).sort("created_at", -1).to_list(1000)
    s = await platform_settings()
    usage = {u["_id"]: u async for u in db.usage.aggregate([
        {"$match": {"month": month}},
        {"$group": {"_id": "$org_id", "cost": {"$sum": "$cost_usd"}, "ai_messages": {"$sum": {"$cond": [{"$in": ["$feature", ["brain_reply", "help"]]}, 1, 0]}},
                    "whatsapp": {"$sum": {"$cond": [{"$eq": ["$feature", "whatsapp"]}, 1, 0]}}, "tokens": {"$sum": {"$add": ["$input_tokens", "$output_tokens"]}}}}])}
    owners = {u["user_id"]: u for u in await db.users.find({"user_id": {"$in": [o.get("owner_user_id") for o in orgs]}}, {"_id": 0, "user_id": 1, "email": 1, "name": 1}).to_list(1000)}
    out = []
    for o in orgs:
        u = usage.get(o["org_id"], {})
        out.append({**{k: o.get(k) for k in ("org_id", "name", "industry", "country", "created_at")},
                    "owner": (owners.get(o.get("owner_user_id")) or {}).get("email"),
                    "members": await db.members.count_documents({"org_id": o["org_id"], "status": "active"}),
                    "ai_messages_month": u.get("ai_messages", 0), "whatsapp_month": u.get("whatsapp", 0), "tokens_month": u.get("tokens", 0),
                    "ai_cost_month_usd": round(u.get("cost", 0), 4),
                    "limit_ai_messages": (o.get("limits") or {}).get("monthly_ai_messages") or s["default_monthly_ai_messages"],
                    "custom_limit": bool((o.get("limits") or {}).get("monthly_ai_messages"))})
    return {"customers": out}


class LimitIn(BaseModel):
    monthly_ai_messages: Optional[int] = None


@router.put("/admin/customers/{org_id}/limits")
async def set_limits(org_id: str, body: LimitIn, admin: dict = Depends(require_admin)):
    r = await db.orgs.update_one({"org_id": org_id}, {"$set": {"limits.monthly_ai_messages": body.monthly_ai_messages}})
    if not r.matched_count:
        raise HTTPException(404, "Not found")
    return {"ok": True}


@router.get("/admin/usage")
async def usage(days: int = 30, admin: dict = Depends(require_admin)):
    since = iso(now() - timedelta(days=days))
    by_day = [d async for d in db.usage.aggregate([
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {"_id": {"$substr": ["$created_at", 0, 10]}, "cost": {"$sum": "$cost_usd"},
                    "ai": {"$sum": {"$cond": [{"$in": ["$feature", ["brain_reply", "help"]]}, 1, 0]}},
                    "whatsapp": {"$sum": {"$cond": [{"$eq": ["$feature", "whatsapp"]}, 1, 0]}}}},
        {"$sort": {"_id": 1}}])]
    by_feature = [d async for d in db.usage.aggregate([
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {"_id": "$feature", "cost": {"$sum": "$cost_usd"}, "count": {"$sum": 1}}}, {"$sort": {"cost": -1}}])]
    wa = [d async for d in db.outbox.aggregate([{"$match": {"created_at": {"$gte": since}}}, {"$group": {"_id": {"channel": "$channel", "status": "$status"}, "count": {"$sum": 1}}}])]
    totals = {"orgs": await db.orgs.count_documents({"deleted": {"$ne": True}}), "users": await db.users.count_documents({}),
              "members": await db.members.count_documents({"status": "active"}),
              "ai_cost": round(sum(d["cost"] for d in by_day), 4), "ai_messages": sum(d["ai"] for d in by_day), "whatsapp_sent": sum(d["whatsapp"] for d in by_day)}
    return {"by_day": [{"day": d["_id"], "cost": round(d["cost"], 4), "ai": d["ai"], "whatsapp": d["whatsapp"]} for d in by_day],
            "by_feature": [{"feature": d["_id"], "cost": round(d["cost"], 4), "count": d["count"]} for d in by_feature],
            "outbox": [{"channel": d["_id"]["channel"], "status": d["_id"]["status"], "count": d["count"]} for d in wa], "totals": totals}


# ---------------------------------------------------------------- feedback + announcements
@router.get("/admin/feedback")
async def list_feedback(admin: dict = Depends(require_admin)):
    return {"feedback": await db.feedback.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)}


class FbStatusIn(BaseModel):
    status: str


@router.patch("/admin/feedback/{feedback_id}")
async def feedback_status(feedback_id: str, body: FbStatusIn, admin: dict = Depends(require_admin)):
    await db.feedback.update_one({"feedback_id": feedback_id}, {"$set": {"status": body.status if body.status in ("new", "seen", "done") else "seen"}})
    return {"ok": True}


class AnnIn(BaseModel):
    title: str
    body: Optional[str] = ""
    active: bool = True
    ends_at: Optional[str] = None


@router.get("/admin/announcements")
async def list_ann(admin: dict = Depends(require_admin)):
    return {"announcements": await db.announcements.find({"archived": {"$ne": True}}, {"_id": 0}).sort("created_at", -1).to_list(200)}


@router.post("/admin/announcements")
async def create_ann(body: AnnIn, admin: dict = Depends(require_admin)):
    a = {"announcement_id": new_id("ann"), **body.model_dump(), "created_at": iso(), "created_by": admin.get("email")}
    await db.announcements.insert_one(dict(a))
    a.pop("_id", None)
    return a


@router.put("/admin/announcements/{ann_id}")
async def update_ann(ann_id: str, body: AnnIn, admin: dict = Depends(require_admin)):
    await db.announcements.update_one({"announcement_id": ann_id}, {"$set": body.model_dump()})
    return await db.announcements.find_one({"announcement_id": ann_id}, {"_id": 0})


@router.delete("/admin/announcements/{ann_id}")
async def delete_ann(ann_id: str, admin: dict = Depends(require_admin)):
    await db.announcements.update_one({"announcement_id": ann_id}, {"$set": {"archived": True, "active": False}})
    return {"ok": True}


# ---------------------------------------------------------------- demo workspace
@router.post("/admin/demo/reset")
async def reset_demo(admin: dict = Depends(require_admin)):
    """Rebuild the ready-made demo business (only touches the demo org)."""
    import demo_account
    return await demo_account.build_demo()
