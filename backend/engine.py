"""KONNTO engine: the talk -> think -> act pipeline, work items, invites, approvals, rules, actions."""
import re
import math
import logging
from datetime import timedelta
from typing import Optional, AsyncGenerator

from core import (db, now, iso, parse_iso, new_id, short_code, local_to_utc_iso, fmt_local, app_link,
                  has_scope, is_owner, item_scope_query, doc_scope_query, redact_item, item_state, SCOPES,
                  SENSITIVE_SCOPES, ai_limit_reached, audit, norm_phone, digits, org_tz, fact_scope_query, fact_category, can_read_rules)
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
        if (currency or "").upper() == "INR":
            txt = _indian_group(val)
    except Exception:
        txt = str(amount)
    return f"{sym}{txt}"


def _indian_group(val: float) -> str:
    neg = val < 0
    val = abs(val)
    whole = int(val)
    frac = val - whole
    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        digits = ",".join(parts + [tail])
    out = digits + (f"{frac:.2f}"[1:] if frac >= 0.005 else "")
    return ("-" if neg else "") + out


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


def _not_expired() -> dict:
    return {"$or": [{"expires_at": None}, {"expires_at": {"$exists": False}}, {"expires_at": {"$gt": iso()}}]}


async def active_rules(org_id: str) -> list:
    return await db.rules.find({"org_id": org_id, "active": True, **_not_expired()}, {"_id": 0}).sort("created_at", -1).to_list(200)


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
                   notify_target: Optional[str] = None, condition: Optional[dict] = None, source: str = "chat", expires_at: Optional[str] = None) -> dict:
    rule = {"rule_id": new_id("rul"), "org_id": org["org_id"], "text": text.strip()[:600], "kind": kind, "trigger": trigger or "any",
            "keyword": (keyword or "").strip().lower() or None, "notify_target": (notify_target or "").strip() or None,
            "condition": condition or {}, "created_by": actor["member_id"], "created_by_name": actor["name"], "source": source,
            "active": True, "expires_at": expires_at, "created_at": iso()}
    await db.rules.insert_one(dict(rule))
    rule.pop("_id", None)
    await audit(org["org_id"], actor["member_id"], "rule_added", {"rule_id": rule["rule_id"], "text": rule["text"]})
    return rule


async def apply_behaviour_rules(org: dict, trigger: str, item: dict, actor: Optional[dict] = None):
    rules = await db.rules.find({"org_id": org["org_id"], "active": True, "kind": "behaviour", "trigger": {"$in": [trigger, "any"]},
                                 "notify_target": {"$ne": None}, **_not_expired()}, {"_id": 0}).to_list(50)
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
    live = await live_state(org, temp)
    async for d in brain.stream_reply(org, temp, question, cfg, sources, ["The owner allowed this answer once (temporary access)."], [], "", live,
                                      trusted_context(org, temp, role_label(temp))):
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
        fq = fact_scope_query(member)
        fq["$and"] = [{"text": rx}] + ([{"text": fq.pop("text")}] if "text" in fq else [])
        for f in await db.knowledge.find(fq, {"_id": 0}).to_list(6):
            add("fact", f["fact_id"], f["text"][:80], f"{f['text']} (source: {f.get('source') or 'chat'}, added by {f.get('created_by_name') or '-'} on {fmt_local(f.get('created_at'), org)})", "/app/knowledge")
        for pj in await db.projects.find({"org_id": org["org_id"], "name": rx}, {"_id": 0}).to_list(3):
            its = await db.items.find({**item_scope_query(member), "project_id": pj["project_id"]}, {"_id": 0, "history": 0}).to_list(30)
            if its or has_scope(member, "team_work"):
                open_n = sum(1 for i in its if i.get("status") not in ("done", "cancelled"))
                late = sum(1 for i in its if item_state(i) == "overdue")
                add("project", pj["project_id"], f"Project: {pj['name']}", f"{open_n} open, {late} overdue, {len(its) - open_n} done/cancelled you can see", "/app/work")
        if has_scope(member, "approve"):
            for a in await db.approvals.find({"org_id": org["org_id"], "status": {"$ne": "pending"}, "$or": [{"title": rx}, {"details": rx}]}, {"_id": 0}).sort("created_at", -1).to_list(4):
                add("approval", a["approval_id"], f"Past approval: {a['title']}", f"{a.get('status')} — {a.get('decision_text') or ''} asked by {a.get('requested_by_name')}" + (f", {money(a.get('amount'), a.get('currency'))}" if a.get('amount') is not None else ""), "/app/approvals")
        threads = await db.threads.find({"org_id": org["org_id"], "member_ids": member["member_id"]}, {"thread_id": 1, "_id": 0}).to_list(200)
        if threads:
            for tm in await db.thread_messages.find({"thread_id": {"$in": [t["thread_id"] for t in threads]}, "text": rx}, {"_id": 0}).sort("created_at", -1).to_list(4):
                add("chat", tm["msg_id"], f"{tm['sender_name']} in team chat", f"{fmt_local(tm['created_at'], org)}: {tm['text'][:220]}", f"/app/team/thread/{tm['thread_id']}")
    if include_open:
        for i in await visible_open_items(member, 15):
            add("work", i["item_id"], i["title"], item_snip(i), f"/app/work?item={i['item_id']}")
    if include_open and has_scope(member, "approve"):
        for a in await db.approvals.find({"org_id": org["org_id"], "status": "pending"}, {"_id": 0}).to_list(5):
            add("approval", a["approval_id"], f"Approval: {a['title']}", f"asked by {a['requested_by_name']}, {a['kind']}" + (f", {money(a.get('amount'), a.get('currency'))}" if a.get('amount') is not None else ""), "/app/approvals")
    return sources


