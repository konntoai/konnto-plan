"""KONNTO engine: the talk -> think -> act pipeline, work items, invites, approvals, rules, actions."""
import re
import math
import logging
from datetime import timedelta
from typing import Optional, AsyncGenerator

from core import (db, now, iso, parse_iso, new_id, short_code, local_to_utc_iso, fmt_local, app_link,
                  has_scope, is_owner, item_scope_query, doc_scope_query, redact_item, item_state, SCOPES,
                  SENSITIVE_SCOPES, ai_limit_reached, audit, norm_phone, digits)
from channels import notify, add_notice, wa_send, wa_join_link, wa_configured
import brain

logger = logging.getLogger("konnto.engine")

CURRENCY_SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "AED": "AED ", "SGD": "S$", "AUD": "A$", "NGN": "₦",
                    "KES": "KSh ", "ZAR": "R", "JPY": "¥", "CNY": "¥", "BDT": "৳", "PKR": "Rs ", "LKR": "Rs ", "NPR": "Rs ",
                    "IDR": "Rp ", "MYR": "RM ", "PHP": "₱", "SAR": "SAR ", "BRL": "R$", "MXN": "MX$", "CAD": "C$"}

COUNTRY_BY_PREFIX = [
    ("971", "AE", "AED", "Asia/Dubai"), ("966", "SA", "SAR", "Asia/Riyadh"), ("977", "NP", "NPR", "Asia/Kathmandu"),
    ("880", "BD", "BDT", "Asia/Dhaka"), ("234", "NG", "NGN", "Africa/Lagos"), ("254", "KE", "KES", "Africa/Nairobi"),
    ("91", "IN", "INR", "Asia/Kolkata"), ("92", "PK", "PKR", "Asia/Karachi"), ("94", "LK", "LKR", "Asia/Colombo"),
    ("44", "GB", "GBP", "Europe/London"), ("49", "DE", "EUR", "Europe/Berlin"), ("33", "FR", "EUR", "Europe/Paris"),
    ("65", "SG", "SGD", "Asia/Singapore"), ("61", "AU", "AUD", "Australia/Sydney"), ("62", "ID", "IDR", "Asia/Jakarta"),
    ("60", "MY", "MYR", "Asia/Kuala_Lumpur"), ("63", "PH", "PHP", "Asia/Manila"), ("27", "ZA", "ZAR", "Africa/Johannesburg"),
    ("55", "BR", "BRL", "America/Sao_Paulo"), ("52", "MX", "MXN", "America/Mexico_City"), ("1", "US", "USD", "America/New_York"),
]


def guess_country(phone: str) -> tuple:
    d = digits(phone)
    for prefix, country, cur, tz in COUNTRY_BY_PREFIX:
        if d.startswith(prefix):
            return country, cur, tz
    return None, "USD", "UTC"


def money(amount, currency: Optional[str]) -> str:
    if amount is None:
        return ""
    sym = CURRENCY_SYMBOLS.get((currency or "").upper(), (currency or "") + " ")
    try:
        val = float(amount)
        txt = f"{val:,.0f}" if val == int(val) else f"{val:,.2f}"
    except Exception:
        txt = str(amount)
    return f"{sym}{txt}"


def nice_ceiling(amount: float) -> float:
    if not amount or amount <= 0:
        return 0
    mag = 10 ** max(0, int(math.log10(amount)) - 1)
    return float(math.ceil(amount * 1.2 / mag) * mag)


# ================================================================ people & lookups
async def org_people(org_id: str, include_invited: bool = True) -> list:
    statuses = ["active", "invited"] if include_invited else ["active"]
    return await db.members.find({"org_id": org_id, "status": {"$in": statuses}}, {"_id": 0}).sort("created_at", 1).to_list(500)


def find_person(people: list, name: Optional[str], speaker: Optional[dict] = None) -> Optional[dict]:
    if not name:
        return None
    n = name.strip().lower()
    if n in ("me", "myself", "i", "self") and speaker:
        return speaker
    for p in people:
        if p["name"].lower() == n:
            return p
    for p in people:
        first = p["name"].lower().split()[0] if p["name"] else ""
        if first and (first == n.split()[0]):
            return p
    for p in people:
        if n in p["name"].lower() or (p.get("job") and n in p["job"].lower()):
            return p
    return None


def people_matching(people: list, target: Optional[str]) -> list:
    if not target:
        return []
    t = target.strip().lower()
    out = []
    for p in people:
        if p.get("status") != "active":
            continue
        if t in p["name"].lower() or (p.get("job") and (t in p["job"].lower() or p["job"].lower().split()[0:1] and t.rstrip("s") in p["job"].lower())):
            out.append(p)
    return out


async def approvers(org_id: str) -> list:
    members = await db.members.find({"org_id": org_id, "status": "active"}, {"_id": 0}).to_list(500)
    return [m for m in members if is_owner(m) or "approve" in (m.get("access") or [])]


async def owners(org_id: str) -> list:
    return await db.members.find({"org_id": org_id, "status": "active", "member_type": "owner"}, {"_id": 0}).to_list(20)


async def active_rules(org_id: str) -> list:
    return await db.rules.find({"org_id": org_id, "active": True}, {"_id": 0}).sort("created_at", -1).to_list(200)


async def visible_open_items(member: dict, limit: int = 40) -> list:
    q = {**item_scope_query(member), "status": {"$nin": ["done", "cancelled"]}}
    items = await db.items.find(q, {"_id": 0, "history": 0}).sort("due_at", 1).to_list(limit)
    return [redact_item(i, member) for i in items]


async def pending_approvals_for(member: dict) -> list:
    if not has_scope(member, "approve"):
        return []
    return await db.approvals.find({"org_id": member["org_id"], "status": "pending"}, {"_id": 0}).sort("created_at", -1).to_list(30)


# ================================================================ work items
TASK_BUTTONS = lambda iid: [{"id": f"done:{iid}", "label": "Done"}, {"id": f"delay:{iid}", "label": "Delayed"}, {"id": f"help:{iid}", "label": "Need help"}]


def _hist(actor_name: str, text: str) -> dict:
    return {"at": iso(), "by": actor_name, "text": text}


async def ensure_project(org_id: str, name: Optional[str], actor: dict) -> Optional[str]:
    if not name:
        return None
    existing = await db.projects.find_one({"org_id": org_id, "name": {"$regex": f"^{re.escape(name.strip())}$", "$options": "i"}})
    if existing:
        return existing["project_id"]
    pid = new_id("prj")
    await db.projects.insert_one({"project_id": pid, "org_id": org_id, "name": name.strip()[:80], "description": "", "status": "active",
                                  "created_by": actor["member_id"], "created_at": iso()})
    return pid