# ================================================================ live state (what K-BRAIN knows right now)

def _ago(ts: Optional[str]) -> str:
    d = parse_iso(ts)
    if not d:
        return ""
    secs = (now() - d).total_seconds()
    if secs < 3600:
        return f"{max(1, int(secs // 60))} min"
    if secs < 86400:
        return f"{int(secs // 3600)} h"
    return f"{int(secs // 86400)} day{'s' if secs >= 172800 else ''}"


def _short_money(total: float, currency: Optional[str]) -> str:
    if (currency or "").upper() == "INR" and total >= 100000:
        return f"{CURRENCY_SYMBOLS.get('INR', 'Rs ')}{total / 100000:.2f}L"
    return money(total, currency)


def visible_people(member: dict, people: list) -> list:
    """External users only see the owner(s) and whoever brought them in."""
    if member.get("member_type") != "partner":
        return people
    keep = {member.get("invited_by"), member.get("manager_id"), member["member_id"]}
    return [p for p in people if p.get("member_type") == "owner" or p["member_id"] in keep]


_ROLE_RULES = [
    (("director", "ceo", "coo", "vice president", "vp ", "general manager"), "DIRECTOR / SENIOR MANAGEMENT"),
    (("account", "finance", "cfo", "bookkeep"), "ACCOUNTANT / FINANCE"),
    (("project manager", "project lead", "project coordinator"), "PROJECT MANAGER"),
    (("sales", "business development", "bde"), "SALES"),
    (("purchase", "procure", "buyer", "sourcing"), "PURCHASE"),
    (("manager", "lead", "supervisor", "head"), "MANAGER"),
]


def role_label(member: dict) -> str:
    if is_owner(member):
        return "OWNER / FOUNDER"
    if member.get("member_type") == "partner":
        return "VENDOR / EXTERNAL USER"
    job = f" {(member.get('job') or '').lower()} "
    for keys, label in _ROLE_RULES:
        if any(k in job for k in keys):
            return label
    if has_scope(member, "manage_team") or has_scope(member, "team_work"):
        return "MANAGER"
    return "TEAM MEMBER"


def trusted_context(org: dict, member: dict, role: str) -> str:
    tz = org_tz(org)
    perms = "everything in this workspace (owner)" if is_owner(member) else ", ".join(
        f"{k} ({SCOPES[k]})" for k in sorted(set((member.get("access") or []) + ["own_work"])) if k in SCOPES)
    denied = [] if is_owner(member) else [SCOPES[k] for k in SCOPES if not has_scope(member, k)]
    first = (member.get("name") or "").split(" ")[0] or "there"
    wa = "connected" if wa_configured() else "NOT connected (messages go in-app, with email fallback where an address exists)"
    return f"""Workspace: {org.get('name')} (id {org['org_id']}) — industry: {org.get('industry') or 'not set'}; about: {org.get('description') or 'not set'}; country: {org.get('country') or '-'}; currency: {org.get('currency') or 'USD'}; timezone: {tz.key}.
Local time: {now().astimezone(tz).strftime('%A %d %b %Y %H:%M')}.
Current user: {member['name']} (call them {first}); member type: {member.get('member_type')}; job: {member.get('job') or '-'}; K-BRAIN role: {role}.
Permissions granted by the server: {perms}.
Not permitted (data for these was withheld before reaching you): {', '.join(denied) or 'none'}.
Platform administration: not available in this chat.
Capabilities available right now:
- Work items (tasks, promises, reminders, decisions, notes) with owners, due dates and status: yes (new items are drafts until the user taps Save).
- Projects (grouping of work): yes. Approvals with once/always/deny and amount limits: yes. Business rules and temporary instructions: yes.
- K-MEMORY: confirmed business facts, uploaded documents (searchable), team chats, decisions and an activity log: yes.
- Team messaging inside KONNTO: yes. WhatsApp: {wa}. Email: only for invites and notification fallback, not free-form email.
- Scheduled jobs (every 15 minutes): due reminders, chasing late work up the line, morning briefs and evening check-ins. No other continuous monitoring.
- NOT available: accounting/Tally or bank integration, CRM/sales pipeline or lead records, inventory, attendance, payroll, payments. Financial figures exist only where people entered them (approval amounts, work amounts, facts)."""