async def create_item(org: dict, actor: dict, data: dict, source: Optional[dict] = None, notify_assignee: bool = True) -> dict:
    people = await org_people(org["org_id"])
    assignee = None
    if data.get("assignee_id"):
        assignee = next((p for p in people if p["member_id"] == data["assignee_id"]), None)
    elif data.get("assignee"):
        assignee = find_person(people, data.get("assignee"), actor)
    kind = data.get("kind") or "task"
    if kind in ("reminder", "note") and not assignee:
        assignee = actor
    if not assignee and kind == "task":
        assignee = actor
    due_at = data.get("due_at_utc") or local_to_utc_iso(data.get("due_at"), org, default_hour=18)
    remind_at = data.get("remind_at_utc") or local_to_utc_iso(data.get("remind_at"), org, default_hour=9)
    if kind == "reminder" and not remind_at:
        remind_at = due_at or iso(now() + timedelta(hours=1))
    project_id = data.get("project_id") or await ensure_project(org["org_id"], data.get("project"), actor)
    item = {
        "item_id": new_id("itm"), "org_id": org["org_id"], "kind": kind,
        "title": (data.get("title") or "Untitled").strip()[:160], "details": (data.get("details") or "").strip()[:2000],
        "status": "open", "assignee_id": assignee["member_id"] if assignee else None,
        "assignee_name": assignee["name"] if assignee else None,
        "created_by": actor["member_id"], "created_by_name": actor["name"],
        "counterparty": data.get("counterparty"), "due_at": due_at, "remind_at": remind_at, "reminded_at": None,
        "amount": data.get("amount"), "currency": data.get("currency") or (org.get("currency") if data.get("amount") is not None else None),
        "depends_on": [d for d in (data.get("depends_on") or []) if d], "project_id": project_id,
        "is_request": bool(data.get("is_request")),
        "visibility": "private" if (kind == "note" and data.get("private", True)) or data.get("private") else "org",
        "watchers": [actor["member_id"]], "source": source or {"type": "app"}, "chase_level": 0, "last_chased_at": None,
        "delay_reason": None, "stuck_reason": None,
        "history": [_hist(actor["name"], f"Created{' for ' + assignee['name'] if assignee and assignee['member_id'] != actor['member_id'] else ''}")],
        "created_at": iso(), "updated_at": iso(), "done_at": None,
    }
    await db.items.insert_one(dict(item))
    item.pop("_id", None)
    await audit(org["org_id"], actor["member_id"], "item_created", {"item_id": item["item_id"], "title": item["title"]})
    if notify_assignee and assignee and assignee["member_id"] != actor["member_id"] and kind in ("task", "promise", "reminder"):
        await deliver_task(org, actor, assignee, item)
    await apply_behaviour_rules(org, "task", item, actor)
    return item


async def deliver_task(org: dict, actor: dict, assignee: dict, item: dict):
    due_txt = fmt_local(item.get("due_at"), org) or "no date"
    verb = "asks" if item.get("is_request") else "gave you"
    text = f"{actor['name']} {verb}: {item['title']}. Due {due_txt}."
    if item.get("is_request"):
        buttons = [{"id": f"accept:{item['item_id']}", "label": "Will do"}, {"id": f"decline:{item['item_id']}", "label": "Can't do"}, {"id": f"done:{item['item_id']}", "label": "Done"}]
    else:
        buttons = TASK_BUTTONS(item["item_id"])
    await notify(assignee, org=org, kind="task", text=text, buttons=buttons, template="konnto_task",
                 params=[actor["name"], org["name"], item["title"], due_txt], email_subject=f"New task from {actor['name']}",
                 link_path=f"/app/work?item={item['item_id']}")
    # also show it in their direct chat thread
    thread = await get_or_create_direct_thread(org["org_id"], actor, assignee)
    await db.thread_messages.insert_one({"msg_id": new_id("tm"), "thread_id": thread["thread_id"], "org_id": org["org_id"],
                                         "sender_id": actor["member_id"], "sender_name": actor["name"], "kind": "request" if item.get("is_request") else "task",
                                         "text": item["title"], "item_id": item["item_id"], "due_at": item.get("due_at"), "cards": [], "created_at": iso()})
    await db.threads.update_one({"thread_id": thread["thread_id"]}, {"$set": {"last_message_at": iso(), "last_message_preview": f"Task: {item['title']}"[:120]}})


async def get_item_for(member: dict, item_id: str) -> Optional[dict]:
    return await db.items.find_one({**item_scope_query(member), "item_id": item_id}, {"_id": 0})


def can_edit_item(member: dict, item: dict) -> bool:
    return is_owner(member) or member["member_id"] in (item.get("assignee_id"), item.get("created_by")) or has_scope(member, "team_work")


async def set_item_status(org: dict, actor: dict, item: dict, status: str, reason: Optional[str] = None,
                          new_due: Optional[str] = None, via: str = "app") -> dict:
    prev = {k: item.get(k) for k in ("status", "delay_reason", "stuck_reason", "due_at", "done_at", "chase_level")}
    upd = {"updated_at": iso()}
    text = ""
    if status == "done":
        upd.update({"status": "done", "done_at": iso()})
        text = "Marked done"
    elif status == "delayed":
        upd.update({"status": "in_progress", "delay_reason": reason, "chase_level": 0, "last_chased_at": None})
        if new_due:
            upd["due_at"] = new_due
        text = f"Delayed: {reason or 'no reason given'}" + (f" (new date {fmt_local(new_due, org)})" if new_due else "")
    elif status == "stuck":
        upd.update({"status": "stuck", "stuck_reason": reason})
        text = f"Stuck: {reason or 'no reason given'}"
    elif status == "in_progress":
        upd.update({"status": "in_progress"})
        text = "Started"
    elif status == "open":
        upd.update({"status": "open", "done_at": None})
        text = "Reopened"
    elif status == "cancelled":
        upd.update({"status": "cancelled"})
        text = "Cancelled"
    await db.items.update_one({"item_id": item["item_id"]}, {"$set": upd, "$push": {"history": _hist(actor["name"], text + (f" via {via}" if via != "app" else ""))}})
    item = await db.items.find_one({"item_id": item["item_id"]}, {"_id": 0})
    # tell the person waiting
    if item.get("created_by") and item["created_by"] != actor["member_id"]:
        creator = await db.members.find_one({"member_id": item["created_by"], "status": "active"}, {"_id": 0})
        if creator:
            if status == "done":
                msg = f"{actor['name']} finished: {item['title']}."
            elif status in ("delayed", "stuck"):
                msg = f"{actor['name']} — {item['title']}: {text}."
            else:
                msg = None
            if msg:
                await notify(creator, org=org, kind="update", text=msg, template="konnto_brief", params=[org["name"], msg],
                             email_subject=f"Update: {item['title'][:50]}", link_path=f"/app/work?item={item['item_id']}", email_fallback=status != "done")
    if status == "done":
        await release_dependents(org, item)
    return {"item": item, "prev": prev}


async def release_dependents(org: dict, item: dict):
    """When one task is done, tell the next person their task can start."""
    dependents = await db.items.find({"org_id": org["org_id"], "depends_on": item["item_id"], "status": {"$nin": ["done", "cancelled"]}}, {"_id": 0}).to_list(50)
    for dep in dependents:
        others = await db.items.count_documents({"item_id": {"$in": dep["depends_on"]}, "status": {"$ne": "done"}})
        if others:
            continue
        if dep.get("assignee_id"):
            m = await db.members.find_one({"member_id": dep["assignee_id"], "status": "active"}, {"_id": 0})
            if m:
                txt = f"Ready for you: {dep['title']}. '{item['title']}' is done."
                await notify(m, org=org, kind="task", text=txt, buttons=TASK_BUTTONS(dep["item_id"]), template="konnto_task",
                             params=["KONNTO", org["name"], dep["title"], fmt_local(dep.get("due_at"), org) or "no date"],
                             email_subject=f"You can start: {dep['title'][:50]}", link_path=f"/app/work?item={dep['item_id']}")
        await db.items.update_one({"item_id": dep["item_id"]}, {"$push": {"history": _hist("KONNTO", f"Unblocked: '{item['title']}' is done")}})


# ================================================================ rules
async def add_rule(org: dict, actor: dict, text: str, *, kind: str = "behaviour", trigger: str = "any", keyword: Optional[str] = None,
                   notify_target: Optional[str] = None, condition: Optional[dict] = None, source: str = "chat") -> dict:
    rule = {"rule_id": new_id("rul"), "org_id": org["org_id"], "text": text.strip()[:300], "kind": kind, "trigger": trigger or "any",
            "keyword": (keyword or "").strip().lower() or None, "notify_target": (notify_target or "").strip() or None,
            "condition": condition or {}, "created_by": actor["member_id"], "created_by_name": actor["name"], "source": source,
            "active": True, "created_at": iso()}
    await db.rules.insert_one(dict(rule))
    rule.pop("_id", None)
    await audit(org["org_id"], actor["member_id"], "rule_added", {"rule_id": rule["rule_id"], "text": rule["text"]})
    return rule


async def apply_behaviour_rules(org: dict, trigger: str, item: dict, actor: Optional[dict] = None):
    rules = await db.rules.find({"org_id": org["org_id"], "active": True, "kind": "behaviour", "trigger": {"$in": [trigger, "any"]},
                                 "notify_target": {"$ne": None}}, {"_id": 0}).to_list(50)
    if not rules:
        return
    people = await org_people(org["org_id"], include_invited=False)
    hay = f"{item.get('title', '')} {item.get('details', '')} {item.get('kind', '')}".lower()
    for r in rules:
        if r.get("keyword") and r["keyword"].rstrip("s") not in hay:
            continue
        for p in people_matching(people, r["notify_target"]):
            if p["member_id"] in (item.get("assignee_id"), (actor or {}).get("member_id")):
                continue
            label = "Reminder" if trigger == "reminder" else "New"
            await notify(p, org=org, kind="fyi", text=f"FYI ({r['text'][:60]}): {label} — {item['title']}.", template="konnto_brief",
                         params=[org["name"], f"{label}: {item['title']}"], email_subject=f"FYI: {item['title'][:50]}",
                         link_path=f"/app/work?item={item['item_id']}")


# ================================================================ invites
async def create_invite(org: dict, actor: dict, name: str, job: str, member_type: str = "team", phone: Optional[str] = None,
                        email: Optional[str] = None) -> dict:
    member_type = member_type if member_type in ("team", "partner") else "team"
    access = await brain.decide_access(org, name, job, member_type)
    token = new_id("inv") + short_code(10)
    code = short_code(6)
    m = {"member_id": new_id("mem"), "org_id": org["org_id"], "user_id": None, "name": name.strip()[:80], "job": (job or "").strip()[:120],
         "member_type": member_type, "phone": norm_phone(phone) if phone else None, "email": (email or "").strip().lower() or None,
         "access": access["scopes"], "access_reason": access["reason"], "status": "invited", "invite_token": token, "invite_code": code,
         "invited_by": actor["member_id"], "invited_by_name": actor["name"], "manager_id": actor["member_id"], "wa_opt_in": False,
         "created_at": iso(), "joined_at": None}
    await db.members.insert_one(dict(m))
    m.pop("_id", None)
    await audit(org["org_id"], actor["member_id"], "member_invited", {"member_id": m["member_id"], "name": m["name"]})
    return m


def invite_links(org: dict, m: dict) -> dict:
    from urllib.parse import quote
    url = app_link(f"/join/{m['invite_token']}")
    msg = f"Hi {m['name'].split()[0]}, {m.get('invited_by_name') or 'I'} added you to {org['name']} on KONNTO AI. Tap to join: {url}"
    share = f"https://wa.me/{digits(m['phone'])}?text={quote(msg)}" if m.get("phone") else f"https://wa.me/?text={quote(msg)}"
    return {"invite_url": url, "share_url": share, "share_text": msg, "wa_join_url": wa_join_link(m["invite_code"]), "invite_code": m["invite_code"]}


async def activate_member(org: dict, m: dict, *, user_id: Optional[str], phone: Optional[str], consent: bool, via: str) -> dict:
    upd = {"status": "active", "joined_at": iso(), "joined_via": via}
    if user_id:
        upd["user_id"] = user_id
    if phone:
        upd["phone"] = norm_phone(phone)
    if consent and (phone or m.get("phone")):
        upd["wa_opt_in"] = True
        upd["wa_opt_in_at"] = iso()
        upd["wa_opt_in_source"] = via
    await db.members.update_one({"member_id": m["member_id"]}, {"$set": upd, "$unset": {"invite_token": ""}})
    m = await db.members.find_one({"member_id": m["member_id"]}, {"_id": 0})
    if user_id:
        await db.users.update_one({"user_id": user_id}, {"$set": {"current_org_id": org["org_id"]}})
    cfg = await brain.get_brain_config()
    first = m["name"].split()[0]
    welcome = f"Hi {first}, welcome to {org['name']} on KONNTO. Message me any time — tasks, updates, questions. I'll keep track."
    await add_notice(org["org_id"], m, welcome, kind="welcome")
    if m.get("wa_opt_in"):
        await wa_send(to_phone=m["phone"], text=welcome, template="konnto_welcome", params=[first, org["name"]], org_id=org["org_id"],
                      member_id=m["member_id"], kind="welcome")
    inviter = await db.members.find_one({"member_id": m.get("invited_by"), "status": "active"}, {"_id": 0})
    if inviter:
        await notify(inviter, org=org, kind="joined", text=f"{m['name']} joined {org['name']}.", template="konnto_brief",
                     params=[org["name"], f"{m['name']} joined"], email_fallback=False, link_path="/app/team")
    await audit(org["org_id"], m["member_id"], "member_joined", {"via": via})
    return m


# ================================================================ team threads
async def get_or_create_direct_thread(org_id: str, a: dict, b: dict) -> dict:
    ids = sorted([a["member_id"], b["member_id"]])
    t = await db.threads.find_one({"org_id": org_id, "kind": "direct", "member_ids": ids}, {"_id": 0})
    if t:
        return t
    t = {"thread_id": new_id("thr"), "org_id": org_id, "kind": "direct", "member_ids": ids, "name": None, "created_by": a["member_id"],
         "created_at": iso(), "last_message_at": iso(), "last_message_preview": "", "reads": {}}
    await db.threads.insert_one(dict(t))
    t.pop("_id", None)
    return t