async def live_state(org: dict, member: dict) -> str:
    ccy = org.get("currency")
    out = []
    ref = now()
    people = visible_people(member, await org_people(org["org_id"]))
    roster = [f"{p['name']} ({p.get('job') or p.get('member_type')}{', invited' if p.get('status') == 'invited' else ''})" for p in people if p["member_id"] != member["member_id"]]
    if roster:
        out.append("People: " + "; ".join(roster[:25]))
    # approvals
    if has_scope(member, "approve"):
        aps = await db.approvals.find({"org_id": org["org_id"], "status": "pending"}, {"_id": 0}).sort("created_at", 1).to_list(30)
        total = sum(float(a.get("amount") or 0) for a in aps)
        if aps:
            out.append(f"Approvals waiting for {member['name'].split(' ')[0]} ({len(aps)}, {_short_money(total, ccy)} in money requests):")
            for a in aps:
                amt = money(a.get("amount"), a.get("currency") or ccy) if a.get("amount") is not None else "no cash amount"
                det = f" — {a['details'][:160]}" if a.get("details") else ""
                out.append(f"- {a['title']} | {amt} | raised by {a.get('requested_by_name')} | {a.get('kind')} | waiting {_ago(a.get('created_at'))}{det}")
        else:
            out.append("Approvals waiting: none.")
    else:
        mine = await db.approvals.find({"org_id": org["org_id"], "requested_by": member["member_id"], "status": "pending"}, {"_id": 0}).to_list(10)
        if mine:
            out.append("Your requests still waiting for the owner:")
            out += [f"- {a['title']} (waiting {_ago(a.get('created_at'))})" for a in mine]
    # work
    items = await visible_open_items(member, 80)
    buckets = {"overdue": [], "due": [], "stuck": [], "delayed": [], "in_progress": [], "open": []}
    for i in items:
        st = item_state(i, ref)
        if i.get("status") == "delayed" and st != "overdue":
            st = "delayed"
        elif i.get("status") == "in_progress" and st == "open":
            st = "in_progress"
        buckets.setdefault(st, []).append(i)

    def line(i):
        bits = [i["title"], f"{i.get('kind')}", f"for {i.get('assignee_name') or '-'}"]
        if i.get("due_at"):
            bits.append(f"due {fmt_local(i['due_at'], org)}")
        if i.get("counterparty"):
            bits.append(f"with {i['counterparty']}")
        if i.get("amount") is not None:
            bits.append(money(i["amount"], i.get("currency") or ccy))
        if i.get("delay_reason") or i.get("stuck_reason"):
            bits.append(f"reason: {i.get('delay_reason') or i.get('stuck_reason')}")
        if i.get("details"):
            bits.append(i["details"][:120])
        return "- " + " | ".join(bits)
    labels = [("overdue", "Overdue"), ("due", "Due in the next 24 hours"), ("stuck", "Stuck"), ("delayed", "Delayed"), ("in_progress", "In progress"), ("open", "Other open work")]
    for key, label in labels:
        b = buckets.get(key) or []
        if b:
            out.append(f"{label} ({len(b)}):")
            out += [line(i) for i in b[:10 if key != 'open' else 8]]
    if not items:
        out.append("Open work: none.")
    # PCM instruction register — scoped to the current member's authorised responsibilities.
    pcm_query = {"org_id": org["org_id"], "deleted": {"$ne": True}}
    if not is_owner(member) and not has_scope(member, "team_work"):
        pcm_query["$or"] = [{"assignee_id": member["member_id"]}, {"issued_by": member["member_id"]}]
    pcm_rows = await db.pcm_instructions.find(pcm_query, {"_id": 0}).sort("updated_at", -1).to_list(20)
    if pcm_rows:
        out.append("KONNTO PCM instruction register (live status; not proof of completed work):")
        for row in pcm_rows[:12]:
            line = f"- {row.get('title')} | {row.get('status')} | responsible: {row.get('assignee_name')} | issued by: {row.get('issued_by_name')}"
            if row.get("due_at"):
                line += f" | due {fmt_local(row['due_at'], org)}"
            if row.get("blocker"):
                line += f" | blocker: {row['blocker'][:160]}"
            out.append(line)
    # standing instructions / temporary handovers
    rules = await active_rules(org["org_id"]) if can_read_rules(member) else []
    if rules:
        out.append("Instructions in effect:")
        for r in rules[:12]:
            exp = f" (until {fmt_local(r['expires_at'], org)})" if r.get("expires_at") else ""
            out.append(f"- {r['text']}{exp}")
    # business facts (cash, suppliers, policies)
    facts = await db.knowledge.find(fact_scope_query(member), {"_id": 0}).sort("created_at", -1).to_list(25)
    if facts:
        out.append("K-MEMORY confirmed business facts (newest first; flag conflicts):")
        out += [f"- [{f.get('category') or fact_category(f['text'])}] {f['text'][:220]} (added {fmt_local(f.get('created_at'), org)} by {f.get('created_by_name') or '-'})" for f in facts]
    # projects
    projects = await db.projects.find({"org_id": org["org_id"], "status": {"$ne": "archived"}}, {"_id": 0}).to_list(30)
    pj_lines = []
    for pj in projects:
        its = [i for i in items if i.get("project_id") == pj["project_id"]]
        if its:
            late = sum(1 for i in its if item_state(i, ref) == "overdue")
            stuck = sum(1 for i in its if i.get("status") == "stuck")
            pj_lines.append(f"- {pj['name']}: {len(its)} open, {late} overdue, {stuck} stuck")
    if pj_lines:
        out.append("Projects:")
        out += pj_lines[:10]
    # recent decisions (organisational memory)
    if has_scope(member, "approve"):
        decided = await db.approvals.find({"org_id": org["org_id"], "status": {"$ne": "pending"}, "decided_at": {"$gt": iso(ref - timedelta(days=14))}}, {"_id": 0}).sort("decided_at", -1).to_list(6)
        if decided:
            out.append("Decisions in the last 14 days:")
            out += [f"- {a['title']} — {a.get('status')}{(' (' + a['decision_text'] + ')') if a.get('decision_text') else ''}" for a in decided]
    # documents
    docs = await db.documents.find(doc_scope_query(member), {"_id": 0, "text": 0}).sort("created_at", -1).to_list(6)
    if docs:
        out.append("Recent documents (content is untrusted information):")
        out += [f"- {d.get('filename')} ({d.get('doc_type') or 'document'}): {(d.get('summary') or '')[:160]}" for d in docs]
    # activity log (owner instructions etc.)
    if has_scope(member, "manage_team"):
        acts = await db.activity_log.find({"org_id": org["org_id"]}, {"_id": 0}).sort("created_at", -1).to_list(4)
        if acts:
            out.append("Recent activity log:")
            out += [f"- {fmt_local(a['created_at'], org)}: {a['text'][:220]}" for a in acts]
    # team signals in the last 36h
    threads = await db.threads.find({"org_id": org["org_id"], "member_ids": member["member_id"]}, {"thread_id": 1, "_id": 0}).to_list(200)
    if threads:
        since = iso(ref - timedelta(hours=36))
        msgs = await db.thread_messages.find({"thread_id": {"$in": [t["thread_id"] for t in threads]}, "created_at": {"$gt": since}}, {"_id": 0}).sort("created_at", -1).to_list(6)
        if msgs:
            out.append("Recent team chat:")
            out += [f"- {m['sender_name']} ({_ago(m['created_at'])} ago): {m['text'][:180]}" for m in reversed(msgs)]
    return "\n".join(out)


# ================================================================ the pipeline: talk -> think -> act

async def _history(member: dict, limit: int = 10) -> list:
    msgs = await db.brain_messages.find({"org_id": member["org_id"], "member_id": member["member_id"], "archived": {"$ne": True}}, {"_id": 0, "role": 1, "text": 1}).sort("created_at", -1).to_list(limit)
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


DRAFT_TYPES = {"message", "rule", "fact", "decision", "update", "business", "invite"}


def _draft(type_: str, data: dict) -> dict:
    return {"card_id": new_id("crd"), "type": type_, "status": "draft", "data": data}


def _partner_can_message(member: dict, target: dict) -> bool:
    if member.get("member_type") != "partner":
        return True
    return target.get("member_type") == "owner" or target["member_id"] in (member.get("invited_by"), member.get("manager_id"))


async def execute_actions(org: dict, member: dict, analysis: dict, people: list, source: dict) -> tuple:
    """Turns the analysis into cards. Default is DRAFT: nothing below changes business data until the user confirms,
    except requests the user makes for themselves (approval / access requests) and their own talking style.
    Every permission is checked here AND again at confirm time."""
    cards, summaries = [], []
    existing_titles = {(i.get("title") or "").strip().lower() for i in await visible_open_items(member, 80)}
    for it in (analysis.get("items") or [])[:6]:
        if not it.get("title"):
            continue
        data = _proposal_data(org, it, people, member)
        if data["title"].strip().lower() in existing_titles:
            summaries.append(f"Did not draft '{data['title']}' again — an open item with this title already exists")
            continue
        cards.append({"card_id": new_id("crd"), "type": "proposal", "status": "pending", "data": data})
        summaries.append(f"DRAFTED (not saved — waits for the user to tap Save) a {data['kind']}: {data['title']}" + (f" for {data['assignee_name']}" if data.get('assignee_name') else ""))

    for a in (analysis.get("actions") or [])[:6]:
        t = a.get("type")
        try:
            if t == "invite_person" and a.get("name"):
                existing = find_person(people, a["name"])
                if existing and existing["name"].lower().split()[0] == a["name"].lower().split()[0]:
                    links = invite_links(org, existing) if existing.get("status") == "invited" and existing.get("invite_token") else None
                    cards.append({"card_id": new_id("crd"), "type": "invite", "status": "exists", "data": {"member_id": existing["member_id"], "name": existing["name"], "job": existing.get("job"),
                                  "member_type": existing.get("member_type"), "joined": existing.get("status") == "active", **(links or {})}})
                    summaries.append(f"{existing['name']} is already in the business ({existing.get('status')}); nothing new drafted")
                elif has_scope(member, "manage_team"):
                    cards.append(_draft("invite", {"name": a["name"].strip()[:80], "job": (a.get("job") or "").strip()[:80], "member_type": a.get("member_type") or "team", "phone": a.get("phone")}))
                    summaries.append(f"DRAFTED an invite for {a['name']} ({a.get('job') or 'role not given'}) — created only when the user taps Confirm")
                else:
                    ap = await create_approval(org, member, kind="other", title=f"Add {a['name']} ({a.get('job') or 'new person'}) to the team",
                                               payload={"action": "invite", "name": a["name"], "job": a.get("job"), "member_type": a.get("member_type") or "team"}, source=source)
                    cards.append({"card_id": new_id("crd"), "type": "approval", "status": ap["status"], "data": {"approval_id": ap["approval_id"], "title": ap["title"]}})
                    summaries.append("EXECUTED: the user cannot add people, so an approval request was created for the owner")
            elif t == "message_person" and a.get("person") and a.get("text"):
                p = find_person(people, a["person"], member)
                if p and p["member_id"] != member["member_id"] and _partner_can_message(member, p):
                    cards.append(_draft("message", {"to_member_id": p["member_id"], "to_name": p["name"], "text": a["text"][:1500]}))
                    summaries.append(f"DRAFTED a message to {p['name']} (not sent — waits for Confirm): \"{a['text'][:300]}\"")
                else:
                    summaries.append(f"Could not find '{a['person']}' among the people this user can message, so nothing was drafted")
            elif t == "add_rule" and a.get("text"):
                if has_scope(member, "manage_team"):
                    temporary = a.get("rule_duration") == "temporary" or bool(a.get("until"))
                    until = local_to_utc_iso(a.get("until"), org, default_hour=23) if a.get("until") else None
                    cards.append(_draft("rule", {"text": a["text"][:600], "trigger": a.get("trigger") or "any", "keyword": a.get("keyword"), "notify": a.get("notify"),
                                                "duration": "temporary" if temporary else "permanent", "until": until,
                                                "scope_level": a.get("rule_scope") or "company", "applies_to": a.get("applies_to")}))
                    summaries.append(f"DRAFTED a {'temporary' if temporary else 'permanent'} {a.get('rule_scope') or 'company'} rule (not saved — waits for Confirm): {a['text'][:200]}")
                else:
                    summaries.append("Only the owner or someone who manages the team can set business rules; nothing was drafted")
            elif t == "request_approval":
                if has_scope(member, "approve"):
                    continue
                ap = await create_approval(org, member, kind=a.get("approval_kind") or "other", title=a.get("title") or a.get("text") or "Request",
                                           details=a.get("text") or "", amount=a.get("amount"), currency=a.get("currency"), source=source)
                cards.append({"card_id": new_id("crd"), "type": "approval", "status": ap["status"], "data": {"approval_id": ap["approval_id"], "title": ap["title"],
                              "amount": ap.get("amount"), "currency": ap.get("currency"), "rule_text": ap.get("decision_text")}})
                summaries.append("EXECUTED: allowed automatically by an existing rule: " + ap["decision_text"] if ap["status"] == "allowed_by_rule" else "EXECUTED: approval request created and placed in the approvers' queue")
            elif t == "decide_approval" and a.get("approval_id") and a.get("decision"):
                ap = await db.approvals.find_one({"org_id": org["org_id"], "approval_id": a["approval_id"]}, {"_id": 0})
                if not has_scope(member, "approve"):
                    summaries.append("This user cannot decide approvals; nothing was drafted")
                elif ap and ap["status"] == "pending":
                    cards.append(_draft("decision", {"approval_id": ap["approval_id"], "title": ap["title"], "requested_by_name": ap.get("requested_by_name"),
                                                    "amount": ap.get("amount"), "currency": ap.get("currency"), "decision": a["decision"], "max_amount": a.get("max_amount"),
                                                    "summary": decision_summary(ap, a["decision"], a.get("max_amount"))}))
                    summaries.append(f"DRAFTED an approval decision (not applied — waits for Confirm): {decision_summary(ap, a['decision'], a.get('max_amount'))}")
                else:
                    summaries.append("That approval is not waiting any more; nothing was drafted")
            elif t == "update_item" and a.get("item_id") and a.get("status"):
                it = await get_item_for(member, a["item_id"])
                if it and can_edit_item(member, it):
                    cards.append(_draft("update", {"item_id": it["item_id"], "title": it["title"], "new_status": a["status"], "reason": a.get("reason"),
                                                  "new_due_at": local_to_utc_iso(a.get("new_due_at"), org, 18)}))
                    summaries.append(f"DRAFTED a status change (not applied — waits for Confirm): '{it['title']}' → {a['status']}")
                else:
                    summaries.append("This user cannot change that item; nothing was drafted")
            elif t == "update_business":
                upd = {k: v for k, v in {"name": a.get("business_name"), "industry": a.get("industry"), "description": a.get("description"), "country": a.get("country")}.items() if v}
                if upd and is_owner(member):
                    cards.append(_draft("business", upd))
                    summaries.append("DRAFTED a business-profile update (not saved — waits for Confirm): " + ", ".join(f"{k}={v}" for k, v in upd.items()))
                elif upd:
                    summaries.append("Only the owner can change the business profile; nothing was drafted")
            elif t == "remember_fact" and a.get("text"):
                if member.get("member_type") == "partner":
                    summaries.append("External users cannot add to company memory; nothing was drafted")
                else:
                    cat = fact_category(a["text"], a.get("category"))
                    cards.append(_draft("fact", {"text": a["text"][:400], "category": cat}))
                    summaries.append(f"DRAFTED a K-MEMORY fact (not saved — waits for Confirm): {a['text'][:160]}")
            elif t == "handover" and (a.get("person") or a.get("name")):
                a["person"] = a.get("person") or a.get("name")
                p = find_person(people, a["person"], member)
                if not has_scope(member, "manage_team"):
                    summaries.append("Only the owner or a manager can hand over responsibilities; nothing was prepared")
                elif not p or p["member_id"] == member["member_id"]:
                    summaries.append(f"Could not find '{a['person']}' in the business, so no handover was prepared. Ask who should take over.")
                else:
                    until = local_to_utc_iso(a.get("until"), org, default_hour=23) if a.get("until") else None
                    if not until:
                        tz = org_tz(org)
                        end_local = now().astimezone(tz).replace(hour=23, minute=59, second=0, microsecond=0)
                        until = iso(end_local)
                    restrictions = [r.strip() for r in (a.get("restrictions") or []) if r and r.strip()][:6]
                    message = (a.get("message") or a.get("text") or "").strip()
                    if not message:
                        message = f"Hi {p['name'].split(' ')[0]}, {member['name'].split(' ')[0]} is unavailable today. Please manage operations."
                    log_text = (a.get("log_text") or "").strip() or (
                        f"OWNER INSTRUCTION — {member['name']} is unavailable. {p['name']} ({p.get('job') or 'team'}) to manage operations. "
                        + ("RESTRICTION: " + "; ".join(restrictions) + ". " if restrictions else "")
                        + (a.get("escalation") or ""))
                    cards.append({"card_id": new_id("crd"), "type": "handover", "status": "pending", "data": {
                        "to_member_id": p["member_id"], "to_name": p["name"], "to_job": p.get("job"), "message": message[:1500],
                        "restrictions": restrictions, "escalation": (a.get("escalation") or "")[:300], "until": until, "log_text": log_text[:1200]}})
                    summaries.append(f"Prepared a handover to {p['name']} ({p.get('job') or 'team'}) \u2014 this is the person they meant by '{a['person']}' (NOT sent yet — waits for the person to tap Confirm). Drafted message: \"{message[:600]}\". "
                                     f"Restrictions: {'; '.join(restrictions) or 'none'}. Ends {fmt_local(until, org)}.")
            elif t == "set_persona" and a.get("persona") in brain.PERSONAS:
                await db.members.update_one({"member_id": member["member_id"]}, {"$set": {"brain_persona": a["persona"]}})
                member["brain_persona"] = a["persona"]
                label = brain.PERSONAS[a["persona"]]["label"]
                cards.append({"card_id": new_id("crd"), "type": "persona", "status": "saved", "data": {"persona": a["persona"], "label": label}})
                summaries.append(f"Switched your conversation style to {label}. Speak in that style from this reply on.")
            elif t == "need_access" and not is_owner(member) and a.get("scope") in SCOPES and not has_scope(member, a.get("scope")):
                existing = await db.approvals.find_one({"org_id": org["org_id"], "kind": "access", "requested_by": member["member_id"], "scope": a["scope"], "status": "pending"})
                if not existing:
                    ap = await create_approval(org, member, kind="access", title=f"See {SCOPES[a['scope']].lower()}", scope=a["scope"],
                                               question=a.get("text") or "", source=source)
                    cards.append({"card_id": new_id("crd"), "type": "access_request", "status": "pending", "data": {"approval_id": ap["approval_id"], "scope": a["scope"], "label": SCOPES[a["scope"]]}})
                summaries.append(f"The user lacks access to {SCOPES[a['scope']].lower()}. Do NOT answer that part. EXECUTED: an access request is in the owner's queue.")
        except Exception as e:
            logger.exception("action %s failed: %s", t, e)
    return cards, summaries