async def post_thread_message(org: dict, sender: dict, thread: dict, text: str, kind: str = "text", spot: bool = True) -> dict:
    msg = {"msg_id": new_id("tm"), "thread_id": thread["thread_id"], "org_id": org["org_id"], "sender_id": sender["member_id"],
           "sender_name": sender["name"], "kind": kind, "text": text.strip()[:4000], "item_id": None, "cards": [], "deliveries": [], "created_at": iso()}
    others = await db.members.find({"member_id": {"$in": [m for m in thread["member_ids"] if m != sender["member_id"]]}, "status": "active"}, {"_id": 0}).to_list(100)
    for o in others:
        status = None
        if o.get("phone") and o.get("wa_opt_in"):
            label = org["name"] if thread["kind"] == "direct" else f"{thread.get('name') or 'group'}, {org['name']}"
            rec = await wa_send(to_phone=o["phone"], text=f"{sender['name']} ({label}): {text[:900]}", template="konnto_message",
                                params=[sender["name"], label, text[:500]], org_id=org["org_id"], member_id=o["member_id"], kind="team_message",
                                extra={"thread_id": thread["thread_id"]})
            status = rec["status"]
        msg["deliveries"].append({"member_id": o["member_id"], "name": o["name"], "whatsapp": status, "app": bool(o.get("user_id"))})
    await db.thread_messages.insert_one(dict(msg))
    msg.pop("_id", None)
    await db.threads.update_one({"thread_id": thread["thread_id"]}, {"$set": {"last_message_at": iso(), "last_message_preview": f"{sender['name'].split()[0]}: {text[:100]}",
                                                                              f"reads.{sender['member_id']}": iso()}})
    return msg


async def spot_and_attach(org: dict, sender: dict, msg: dict):
    people = await org_people(org["org_id"])
    found = await brain.spot_commitments(org, sender["name"], msg["text"], [p["name"] for p in people])
    if not found:
        return
    cards = [{"card_id": new_id("crd"), "type": "proposal", "status": "pending", "data": {**f, "source_thread": msg["thread_id"]}} for f in found]
    await db.thread_messages.update_one({"msg_id": msg["msg_id"]}, {"$set": {"cards": cards}})


# ================================================================ approvals
KIND_LABEL = {"order": "order", "payment": "payment", "time_off": "time off", "work_done": "finished work", "access": "more access", "other": "request"}


async def match_permission_rule(org_id: str, requester_id: str, kind: str, amount) -> Optional[dict]:
    rules = await db.rules.find({"org_id": org_id, "active": True, "kind": "permission", "condition.approval_kind": kind}, {"_id": 0}).to_list(50)
    for r in rules:
        c = r.get("condition") or {}
        if c.get("member_id") not in (None, requester_id):
            continue
        if c.get("max_amount") is not None:
            if amount is None or float(amount) > float(c["max_amount"]):
                continue
        return r
    return None


async def create_approval(org: dict, requester: dict, *, kind: str, title: str, details: str = "", amount=None, currency=None,
                          scope: Optional[str] = None, question: Optional[str] = None, payload: Optional[dict] = None,
                          source: Optional[dict] = None) -> dict:
    kind = kind if kind in KIND_LABEL else "other"
    ap = {"approval_id": new_id("apr"), "org_id": org["org_id"], "kind": kind, "title": (title or KIND_LABEL[kind]).strip()[:200],
          "details": (details or "")[:1000], "amount": amount, "currency": currency or (org.get("currency") if amount is not None else None),
          "requested_by": requester["member_id"], "requested_by_name": requester["name"], "scope": scope, "question": question,
          "payload": payload or {}, "status": "pending", "decided_by": None, "decided_by_name": None, "decided_at": None,
          "decision_text": None, "rule_id": None, "source": source or {"type": "app"}, "created_at": iso()}
    rule = None if kind == "access" else await match_permission_rule(org["org_id"], requester["member_id"], kind, amount)
    if rule:
        ap.update({"status": "allowed_by_rule", "decided_by_name": "Business rule", "decided_at": iso(), "decision_text": rule["text"], "rule_id": rule["rule_id"]})
    await db.approvals.insert_one(dict(ap))
    ap.pop("_id", None)
    amt = f" ({money(amount, ap['currency'])})" if amount is not None else ""
    if rule:
        await notify(requester, org=org, kind="approval_result", text=f"Allowed: {ap['title']}{amt}. Your rule: {rule['text']}", in_app=False,
                     template="konnto_brief", params=[org["name"], f"Allowed: {ap['title']}"], email_fallback=False)
    else:
        buttons = [{"id": f"ap_once:{ap['approval_id']}", "label": "Allow once"}, {"id": f"ap_always:{ap['approval_id']}", "label": "Always allow"},
                   {"id": f"ap_deny:{ap['approval_id']}", "label": "Don't allow"}]
        for a in await approvers(org["org_id"]):
            if a["member_id"] == requester["member_id"]:
                continue
            await notify(a, org=org, kind="approval", text=f"{requester['name']} asks: {ap['title']}{amt}.", buttons=buttons, template="konnto_approval",
                         params=[requester["name"], org["name"], f"{ap['title']}{amt}"], email_subject=f"Approval needed: {ap['title'][:50]}",
                         link_path="/app/approvals")
        await apply_behaviour_rules(org, "approval", {"item_id": "", "title": ap["title"], "details": ap["details"], "kind": kind}, requester)
    return ap


def decision_summary(ap: dict, decision: str, max_amount=None) -> str:
    who = ap["requested_by_name"]
    if decision == "deny":
        return f"Not allowed: {who} — {ap['title']}."
    if decision == "once":
        return f"Allowed once: {who} — {ap['title']}."
    if ap["kind"] == "access":
        return f"{who} can now always see {SCOPES.get(ap.get('scope'), 'this').lower()}."
    if max_amount:
        return f"Done. {who} can always do {KIND_LABEL[ap['kind']]}s under {money(max_amount, ap.get('currency'))} without asking."
    return f"Done. {who} can always do this without asking: {KIND_LABEL[ap['kind']]}s."


async def decide_approval(org: dict, decider: dict, ap: dict, decision: str, max_amount=None, note: Optional[str] = None) -> dict:
    if ap["status"] != "pending":
        return {"approval": ap, "summary": "This was already decided.", "rule": None}
    status = {"once": "allowed_once", "always": "allowed_always", "deny": "denied"}[decision]
    rule = None
    upd = {"status": status, "decided_by": decider["member_id"], "decided_by_name": decider["name"], "decided_at": iso(), "decision_text": note}
    requester = await db.members.find_one({"member_id": ap["requested_by"]}, {"_id": 0})
    if decision == "always" and ap["kind"] == "access" and ap.get("scope") and requester:
        await db.members.update_one({"member_id": requester["member_id"]}, {"$addToSet": {"access": ap["scope"]}})
        upd["granted_scope"] = ap["scope"]
    elif decision == "always" and ap["kind"] != "access":
        if ap.get("amount") is not None and not max_amount:
            max_amount = nice_ceiling(float(ap["amount"]))
        text = f"{ap['requested_by_name']} may always do {KIND_LABEL[ap['kind']]}s" + (f" under {money(max_amount, ap.get('currency'))}" if max_amount else "") + " without asking"
        rule = await add_rule(org, decider, text, kind="permission", trigger="approval",
                              condition={"approval_kind": ap["kind"], "member_id": ap["requested_by"], "max_amount": max_amount}, source="approval")
        upd["rule_id"] = rule["rule_id"]
        upd["max_amount"] = max_amount
    await db.approvals.update_one({"approval_id": ap["approval_id"]}, {"$set": upd})
    ap = await db.approvals.find_one({"approval_id": ap["approval_id"]}, {"_id": 0})
    summary = decision_summary(ap, decision, max_amount)
    await audit(org["org_id"], decider["member_id"], "approval_decided", {"approval_id": ap["approval_id"], "decision": decision})
    if requester and requester.get("status") == "active":
        result_word = "Not allowed" if decision == "deny" else "Allowed"
        await notify(requester, org=org, kind="approval_result", text=f"{result_word} by {decider['name']}: {ap['title']}." + (f" Note: {note}" if note else ""),
                     template="konnto_brief", params=[org["name"], f"{result_word}: {ap['title']}"], email_subject=f"{result_word}: {ap['title'][:50]}",
                     link_path="/app/approvals")
        if decision in ("once", "always") and ap["kind"] == "access" and ap.get("question"):
            await answer_with_temp_scope(org, requester, ap.get("scope"), ap["question"])
        if decision in ("once", "always") and (ap.get("payload") or {}).get("action") == "invite":
            p = ap["payload"]
            m = await create_invite(org, decider, p.get("name"), p.get("job"), p.get("member_type", "team"))
            links = invite_links(org, m)
            await notify(requester, org=org, kind="invite", text=f"{m['name']} can join with this link: {links['invite_url']}", email_fallback=False)
    return {"approval": ap, "summary": summary, "rule": rule}


async def undo_decision(org: dict, actor: dict, ap: dict) -> dict:
    if ap["status"] not in ("allowed_once", "allowed_always", "denied"):
        return ap
    if ap.get("rule_id"):
        await db.rules.update_one({"rule_id": ap["rule_id"]}, {"$set": {"active": False, "removed_at": iso()}})
    if ap.get("granted_scope"):
        await db.members.update_one({"member_id": ap["requested_by"]}, {"$pull": {"access": ap["granted_scope"]}})
    await db.approvals.update_one({"approval_id": ap["approval_id"]}, {"$set": {"status": "pending", "decided_by": None, "decided_by_name": None, "decided_at": None,
                                                                                 "rule_id": None, "granted_scope": None, "max_amount": None}})
    await audit(org["org_id"], actor["member_id"], "approval_undone", {"approval_id": ap["approval_id"]})
    return await db.approvals.find_one({"approval_id": ap["approval_id"]}, {"_id": 0})


async def answer_with_temp_scope(org: dict, member: dict, scope: Optional[str], question: str):
    temp = {**member, "access": list(set((member.get("access") or []) + ([scope] if scope else [])))}
    cfg = await brain.get_brain_config()
    sources = await retrieve(org, temp, question, question)
    out = []
    async for d in brain.stream_reply(org, temp, question, cfg, sources, ["The owner allowed this answer once."], []):
        out.append(d)
    text = "".join(out).strip()
    await notify(member, org=org, kind="answer", text=f"You asked: {question[:120]}\n{text}", template="konnto_brief", params=[org["name"], text[:500]],
                 email_subject="Your answer from KONNTO")


# ================================================================ retrieval (permission-scoped business memory)
STOP = set("the a an and or to of for in on at by with is are was were be been this that these those what which who whom when where why how do does did "
           "can could should would will shall may might must have has had i me my we our you your he she it they them their there here from about into "
           "please tell show give get any all some today tomorrow".split())


def _words(*texts) -> list:
    words = []
    for t in texts:
        for w in re.findall(r"[\w₹$€£]{3,}", (t or "").lower()):
            if w not in STOP and w not in words:
                words.append(w)
    return words[:10]


def _snippet(text: str, words: list, width: int = 260) -> str:
    low = (text or "").lower()
    for w in words:
        i = low.find(w)
        if i >= 0:
            s = max(0, i - 80)
            return ("…" if s else "") + text[s:s + width].replace("\n", " ") + "…"
    return (text or "")[:width].replace("\n", " ")


async def retrieve(org: dict, member: dict, query: str, text: str, include_open: bool = True) -> list:
    words = _words(query, text)
    sources = []
    seen = set()

    def add(type_, id_, title, snippet, link):
        if (type_, id_) in seen or len(sources) >= 28:
            return
        seen.add((type_, id_))
        sources.append({"n": len(sources) + 1, "type": type_, "id": id_, "title": title[:120], "snippet": snippet, "link": link})

    def item_snip(i):
        i = redact_item(i, member)
        parts = [f"{i.get('kind')}", f"status {item_state(i)}", f"for {i.get('assignee_name') or '-'}", f"by {i.get('created_by_name')}"]
        if i.get("due_at"):
            parts.append(f"due {fmt_local(i['due_at'], org)}")
        if i.get("counterparty"):
            parts.append(f"with {i['counterparty']}")
        if i.get("amount") is not None:
            parts.append(f"amount {money(i['amount'], i.get('currency'))}")
        if i.get("delay_reason"):
            parts.append(f"delay reason: {i['delay_reason']}")
        if i.get("stuck_reason"):
            parts.append(f"stuck: {i['stuck_reason']}")
        if i.get("details"):
            parts.append(i["details"][:160])
        return ", ".join(parts)

    if words:
        rx = {"$regex": "|".join(re.escape(w) for w in words), "$options": "i"}
        for i in await db.items.find({**item_scope_query(member), "$or": [{"title": rx}, {"details": rx}, {"counterparty": rx}, {"assignee_name": rx}]},
                                     {"_id": 0, "history": 0}).sort("updated_at", -1).to_list(10):
            add("work", i["item_id"], i["title"], item_snip(i), f"/app/work?item={i['item_id']}")
        for d in await db.documents.find({**doc_scope_query(member), "$or": [{"filename": rx}, {"summary": rx}, {"text": rx}]}, {"_id": 0}).to_list(4):
            kd = "; ".join(f"{k['label']}: {k['value']}" for k in (d.get("key_details") or [])[:8])
            add("document", d["doc_id"], d["filename"], f"{d.get('summary', '')[:200]} {kd} {_snippet(d.get('text', ''), words)}", f"/app/documents?doc={d['doc_id']}")
        for f in await db.knowledge.find({"org_id": org["org_id"], "deleted": {"$ne": True}, "text": rx}, {"_id": 0}).to_list(5):
            add("fact", f["fact_id"], f["text"][:80], f["text"], "/app/knowledge")
        threads = await db.threads.find({"org_id": org["org_id"], "member_ids": member["member_id"]}, {"thread_id": 1, "_id": 0}).to_list(200)
        if threads:
            for tm in await db.thread_messages.find({"thread_id": {"$in": [t["thread_id"] for t in threads]}, "text": rx}, {"_id": 0}).sort("created_at", -1).to_list(4):
                add("chat", tm["msg_id"], f"{tm['sender_name']} in team chat", f"{fmt_local(tm['created_at'], org)}: {tm['text'][:220]}", f"/app/team/thread/{tm['thread_id']}")
    if include_open:
        for i in await visible_open_items(member, 15):
            add("work", i["item_id"], i["title"], item_snip(i), f"/app/work?item={i['item_id']}")
    if has_scope(member, "approve"):
        for a in await db.approvals.find({"org_id": org["org_id"], "status": "pending"}, {"_id": 0}).to_list(5):
            add("approval", a["approval_id"], f"Approval: {a['title']}", f"asked by {a['requested_by_name']}, {a['kind']}" + (f", {money(a.get('amount'), a.get('currency'))}" if a.get('amount') is not None else ""), "/app/approvals")
    return sources