def draft_line(c: dict) -> str:
    d = c.get("data") or {}
    return {"message": f"Message to {d.get('to_name')}", "rule": f"Rule: {(d.get('text') or '')[:80]}", "fact": f"Remember: {(d.get('text') or '')[:80]}",
            "decision": d.get("summary") or "Approval decision", "update": f"{d.get('title')} \u2192 {d.get('new_status')}",
            "business": "Update business profile", "invite": f"Invite {d.get('name')}", "handover": f"Handover to {d.get('to_name')}"}.get(c["type"], c["type"])


async def apply_draft(org: dict, member: dict, card: dict) -> Optional[str]:
    """Executes a confirmed draft card. Re-checks permissions. Returns an error message or None."""
    t, d = card["type"], card["data"]
    if t == "message":
        p = await db.members.find_one({"member_id": d["to_member_id"], "org_id": org["org_id"], "status": {"$in": ["active", "invited"]}}, {"_id": 0})
        if not p or not _partner_can_message(member, p):
            return "That person is no longer available to message."
        thread = await get_or_create_direct_thread(org["org_id"], member, p)
        sent = await post_thread_message(org, member, thread, d["text"], spot=False)
        card["status"] = "sent"
        card["data"] = {**d, "thread_id": thread["thread_id"], "deliveries": sent.get("deliveries")}
    elif t == "rule":
        if not has_scope(member, "manage_team"):
            return "Only the owner or a team manager can set business rules."
        expires = d.get("until") if d.get("duration") == "temporary" else None
        r = await add_rule(org, member, d["text"], trigger=d.get("trigger") or "any", keyword=d.get("keyword"), notify_target=d.get("notify"),
                           condition={"scope_level": d.get("scope_level") or "company", "applies_to": d.get("applies_to")}, expires_at=expires)
        card["status"] = "saved"
        card["data"] = {**d, "rule_id": r["rule_id"]}
    elif t == "fact":
        if member.get("member_type") == "partner":
            return "External users cannot add to company memory."
        fid = new_id("fct")
        await db.knowledge.insert_one({"fact_id": fid, "org_id": org["org_id"], "text": d["text"][:400], "category": d.get("category") or fact_category(d["text"]),
                                       "source": "chat (confirmed)", "confirmed": True, "created_by": member["member_id"], "created_by_name": member["name"], "created_at": iso()})
        card["status"] = "saved"
        card["data"] = {**d, "fact_id": fid}
    elif t == "decision":
        ap = await db.approvals.find_one({"org_id": org["org_id"], "approval_id": d["approval_id"]}, {"_id": 0})
        if not has_scope(member, "approve"):
            return "You can't decide approvals."
        if not ap or ap["status"] != "pending":
            return "This approval was already decided."
        res = await decide_approval(org, member, ap, d["decision"], d.get("max_amount"), note=None)
        card["status"] = "applied"
        card["data"] = {**d, "summary": res["summary"]}
    elif t == "update":
        it = await get_item_for(member, d["item_id"])
        if not it or not can_edit_item(member, it):
            return "You can't change that item."
        res = await set_item_status(org, member, it, d["new_status"], d.get("reason"), d.get("new_due_at"), via="chat")
        card["status"] = "applied"
        card["data"] = {**d, "prev": res["prev"]}
    elif t == "business":
        if not is_owner(member):
            return "Only the owner can change the business profile."
        upd = {k: v for k, v in d.items() if k in ("name", "industry", "description", "country") and v}
        await db.orgs.update_one({"org_id": org["org_id"]}, {"$set": {**upd, "profile_learned": True}})
        card["status"] = "saved"
    elif t == "invite":
        if not has_scope(member, "manage_team"):
            return "Only the owner or a team manager can add people."
        m = await create_invite(org, member, d["name"], d.get("job") or "", d.get("member_type") or "team", d.get("phone"))
        card["status"] = "created"
        card["data"] = {"member_id": m["member_id"], "name": m["name"], "job": m["job"], "member_type": m["member_type"],
                        "access": m["access"], "access_reason": m["access_reason"], **invite_links(org, m)}
    else:
        return "Nothing to confirm."
    await audit(org["org_id"], member["member_id"], f"draft_confirmed_{t}", {"card_id": card["card_id"]})
    return None


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
    role = role_label(member)
    people = visible_people(member, await org_people(org["org_id"]))
    open_items = await visible_open_items(member, 40)
    approvals = await pending_approvals_for(member)
    rules = await active_rules(org["org_id"]) if can_read_rules(member) else []
    untrusted = (f"<untrusted_input source=\"attachments\">\n{extra_context[:3000]}\n</untrusted_input>" if extra_context else "")
    full_text = text + (f"\n\n{untrusted}" if untrusted else "")
    analysis = await brain.analyze(org, member, full_text, people, open_items, approvals, rules, cfg, role)
    source = {"type": channel, "msg_id": user_msg["msg_id"]}
    cards, summaries = await execute_actions(org, member, analysis, people, source)
    for a in attachments:
        if a.get("type") == "document" and a.get("doc_id"):
            cards.append({"card_id": new_id("crd"), "type": "doc", "status": "saved", "data": {"doc_id": a["doc_id"], "filename": a.get("filename"), "summary": a.get("summary", "")[:400]}})
    yield {"type": "cards", "cards": cards}

    sources = await retrieve(org, member, analysis.get("search_query") or "", text, include_open=True)
    live = await live_state(org, member)
    history = await _history(member)
    extra = (f"\nAttached content sent with this message:\n{untrusted}\n" if untrusted else "")
    extra += "\\n\\n" + brain.branch_context(analysis)
    if analysis.get("failed"):
        extra += "\n(Understanding step failed; answer helpfully and say nothing was drafted or saved.)"
    trusted = trusted_context(org, member, role)
    out = []
    async for d in brain.stream_reply(org, member, text, cfg, sources, summaries, history, extra, live, trusted):
        out.append(d)
        yield {"type": "delta", "text": d}
    reply = "".join(out).strip()
    msg = {"msg_id": new_id("bm"), "org_id": org["org_id"], "member_id": member["member_id"], "role": "assistant", "kind": "message",
           "text": reply, "cards": cards, "citations": _citations(reply, sources), "language": analysis.get("language"),
           "brain_branch": analysis.get("branch", "general"), "brain_subdomain": analysis.get("subdomain", "other"),
           "brain_response_mode": analysis.get("response_mode", "direct"), "brain_reasoning_level": analysis.get("reasoning_level", "standard"),
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
    elif card["type"] in DRAFT_TYPES and card["status"] == "draft" and op in ("confirm", "dismiss"):
        if op == "dismiss":
            card["status"] = "dismissed"
        else:
            err = await apply_draft(org, member, card)
            if err:
                return {"error": "forbidden", "message": err}
    elif card["type"] == "handover" and op in ("confirm", "dismiss", "undo"):
        d = card["data"]
        if op == "confirm" and card["status"] == "pending":
            if not has_scope(member, "manage_team"):
                return {"error": "forbidden", "message": "Only the owner or a team manager can hand over responsibilities."}
            p = await db.members.find_one({"member_id": d["to_member_id"], "org_id": org["org_id"]}, {"_id": 0})
            if not p:
                return {"error": "not_found"}
            body = d["message"]
            if d.get("restrictions") and not any(r.lower()[:20] in body.lower() for r in d["restrictions"]):
                body += "\n\nPlease note: " + "; ".join(d["restrictions"]) + "."
            thread = await get_or_create_direct_thread(org["org_id"], member, p)
            sent = await post_thread_message(org, member, thread, body, spot=False)
            rule_text = (f"Handover: {p['name']} manages operations for {member['name']}."
                         + (" " + "; ".join(d["restrictions"]) + "." if d.get("restrictions") else "")
                         + (f" Escalation: {d['escalation']}" if d.get("escalation") else ""))
            rule = await add_rule(org, member, rule_text, kind="handover", trigger="any", source="handover", expires_at=d.get("until"))
            act_id = new_id("act")
            await db.activity_log.insert_one({"activity_id": act_id, "org_id": org["org_id"], "kind": "owner_instruction", "text": d.get("log_text") or rule_text,
                                              "by": member["member_id"], "by_name": member["name"], "to_member_id": p["member_id"], "rule_id": rule["rule_id"],
                                              "until": d.get("until"), "created_at": iso()})
            await audit(org["org_id"], member["member_id"], "handover_confirmed", {"to": p["member_id"], "rule_id": rule["rule_id"], "activity_id": act_id})
            card["status"] = "confirmed"
            card["data"] = {**d, "rule_id": rule["rule_id"], "thread_id": thread["thread_id"], "activity_id": act_id, "deliveries": sent.get("deliveries"), "confirmed_at": iso()}
        elif op == "dismiss" and card["status"] == "pending":
            card["status"] = "dismissed"
        elif op == "undo" and card["status"] == "confirmed" and d.get("rule_id"):
            await db.rules.update_one({"rule_id": d["rule_id"], "org_id": org["org_id"]}, {"$set": {"active": False, "removed_at": iso()}})
            card["status"] = "ended"
    elif op == "undo":
        if card["type"] == "message":
            return {"error": "forbidden", "message": "A sent message can't be unsent."}
        if card["type"] == "business" and card["status"] == "saved":
            return {"error": "forbidden", "message": "Change the business profile in Settings."}
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
        return res["summary"] + (" You can undo it any time in Approvals." if via == "app" else " Reply UNDO to change it.")
    if op in ("confirm", "dismiss"):
        msg = await db.brain_messages.find_one({"msg_id": ref, "member_id": member["member_id"]}, {"_id": 0})
        if not msg:
            return "I couldn't find that."
        done, failed = [], []
        for c in msg.get("cards", []):
            if c["status"] == "draft" or (c["type"] == "handover" and c["status"] == "pending"):
                r = await card_action(org, member, c["card_id"], op)
                (failed if r.get("error") else done).append(r.get("message") or draft_line(c))
        if op == "dismiss":
            return "Okay, nothing was done."
        return ("Done: " + "; ".join(done) + "." if done else "Nothing was done.") + (" Not done: " + "; ".join(failed) if failed else "")
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


async def handle_pending_reply(org: dict, member: dict, state: dict, text: str, via: str = "whatsapp") -> str:
    if state["kind"] == "reason":
        item = await get_item_for(member, state["ref"])
        if not item:
            return "I couldn't find that item."
        status = state["extra"].get("status", "delayed")
        # look for a date in the reason via the brain (best-effort)
        await set_item_status(org, member, item, status, reason=text[:300], via=via)
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