# ================================================================ the pipeline: talk -> think -> act

async def _history(member: dict, limit: int = 10) -> list:
    msgs = await db.brain_messages.find({"org_id": member["org_id"], "member_id": member["member_id"]}, {"_id": 0, "role": 1, "text": 1}).sort("created_at", -1).to_list(limit)
    msgs.reverse()
    # Anthropic needs alternating turns starting with user: merge runs, drop leading assistant turns
    merged = []
    for m in msgs:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["text"] = (merged[-1]["text"] or "") + "\n" + (m.get("text") or "")
        else:
            merged.append({"role": m["role"], "text": m.get("text") or ""})
    while merged and merged[0]["role"] != "user":
        merged.pop(0)
    if merged and merged[-1]["role"] == "user":
        merged.pop()
    return merged


def _proposal_data(org: dict, it: dict, people: list, speaker: dict) -> dict:
    assignee = find_person(people, it.get("assignee"), speaker) if it.get("assignee") else None
    kind = it.get("kind") or "task"
    if not assignee and kind in ("reminder", "note", "task"):
        assignee = speaker
    if kind == "promise" and not assignee and it.get("assignee") and not it.get("counterparty"):
        it["counterparty"] = it.get("assignee")
    return {"kind": kind, "title": (it.get("title") or "")[:160], "details": it.get("details") or "",
            "assignee_id": assignee["member_id"] if assignee else None,
            "assignee_name": assignee["name"] if assignee else None,
            "counterparty": it.get("counterparty"),
            "due_at": local_to_utc_iso(it.get("due_at"), org, default_hour=18),
            "remind_at": local_to_utc_iso(it.get("remind_at"), org, default_hour=9),
            "amount": it.get("amount"), "currency": it.get("currency") or (org.get("currency") if it.get("amount") is not None else None),
            "project": it.get("project"), "private": bool(it.get("private")) or kind == "note"}


async def execute_actions(org: dict, member: dict, analysis: dict, people: list, source: dict) -> tuple:
    cards, summaries = [], []
    for it in (analysis.get("items") or [])[:6]:
        if not it.get("title"):
            continue
        data = _proposal_data(org, it, people, member)
        cards.append({"card_id": new_id("crd"), "type": "proposal", "status": "pending", "data": data})
        summaries.append(f"Prepared (NOT saved yet — the person must tap Save) a {data['kind']}: {data['title']}")

    for a in (analysis.get("actions") or [])[:6]:
        t = a.get("type")
        try:
            if t == "invite_person" and a.get("name"):
                existing = find_person(people, a["name"])
                if existing and existing["name"].lower().split()[0] == a["name"].lower().split()[0]:
                    links = invite_links(org, existing) if existing.get("status") == "invited" and existing.get("invite_token") else None
                    cards.append({"card_id": new_id("crd"), "type": "invite", "status": "exists", "data": {"member_id": existing["member_id"], "name": existing["name"], "job": existing.get("job"),
                                  "member_type": existing.get("member_type"), "joined": existing.get("status") == "active", **(links or {})}})
                    summaries.append(f"{existing['name']} is already in the business ({existing.get('status')})")
                elif has_scope(member, "manage_team"):
                    m = await create_invite(org, member, a["name"], a.get("job") or "", a.get("member_type") or "team", a.get("phone"))
                    people.append(m)
                    cards.append({"card_id": new_id("crd"), "type": "invite", "status": "created", "data": {"member_id": m["member_id"], "name": m["name"], "job": m["job"],
                                  "member_type": m["member_type"], "access": m["access"], "access_reason": m["access_reason"], **invite_links(org, m)}})
                    summaries.append(f"Created an invite link for {m['name']} ({m['job']}). Access: {m['access_reason']}")
                else:
                    ap = await create_approval(org, member, kind="other", title=f"Add {a['name']} ({a.get('job') or 'new person'}) to the team",
                                               payload={"action": "invite", "name": a["name"], "job": a.get("job"), "member_type": a.get("member_type") or "team"}, source=source)
                    cards.append({"card_id": new_id("crd"), "type": "approval", "status": ap["status"], "data": {"approval_id": ap["approval_id"], "title": ap["title"]}})
                    summaries.append("Asked the owner to approve adding this person")
            elif t == "message_person" and a.get("person") and a.get("text"):
                p = find_person(people, a["person"], member)
                if p and p["member_id"] != member["member_id"]:
                    thread = await get_or_create_direct_thread(org["org_id"], member, p)
                    msg = await post_thread_message(org, member, thread, a["text"], spot=False)
                    cards.append({"card_id": new_id("crd"), "type": "message", "status": "sent", "data": {"to_member_id": p["member_id"], "to_name": p["name"],
                                  "text": a["text"], "thread_id": thread["thread_id"], "deliveries": msg["deliveries"]}})
                    summaries.append(f"Sent the message to {p['name']}")
                else:
                    summaries.append(f"Could not find '{a['person']}' in the business, so nothing was sent")
            elif t == "add_rule" and a.get("text"):
                if has_scope(member, "manage_team"):
                    r = await add_rule(org, member, a["text"], trigger=a.get("trigger") or "any", keyword=a.get("keyword"), notify_target=a.get("notify"))
                    cards.append({"card_id": new_id("crd"), "type": "rule", "status": "saved", "data": {"rule_id": r["rule_id"], "text": r["text"]}})
                    summaries.append(f"Saved a business rule: {r['text']}")
                else:
                    summaries.append("Only the owner can set business rules")
            elif t == "request_approval":
                if has_scope(member, "approve"):
                    continue
                ap = await create_approval(org, member, kind=a.get("approval_kind") or "other", title=a.get("title") or a.get("text") or "Request",
                                           details=a.get("text") or "", amount=a.get("amount"), currency=a.get("currency"), source=source)
                cards.append({"card_id": new_id("crd"), "type": "approval", "status": ap["status"], "data": {"approval_id": ap["approval_id"], "title": ap["title"],
                              "amount": ap.get("amount"), "currency": ap.get("currency"), "rule_text": ap.get("decision_text")}})
                summaries.append("Allowed automatically by an existing rule: " + ap["decision_text"] if ap["status"] == "allowed_by_rule" else "Sent to the owner for approval")
            elif t == "decide_approval" and a.get("approval_id") and a.get("decision"):
                ap = await db.approvals.find_one({"org_id": org["org_id"], "approval_id": a["approval_id"]}, {"_id": 0})
                if ap and has_scope(member, "approve") and ap["status"] == "pending":
                    res = await decide_approval(org, member, ap, a["decision"], a.get("max_amount"), note=None)
                    cards.append({"card_id": new_id("crd"), "type": "decision", "status": "applied", "data": {"approval_id": ap["approval_id"], "summary": res["summary"], "decision": a["decision"]}})
                    summaries.append(f"Applied the decision. Repeat it back exactly: {res['summary']}")
            elif t == "update_item" and a.get("item_id") and a.get("status"):
                it = await get_item_for(member, a["item_id"])
                if it and can_edit_item(member, it):
                    res = await set_item_status(org, member, it, a["status"], a.get("reason"), local_to_utc_iso(a.get("new_due_at"), org, 18), via=source.get("type", "chat"))
                    cards.append({"card_id": new_id("crd"), "type": "update", "status": "applied", "data": {"item_id": it["item_id"], "title": it["title"], "new_status": a["status"],
                                  "reason": a.get("reason"), "prev": res["prev"]}})
                    summaries.append(f"Updated '{it['title']}' to {a['status']}")
            elif t == "update_business" and is_owner(member):
                upd = {k: v for k, v in {"name": a.get("business_name"), "industry": a.get("industry"), "description": a.get("description"), "country": a.get("country")}.items() if v}
                if upd:
                    await db.orgs.update_one({"org_id": org["org_id"]}, {"$set": {**upd, "profile_learned": True}})
                    org.update(upd)
                    cards.append({"card_id": new_id("crd"), "type": "business", "status": "saved", "data": upd})
                    summaries.append("Updated the business profile: " + ", ".join(f"{k}={v}" for k, v in upd.items()))
            elif t == "remember_fact" and a.get("text"):
                fid = new_id("fct")
                await db.knowledge.insert_one({"fact_id": fid, "org_id": org["org_id"], "text": a["text"][:400], "source": source.get("type", "chat"),
                                               "created_by": member["member_id"], "created_by_name": member["name"], "created_at": iso()})
                cards.append({"card_id": new_id("crd"), "type": "fact", "status": "saved", "data": {"fact_id": fid, "text": a["text"][:400]}})
                summaries.append(f"Remembered: {a['text'][:120]}")
            elif t == "need_access" and not is_owner(member) and a.get("scope") in SCOPES and not has_scope(member, a.get("scope")):
                existing = await db.approvals.find_one({"org_id": org["org_id"], "kind": "access", "requested_by": member["member_id"], "scope": a["scope"], "status": "pending"})
                if not existing:
                    ap = await create_approval(org, member, kind="access", title=f"See {SCOPES[a['scope']].lower()}", scope=a["scope"],
                                               question=a.get("text") or "", source=source)
                    cards.append({"card_id": new_id("crd"), "type": "access_request", "status": "pending", "data": {"approval_id": ap["approval_id"], "scope": a["scope"], "label": SCOPES[a["scope"]]}})
                summaries.append(f"The person lacks access to {SCOPES[a['scope']].lower()}. Do NOT answer that part. Say you've asked the owner.")
        except Exception as e:
            logger.exception("action %s failed: %s", t, e)
    return cards, summaries


def _citations(text: str, sources: list) -> list:
    used = sorted({int(n) for n in re.findall(r"\[(\d{1,2})\]", text or "")})
    by_n = {s["n"]: s for s in sources}
    return [{k: by_n[n][k] for k in ("n", "type", "id", "title", "link")} for n in used if n in by_n]


async def run_brain(org: dict, member: dict, text: str, *, channel: str = "app", attachments: Optional[list] = None,
                    extra_context: str = "") -> AsyncGenerator:
    """Yields events: user, cards, delta, done."""
    attachments = attachments or []
    user_msg = {"msg_id": new_id("bm"), "org_id": org["org_id"], "member_id": member["member_id"], "role": "user", "kind": "message",
                "text": text, "channel": channel, "attachments": attachments, "created_at": iso()}
    await db.brain_messages.insert_one(dict(user_msg))
    user_msg.pop("_id", None)
    yield {"type": "user", "message": user_msg}

    if await ai_limit_reached(org):
        msg = {"msg_id": new_id("bm"), "org_id": org["org_id"], "member_id": member["member_id"], "role": "assistant", "kind": "message",
               "text": "This business has reached its KONNTO usage limit for this month. Your message is saved; the KONNTO team will raise the limit soon.",
               "cards": [], "citations": [], "channel": channel, "created_at": iso()}
        await db.brain_messages.insert_one(dict(msg))
        msg.pop("_id", None)
        yield {"type": "delta", "text": msg["text"]}
        yield {"type": "done", "message": msg}
        return

    cfg = await brain.get_brain_config()
    people = await org_people(org["org_id"])
    open_items = await visible_open_items(member, 40)
    approvals = await pending_approvals_for(member)
    rules = await active_rules(org["org_id"])
    full_text = text + (f"\n\n{extra_context}" if extra_context else "")
    analysis = await brain.analyze(org, member, full_text, people, open_items, approvals, rules, cfg)
    source = {"type": channel, "msg_id": user_msg["msg_id"]}
    cards, summaries = await execute_actions(org, member, analysis, people, source)
    for a in attachments:
        if a.get("type") == "document" and a.get("doc_id"):
            cards.append({"card_id": new_id("crd"), "type": "doc", "status": "saved", "data": {"doc_id": a["doc_id"], "filename": a.get("filename"), "summary": a.get("summary", "")[:400]}})
    yield {"type": "cards", "cards": cards}

    sources = await retrieve(org, member, analysis.get("search_query") or "", text)
    history = await _history(member)
    rules_txt = "\n".join(f"- {r['text']}" for r in rules[:20])
    extra = (f"\nBusiness rules to follow:\n{rules_txt}\n" if rules_txt else "") + (f"\nAttached content:\n{extra_context[:3000]}\n" if extra_context else "")
    if analysis.get("failed"):
        extra += "\n(Understanding step failed; just answer helpfully and say nothing was saved.)"
    out = []
    async for d in brain.stream_reply(org, member, text, cfg, sources, summaries, history, extra):
        out.append(d)
        yield {"type": "delta", "text": d}
    reply = "".join(out).strip()
    msg = {"msg_id": new_id("bm"), "org_id": org["org_id"], "member_id": member["member_id"], "role": "assistant", "kind": "message",
           "text": reply, "cards": cards, "citations": _citations(reply, sources), "language": analysis.get("language"),
           "channel": channel, "reply_to": user_msg["msg_id"], "created_at": iso()}
    await db.brain_messages.insert_one(dict(msg))
    msg.pop("_id", None)
    yield {"type": "done", "message": msg}


async def run_brain_collect(org: dict, member: dict, text: str, **kw) -> dict:
    final = None
    async for ev in run_brain(org, member, text, **kw):
        if ev["type"] == "done":
            final = ev["message"]
    return final


# ================================================================ cards (save / skip / undo)

async def save_proposal(org: dict, member: dict, data: dict, source: dict) -> dict:
    payload = dict(data)
    payload["due_at_utc"] = data.get("due_at")
    payload["remind_at_utc"] = data.get("remind_at")
    payload.pop("due_at", None)
    payload.pop("remind_at", None)
    return await create_item(org, member, payload, source=source)


async def card_action(org: dict, member: dict, card_id: str, op: str, edits: Optional[dict] = None) -> dict:
    msg = await db.brain_messages.find_one({"member_id": member["member_id"], "cards.card_id": card_id}, {"_id": 0})
    if not msg:
        return {"error": "not_found"}
    card = next(c for c in msg["cards"] if c["card_id"] == card_id)
    result = {}
    if card["type"] == "proposal":
        if op == "save" and card["status"] == "pending":
            data = {**card["data"], **{k: v for k, v in (edits or {}).items() if k in ("title", "details", "assignee_id", "due_at", "remind_at", "kind", "amount", "counterparty", "private")}}
            if edits and edits.get("assignee_id"):
                p = await db.members.find_one({"member_id": edits["assignee_id"], "org_id": org["org_id"]}, {"_id": 0})
                data["assignee_name"] = p["name"] if p else None
            item = await save_proposal(org, member, data, {"type": "chat", "msg_id": msg["msg_id"]})
            card["data"] = data
            card["status"], card["item_id"] = "saved", item["item_id"]
            result = {"item": item}
        elif op == "skip" and card["status"] == "pending":
            card["status"] = "skipped"
        elif op == "undo" and card["status"] == "saved" and card.get("item_id"):
            await db.items.update_one({"item_id": card["item_id"], "org_id": org["org_id"]}, {"$set": {"deleted": True, "updated_at": iso()}})
            card["status"] = "pending"
            card.pop("item_id", None)
    elif op == "undo":
        if card["type"] == "invite" and card["status"] == "created":
            await db.members.update_one({"member_id": card["data"]["member_id"], "status": "invited"}, {"$set": {"status": "removed"}})
            card["status"] = "undone"
        elif card["type"] == "rule" and card["status"] == "saved":
            await db.rules.update_one({"rule_id": card["data"]["rule_id"], "org_id": org["org_id"]}, {"$set": {"active": False, "removed_at": iso()}})
            card["status"] = "undone"
        elif card["type"] == "decision" and card["status"] == "applied":
            ap = await db.approvals.find_one({"approval_id": card["data"]["approval_id"], "org_id": org["org_id"]}, {"_id": 0})
            if ap:
                await undo_decision(org, member, ap)
            card["status"] = "undone"
        elif card["type"] == "fact" and card["status"] == "saved":
            await db.knowledge.update_one({"fact_id": card["data"]["fact_id"], "org_id": org["org_id"]}, {"$set": {"deleted": True, "deleted_at": iso()}})
            card["status"] = "undone"
        elif card["type"] == "update" and card["status"] == "applied":
            prev = card["data"].get("prev") or {}
            await db.items.update_one({"item_id": card["data"]["item_id"], "org_id": org["org_id"]}, {"$set": {**prev, "updated_at": iso()},
                                       "$push": {"history": _hist(member["name"], "Undid last change")}})
            card["status"] = "undone"
    await db.brain_messages.update_one({"msg_id": msg["msg_id"]}, {"$set": {"cards": msg["cards"]}})
    return {"card": card, **result}


# ================================================================ button actions (WhatsApp + in-app notices)

async def set_pending_state(member: dict, kind: str, ref: str, extra: Optional[dict] = None):
    await db.pending_states.update_one({"member_id": member["member_id"]}, {"$set": {"member_id": member["member_id"], "org_id": member["org_id"], "kind": kind, "ref": ref,
                                        "extra": extra or {}, "expires_at": iso(now() + timedelta(hours=6))}}, upsert=True)


async def pop_pending_state(member: dict) -> Optional[dict]:
    st = await db.pending_states.find_one({"member_id": member["member_id"]}, {"_id": 0})
    if not st:
        return None
    await db.pending_states.delete_one({"member_id": member["member_id"]})
    if parse_iso(st["expires_at"]) < now():
        return None
    return st


async def handle_button(org: dict, member: dict, action_id: str, via: str = "whatsapp") -> str:
    """Handles Done / Delayed / Need help / Save / Skip / Allow once / Always allow / Don't allow. Returns reply text."""
    op, _, ref = action_id.partition(":")
    if op in ("done", "delay", "help", "accept", "decline"):
        item = await get_item_for(member, ref)
        if not item:
            return "I couldn't find that item."
        if op == "done":
            await set_item_status(org, member, item, "done", via=via)
            return f"Great — marked done: {item['title']}."
        if op == "accept":
            await set_item_status(org, member, item, "in_progress", via=via)
            return f"Thanks. I'll remind you before it's due: {item['title']}."
        if op == "decline":
            await set_pending_state(member, "reason", ref, {"status": "stuck"})
            return "Okay. Please reply with a short reason, so I can tell them."
        await set_pending_state(member, "reason", ref, {"status": "delayed" if op == "delay" else "stuck"})
        return "What's the reason? Reply in a few words (and a new date if you know it)." if op == "delay" else "What do you need? Reply in a few words and I'll tell the right person."
    if op in ("ap_once", "ap_always", "ap_deny"):
        ap = await db.approvals.find_one({"approval_id": ref, "org_id": org["org_id"]}, {"_id": 0})
        if not ap or not has_scope(member, "approve"):
            return "I couldn't find that approval."
        if ap["status"] != "pending":
            return "This was already decided."
        if op == "ap_always" and ap.get("amount") is not None:
            await set_pending_state(member, "always_amount", ref)
            return f"Always allow {KIND_LABEL[ap['kind']]}s from {ap['requested_by_name']} under what amount? Reply with a number, e.g. {int(nice_ceiling(float(ap['amount'])))}."
        res = await decide_approval(org, member, ap, {"ap_once": "once", "ap_always": "always", "ap_deny": "deny"}[op])
        return res["summary"] + " Reply UNDO to change it."
    if op in ("save", "skip"):
        msg = await db.brain_messages.find_one({"msg_id": ref, "member_id": member["member_id"]}, {"_id": 0})
        if not msg:
            return "I couldn't find that."
        saved = []
        for c in msg.get("cards", []):
            if c["type"] == "proposal" and c["status"] == "pending":
                r = await card_action(org, member, c["card_id"], op)
                if op == "save" and r.get("item"):
                    saved.append(r["item"]["title"])
        return ("Saved: " + "; ".join(saved) + ".") if saved else "Okay, not saved."
    return "Okay."


async def handle_pending_reply(org: dict, member: dict, state: dict, text: str) -> str:
    if state["kind"] == "reason":
        item = await get_item_for(member, state["ref"])
        if not item:
            return "I couldn't find that item."
        status = state["extra"].get("status", "delayed")
        # look for a date in the reason via the brain (best-effort)
        await set_item_status(org, member, item, status, reason=text[:300], via="whatsapp")
        return f"Thanks. I've told {item.get('created_by_name') or 'them'}: {text[:120]}"
    if state["kind"] == "always_amount":
        ap = await db.approvals.find_one({"approval_id": state["ref"], "org_id": org["org_id"]}, {"_id": 0})
        nums = re.findall(r"\d[\d,]*\.?\d*", text)
        if not ap or not nums:
            return "I didn't get an amount, so nothing changed. Reply 'always under 15000' to try again."
        amount = float(nums[0].replace(",", ""))
        res = await decide_approval(org, member, ap, "always", amount)
        return res["summary"] + " Reply UNDO to change it."
    return "Okay."


async def last_undoable_decision(member: dict) -> Optional[dict]:
    return await db.approvals.find_one({"org_id": member["org_id"], "decided_by": member["member_id"], "status": {"$in": ["allowed_once", "allowed_always", "denied"]}},
                                       {"_id": 0}, sort=[("decided_at", -1)])
