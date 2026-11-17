"""KONNTO demo workspace: three ready-made sign-ins (owner, team lead, supplier) inside one fully lived-in business.

Run from /app/backend:  python demo_account.py        (rebuilds the demo from scratch — safe to repeat)
Or as an admin:         POST /api/admin/demo/reset

Sign-in works on the preview (Clerk development instance): enter the email, then the code 424242.
"""
import os
import asyncio
import logging
from datetime import timedelta

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from core import db, now, iso, new_id, short_code, SCOPES, ENV  # noqa: E402
from storage import put_object, APP_NAME  # noqa: E402

logger = logging.getLogger("konnto.demo")

DEMO_KEY = "konnto-demo"
DEMO_CODE = "424242"
DEMO_USERS = {
    "owner": {"email": "demo.owner+clerk_test@konnto.ai", "first": "Arjun", "last": "Mehra"},
    "priya": {"email": "demo.priya+clerk_test@konnto.ai", "first": "Priya", "last": "Nair"},
    "partner": {"email": "demo.supplier+clerk_test@konnto.ai", "first": "Rajesh", "last": "Gupta"},
}
ORG_COLLECTIONS = ["members", "items", "projects", "approvals", "rules", "knowledge", "documents", "files", "threads", "thread_messages",
                   "brain_messages", "activity_log", "audit", "usage", "outbox", "pending_states", "briefs_sent"]


# ---------------------------------------------------------------- Clerk users (development instance)
def _clerk(path: str, body=None, method: str = "POST"):
    r = requests.request(method, "https://api.clerk.com/v1" + path, json=body, timeout=20,
                         headers={"Authorization": f"Bearer {os.environ['CLERK_SECRET_KEY']}", "User-Agent": "konnto-demo"})
    r.raise_for_status()
    return r.json()


def ensure_clerk_user(email: str, first: str, last: str) -> str:
    found = _clerk(f"/users?email_address={requests.utils.quote(email)}", method="GET")
    if found:
        return found[0]["id"]
    u = _clerk("/users", {"email_address": [email], "first_name": first, "last_name": last,
                          "password": "Konnto-Demo-2026!", "skip_password_checks": True})
    return u["id"]


# ---------------------------------------------------------------- helpers
def _h(by: str, text: str, at) -> dict:
    return {"at": iso(at), "by": by, "text": text}


async def _wipe_previous():
    old = await db.orgs.find({"demo_key": DEMO_KEY}, {"_id": 0, "org_id": 1}).to_list(20)
    ids = [o["org_id"] for o in old]
    if not ids:
        return 0
    for c in ORG_COLLECTIONS:
        await db[c].delete_many({"org_id": {"$in": ids}})
    await db.orgs.delete_many({"org_id": {"$in": ids}})
    return len(ids)


async def _store_text_file(org_id: str, member_id: str, filename: str, text: str, ctype: str) -> str:
    path = f"{APP_NAME}/{org_id}/document/{new_id('f')}.{filename.rsplit('.', 1)[-1]}"
    stored = path
    try:
        res = await put_object(path, text.encode(), ctype)
        stored = res.get("path", path)
    except Exception as e:  # storage unavailable: the document still shows, only the download would fail
        logger.warning("demo storage put failed: %s", e)
    fid = new_id("fil")
    await db.files.insert_one({"file_id": fid, "org_id": org_id, "member_id": member_id, "storage_path": stored, "content_type": ctype,
                               "size": len(text.encode()), "kind": "document", "filename": filename, "is_deleted": False, "created_at": iso()})
    return fid


# ---------------------------------------------------------------- build
async def build_demo(create_logins: bool = True) -> dict:
    ref = now()
    wiped = await _wipe_previous()

    uids = {}
    if create_logins and os.environ.get("CLERK_SECRET_KEY"):
        for k, u in DEMO_USERS.items():
            uids[k] = ensure_clerk_user(u["email"], u["first"], u["last"])

    org_id = new_id("org")
    org = {"org_id": org_id, "name": "Mehra Build Supplies", "industry": "Building materials wholesale",
           "description": "Wholesale cement, TMT steel and bricks for builders across Pune and PCMC. 6 people, 1 warehouse, ~40 active builder accounts.",
           "country": "IN", "currency": "INR", "timezone": "Asia/Kolkata", "owner_user_id": uids.get("owner"), "created_at": iso(ref - timedelta(days=21)),
           "profile_learned": True, "briefs": {"enabled": True, "morning_hour": 8, "evening_hour": 19}, "limits": {},
           "demo_key": DEMO_KEY, "is_demo": True}
    await db.orgs.insert_one(dict(org))

    # ---- people ----
    def member(key, name, job, mtype, access, phone=None, email=None, user_key=None, status="active", days_ago=20, persona=None, extra=None):
        m = {"member_id": new_id("mem"), "org_id": org_id, "user_id": uids.get(user_key) if user_key else None, "name": name, "job": job,
             "member_type": mtype, "phone": phone, "email": email, "access": access,
             "access_reason": {"owner": "Owner — sees everything.", "team": f"Set for a {job}.", "partner": "External partner — only their own work."}[mtype],
             "status": status, "wa_opt_in": False, "manager_id": None, "joined_via": "demo", "created_at": iso(ref - timedelta(days=days_ago)),
             "joined_at": iso(ref - timedelta(days=days_ago)) if status == "active" else None}
        if persona:
            m["brain_persona"] = persona
        m.update(extra or {})
        return m

    owner = member("owner", "Arjun Mehra", "Owner", "owner", list(SCOPES.keys()), "919800000101", DEMO_USERS["owner"]["email"], "owner", days_ago=21, persona="chief_of_staff")
    priya = member("priya", "Priya Nair", "Operations Lead", "team", ["own_work", "team_work", "documents", "manage_team"], "919800000102",
                   DEMO_USERS["priya"]["email"], "priya", days_ago=19, persona="assistant")
    anita = member("anita", "Anita Desai", "Accountant", "team", ["own_work", "documents", "money", "approve"], "919800000103", None, days_ago=18)
    ramesh = member("ramesh", "Ramesh Kumar", "Site Supervisor", "team", ["own_work"], "919800000104", None, days_ago=18)
    vikram = member("vikram", "Vikram Singh", "Sales Executive", "team", ["own_work", "team_work"], "919800000105", None, days_ago=12)
    gupta = member("gupta", "Rajesh Gupta", "Gupta Cement — supplier", "partner", ["own_work"], "919800000106", DEMO_USERS["partner"]["email"], "partner", days_ago=15)
    mehta = member("mehta", "Karan Mehta", "Mehta Builders — customer", "partner", ["own_work"], "919800000107", None, days_ago=10)
    sameer = member("sameer", "Sameer Khan", "Delivery Driver", "team", ["own_work"], "919800000108", None, status="invited", days_ago=1,
                    extra={"invite_token": new_id("inv") + short_code(10), "invite_code": short_code(6)})
    people = [owner, priya, anita, ramesh, vikram, gupta, mehta, sameer]
    for p in people[1:]:
        p["invited_by"], p["invited_by_name"], p["manager_id"] = owner["member_id"], owner["name"], owner["member_id"]
    await db.members.insert_many([dict(p) for p in people])

    for key, m in (("owner", owner), ("priya", priya), ("partner", gupta)):
        if uids.get(key):
            await db.users.update_one({"user_id": uids[key]}, {
                "$setOnInsert": {"user_id": uids[key], "created_at": iso(), "auth": "clerk"},
                "$set": {"email": DEMO_USERS[key]["email"], "name": m["name"], "role": "member", "env": ENV, "whatsapp": m["phone"],
                         "current_org_id": org_id, "is_demo": True}}, upsert=True)

    # ---- projects ----
    projects = {}
    for key, name, desc, days in [("mehta", "Mehta Tower — Phase 2 supply", "1,200 bags cement + 40 t TMT steel for Mehta Builders' Baner tower.", 14),
                                  ("monsoon", "Monsoon Sale 2026", "10% off cement + free delivery above ₹50k, 15 Jul – 31 Jul.", 9),
                                  ("warehouse", "Warehouse move to Hadapsar", "Shift stock from Kharadi to the bigger Hadapsar warehouse before August.", 7),
                                  ("ops", "Daily operations", "Bills, licences, upkeep and routine follow-ups.", 21)]:
        pid = new_id("prj")
        projects[key] = pid
        await db.projects.insert_one({"project_id": pid, "org_id": org_id, "name": name, "description": desc, "status": "active",
                                      "created_by": owner["member_id"], "created_at": iso(ref - timedelta(days=days))})

    # ---- work items ----
    D = lambda **kw: ref + timedelta(**kw)  # noqa: E731
    from zoneinfo import ZoneInfo
    day0 = ref.astimezone(ZoneInfo("Asia/Kolkata")).replace(hour=0, minute=0, second=0, microsecond=0)
    L = lambda d, h, mi=0: day0 + timedelta(days=d, hours=h, minutes=mi)  # noqa: E731  fixed local (IST) times

    def today_at(h):  # "due today" that is still ahead, whatever time the demo is rebuilt
        t = L(0, h)
        return t if t > ref + timedelta(minutes=45) else min(ref + timedelta(hours=1), L(0, 23, 50))
    dname = lambda d: L(d, 12).strftime("%A")  # noqa: E731
    items = {}

    def item(key, kind, title, who, proj, *, details="", due=None, remind=None, status="open", by=owner, amount=None, counterparty=None,
             depends=None, private=False, chase=0, delay=None, stuck=None, done=None, request=False, created_days=3, history=None):
        iid = new_id("itm")
        items[key] = iid
        created = ref - timedelta(days=created_days)
        hist = [_h(by["name"], f"Created{' for ' + who['name'] if who['member_id'] != by['member_id'] else ''}", created)] + (history or [])
        return {"item_id": iid, "org_id": org_id, "kind": kind, "title": title, "details": details, "status": status,
                "assignee_id": who["member_id"], "assignee_name": who["name"], "created_by": by["member_id"], "created_by_name": by["name"],
                "counterparty": counterparty, "due_at": iso(due) if due else None, "remind_at": iso(remind) if remind else None, "reminded_at": None,
                "amount": amount, "currency": "INR" if amount is not None else None, "depends_on": [items[d] for d in (depends or [])],
                "project_id": projects[proj], "is_request": request, "visibility": "private" if private else "org",
                "watchers": list({by["member_id"], owner["member_id"]}), "source": {"type": "demo"}, "chase_level": chase,
                "last_chased_at": iso(ref - timedelta(hours=6)) if chase else None, "delay_reason": delay, "stuck_reason": stuck,
                "history": hist, "created_at": iso(created), "updated_at": iso(ref - timedelta(hours=2)), "done_at": iso(done) if done else None}

    rows = [
        # Mehta Tower
        item("quote", "task", "Send Mehta Builders the revised quote for 1,200 cement bags", priya, "mehta",
             details="Karan asked for OPC 53 at the new rate. Include delivery in 3 lots. They decide by Friday.", due=L(-1, 13),
             amount=492000, chase=1, created_days=4, history=[_h("KONNTO", "Chased Priya on WhatsApp — no reply yet", ref - timedelta(hours=6))]),
        item("gupta_delivery", "promise", "Deliver 500 bags OPC 53 to the Mehta Baner site", gupta, "mehta", counterparty="Gupta Cement",
             details="Promised on Monday's call. Afternoon slot, 2–6 pm.", due=L(2, 15), remind=L(1, 10), amount=185000, created_days=3),
        item("unload", "task", "Unload and count the Gupta delivery at the Mehta site", ramesh, "mehta", due=L(2, 18), depends=["gupta_delivery"],
             details="Count bags, check for torn ones, photo of the challan.", created_days=3),
        item("inv2041", "promise", "Mehta Builders to pay invoice #INV-2041", anita, "mehta", counterparty="Mehta Builders", amount=340000,
             due=L(-3, 18), chase=1, details="Phase 1 steel. 45-day terms ended last week.", created_days=50),
        item("po", "task", "Get the signed PO from Karan Mehta for Phase 2 steel", vikram, "mehta", status="in_progress", due=L(1, 17),
             delay=f"Karan is travelling till {dname(1)}", created_days=5, history=[_h("Vikram Singh", f"Delayed: Karan is travelling till {dname(1)} (via whatsapp)", ref - timedelta(days=1))]),
        # Monsoon sale
        item("flyer", "task", "Design the monsoon sale WhatsApp flyer", vikram, "monsoon", due=today_at(18), created_days=2,
             details="Square image + 3-line caption. Mention free delivery above ₹50k."),
        item("stock", "task", "Confirm TMT steel stock before the sale", priya, "monsoon", status="done", due=L(-2, 12), done=L(-2, 14),
             created_days=6, history=[_h("Priya Nair", "Marked done via whatsapp", ref - timedelta(days=2))]),
        item("idea", "note", "Idea: bundle bricks + cement for small contractors", owner, "monsoon", private=True, created_days=4,
             details="Only for my eyes until I check margins."),
        item("broadcast", "reminder", "Launch the monsoon sale broadcast to all builders", owner, "monsoon", due=L(3, 11), remind=L(3, 9)),
        # Warehouse
        item("quotes3", "task", "Get 3 quotes for warehouse shifting", ramesh, "warehouse", status="stuck", due=L(-1, 18),
             stuck="Two of the three movers haven't replied", created_days=6, history=[_h("Ramesh Kumar", "Stuck: Two of the three movers haven't replied", ref - timedelta(days=1))]),
        item("lease", "task", "Sign the Hadapsar warehouse lease", owner, "warehouse", due=L(6, 12), amount=85000,
             details="₹85,000 / month, 11-month term. Draft lease is in Documents.", depends=["quotes3"], created_days=5),
        item("deposit", "task", "Pay the security deposit for Hadapsar", anita, "warehouse", due=L(5, 12), amount=250000, depends=["lease"], created_days=5),
        # Daily ops
        item("power", "reminder", "Pay the warehouse electricity bill", owner, "ops", due=L(3, 12), remind=L(2, 10), amount=14200),
        item("jsw", "task", "Review the new JSW Steel price list", owner, "ops", due=today_at(16), created_days=1, details="Rates went up ~3%. Check if we pass it on."),
        item("gst", "task", "File last month's GST return", anita, "ops", due=L(8, 18), created_days=2),
        item("forklift", "task", "Fix the forklift hydraulic leak", ramesh, "ops", due=L(-2, 18), chase=2, created_days=5,
             history=[_h("KONNTO", "Chased Ramesh (2nd reminder)", ref - timedelta(hours=20))]),
        item("call_md", "task", "Call Gupta Cement's MD about the price hike", owner, "ops", by=priya, request=True, due=L(1, 11), created_days=1,
             details="Priya thinks a call from you will hold this week's rate."),
        item("licence", "task", "Renew the trade licence", owner, "ops", status="done", due=L(-5, 18), done=L(-4, 12), created_days=10),
        item("sharma", "task", "Collect payment from Sharma Hardware", vikram, "ops", status="done", amount=62000, due=L(-1, 18), done=L(-1, 15), created_days=7),
        item("tape", "task", "Order packaging tape and stretch film", ramesh, "ops", status="done", due=L(-6, 18), done=L(-6, 16), created_days=9),
        item("shree", "task", "Trial order with Shree Cement", priya, "ops", status="cancelled", created_days=12,
             history=[_h("Arjun Mehra", "Cancelled", ref - timedelta(days=8))]),
        item("visit", "task", "Visit 5 new builder sites in Wakad", vikram, "monsoon", due=L(4, 12), created_days=1),
    ]
    await db.items.insert_many([dict(r) for r in rows])

    # ---- approvals ----
    def appr(kind, title, by, amount=None, details="", status="pending", hours=5, decided_by=None, text=None, scope=None, question=None, rule_id=None, max_amount=None):
        return {"approval_id": new_id("apr"), "org_id": org_id, "kind": kind, "title": title, "details": details, "amount": amount,
                "currency": "INR" if amount is not None else None, "requested_by": by["member_id"], "requested_by_name": by["name"], "scope": scope,
                "question": question, "payload": {}, "status": status, "decided_by": (decided_by or {}).get("member_id"),
                "decided_by_name": (decided_by or {}).get("name") if decided_by else ("Business rule" if status == "allowed_by_rule" else None),
                "decided_at": iso(ref - timedelta(hours=hours - 1)) if status != "pending" else None, "decision_text": text, "rule_id": rule_id,
                "max_amount": max_amount, "source": {"type": "demo"}, "created_at": iso(ref - timedelta(hours=hours))}

    perm_rule_id = new_id("rul")
    approvals = [
        appr("payment", "Advance to Gupta Cement for the Mehta order", priya, 42000, hours=20,
             details="Gupta wants 50% upfront to lock this week's rate before Monday's price rise. Mehta's delivery depends on it."),
        appr("order", "Spare parts for the forklift repair", ramesh, 8500, hours=4, details="Hydraulic seal kit + oil. Mechanic can fix it tomorrow if parts arrive."),
        appr("time_off", "Leave on Friday for a family function", vikram, hours=9, details="Will hand the Wakad visits to Priya."),
        appr("access", "See amounts, orders and payments", priya, hours=2, scope="money", question="What's our margin on the Mehta order?"),
        appr("payment", "Refund for 6 torn bags — Sharma Hardware", ramesh, 6800, hours=30, details="Customer is waiting on a call-back before next month's order."),
        appr("order", "Site consumables (gloves, tarpaulin)", ramesh, 4800, status="allowed_always", hours=120, decided_by=owner,
             text="Ramesh can order site consumables up to ₹5,000 without asking.", rule_id=perm_rule_id, max_amount=5000),
        appr("payment", "Pay JSW Steel invoice #J-7781", anita, 120000, status="allowed_once", hours=72, decided_by=owner, text="Allowed once by Arjun Mehra"),
        appr("other", "New phone for sales calls", vikram, 15000, status="denied", hours=96, decided_by=owner, text="Not this quarter — use the office phone."),
        appr("order", "Tarpaulin sheets for the Mehta site", ramesh, 3200, status="allowed_by_rule", hours=26,
             text="Ramesh can order site consumables up to ₹5,000 without asking.", rule_id=perm_rule_id),
    ]
    await db.approvals.insert_many([dict(a) for a in approvals])

    # ---- rules (business memory) ----
    def rule(text, kind="behaviour", trigger="any", keyword=None, notify=None, condition=None, days=5, expires=None, rid=None, source="chat"):
        return {"rule_id": rid or new_id("rul"), "org_id": org_id, "text": text, "kind": kind, "trigger": trigger, "keyword": keyword,
                "notify_target": notify, "condition": condition or {"scope_level": "company"}, "created_by": owner["member_id"],
                "created_by_name": owner["name"], "source": source, "active": True, "expires_at": iso(expires) if expires else None,
                "created_at": iso(ref - timedelta(days=days))}

    rules = [
        rule("Whenever a payment approval comes in, tell Anita.", trigger="approval", keyword="payment", notify="Anita", days=10),
        rule("Tell Priya about every new task for the Mehta order.", trigger="task", keyword="mehta", notify="Priya", days=8),
        rule("Ramesh can order site consumables up to ₹5,000 without asking.", kind="permission", trigger="approval",
             condition={"approval_kind": "order", "member_id": ramesh["member_id"], "max_amount": 5000}, days=5, rid=perm_rule_id, source="approval"),
        rule("Never share our purchase prices with customers or suppliers.", days=14),
        rule("Monsoon sale: 10% off cement and free delivery above ₹50,000.", days=3, expires=D(days=20),
             condition={"scope_level": "company", "applies_to": "sales"}),
    ]
    await db.rules.insert_many([dict(r) for r in rules])

    # ---- knowledge facts ----
    facts = [
        ("We supply cement, TMT steel and bricks to ~40 builders across Pune and PCMC.", "other", False),
        ("Gupta Cement deliveries always come in the afternoon slot (2–6 pm).", "other", True),
        ("The warehouse is closed every Sunday.", "other", True),
        ("Mehta Builders usually pays within 45 days of the invoice.", "other", False),
        ("Karan Mehta prefers calls after 11 am.", "other", False),
        ("Ramesh handles all site deliveries; Priya handles customer quotes.", "other", False),
        ("Our wholesale margin on cement is usually 8–12%.", "finance", False),
        ("Cash in bank is about ₹24.1 lakh this week.", "finance", False),
        ("Credit limit for new customers is ₹2 lakh until they make 3 on-time payments.", "finance", False),
    ]
    await db.knowledge.insert_many([{"fact_id": new_id("fct"), "org_id": org_id, "text": t, "category": c, "confirmed": True, "shared_with_partners": s,
                                     "source": "chat (confirmed)", "created_by": owner["member_id"], "created_by_name": owner["name"],
                                     "created_at": iso(ref - timedelta(days=12 - i))} for i, (t, c, s) in enumerate(facts)])

    # ---- documents ----
    docs_spec = [
        ("Quote_Mehta_Tower_Phase2.txt", "text/plain", "org", priya, 3, "quote",
         "Draft quote for Mehta Builders' Phase 2: 1,200 bags OPC 53 cement in three lots at ₹410/bag, total ₹4,92,000 plus GST.",
         [("Customer", "Mehta Builders"), ("Quantity", "1,200 bags OPC 53"), ("Rate", "₹410 / bag"), ("Total", "₹4,92,000 + GST"), ("Valid till", "Friday")],
         "QUOTATION — Mehra Build Supplies\nCustomer: Mehta Builders (Karan Mehta)\nProject: Mehta Tower, Baner — Phase 2\n\nItem: OPC 53 grade cement\nQuantity: 1,200 bags (3 lots of 400)\nRate: Rs 410 per bag\nTotal: Rs 4,92,000 + 18% GST\nDelivery: Lot 1 within 3 days of PO, then weekly\nPayment terms: 45 days from invoice\nValid till: Friday\n"),
        ("Gupta_Cement_Rate_Card_July.csv", "text/csv", "org", owner, 6, "rate card",
         "Gupta Cement's July rate card for OPC 43, OPC 53 and PPC cement, with a price rise from next Monday.",
         [("Supplier", "Gupta Cement"), ("OPC 53", "₹372 / bag"), ("PPC", "₹355 / bag"), ("Price rise", "+₹12 / bag from Monday")],
         "grade,rate_per_bag,min_order,price_from_monday\nOPC 43,360,200,372\nOPC 53,372,200,384\nPPC,355,200,367\n"),
        ("Hadapsar_Warehouse_Lease_Draft.txt", "text/plain", "org", owner, 5, "contract",
         "Draft 11-month lease for the Hadapsar warehouse at ₹85,000 a month with a ₹2,50,000 deposit.",
         [("Rent", "₹85,000 / month"), ("Deposit", "₹2,50,000"), ("Term", "11 months"), ("Lock-in", "6 months"), ("Area", "6,500 sq ft")],
         "LEAVE AND LICENCE AGREEMENT (DRAFT)\nLicensor: Shinde Estates\nLicensee: Mehra Build Supplies\nPremises: Plot 14, Hadapsar Industrial Estate, 6,500 sq ft\nMonthly fee: Rs 85,000\nSecurity deposit: Rs 2,50,000 (refundable)\nTerm: 11 months, lock-in 6 months\nStart: 1 August\n"),
        ("Owner_Cashflow_Notes.txt", "text/plain", "private", owner, 2, "notes",
         "Arjun's private cash-flow notes: bank balance, receivables due, and the big payments planned for the next 30 days.",
         [("Bank balance", "₹24.1 lakh"), ("Receivables", "₹8.3 lakh"), ("Big outflows", "Deposit ₹2.5 lakh, JSW ₹1.2 lakh")],
         "Cash this week: Rs 24.1 lakh\nReceivables due: Rs 8.3 lakh (Mehta INV-2041 is the biggest at 3.4 lakh)\nPlanned outflows: Hadapsar deposit 2.5 lakh, JSW 1.2 lakh, salaries 3.1 lakh\n"),
    ]
    doc_ids = {}
    for fn, ctype, vis, by, days, dtype, summary, kd, text in docs_spec:
        fid = await _store_text_file(org_id, by["member_id"], fn, text, ctype)
        did = new_id("doc")
        doc_ids[fn] = did
        await db.documents.insert_one({"doc_id": did, "org_id": org_id, "file_id": fid, "uploaded_by": by["member_id"], "uploaded_by_name": by["name"],
                                       "filename": fn, "content_type": ctype, "size": len(text.encode()), "text": text, "summary": summary, "doc_type": dtype,
                                       "key_details": [{"label": a, "value": b} for a, b in kd], "found_items": [], "visibility": vis,
                                       "is_deleted": False, "created_at": iso(ref - timedelta(days=days))})

    # ---- team chats ----
    async def thread(kind, members, msgs, name=None):
        tid = new_id("thr")
        last = msgs[-1]
        await db.threads.insert_one({"thread_id": tid, "org_id": org_id, "kind": kind, "member_ids": sorted(m["member_id"] for m in members), "name": name,
                                     "created_by": owner["member_id"], "created_at": iso(ref - timedelta(days=7)),
                                     "last_message_at": iso(ref - timedelta(hours=last[1])),
                                     "last_message_preview": f"{last[0]['name'].split()[0]}: {last[2][:100]}",
                                     "reads": {owner["member_id"]: iso(ref - timedelta(hours=last[1] + 1))}})
        for sender, hrs, text, *extra in msgs:
            cards = extra[0] if extra else []
            await db.thread_messages.insert_one({"msg_id": new_id("tm"), "thread_id": tid, "org_id": org_id, "sender_id": sender["member_id"],
                                                 "sender_name": sender["name"], "kind": "text", "text": text, "item_id": None, "cards": cards,
                                                 "deliveries": [], "created_at": iso(ref - timedelta(hours=hrs))})
        return tid

    await thread("direct", [owner, priya], [
        (priya, 26, "Karan asked again about the Phase 2 quote. Can I go with ₹410 a bag?"),
        (owner, 25.5, "Yes, ₹410 is fine. Don't go below ₹402 without asking me."),
        (priya, 25, "Got it. I'll send it tomorrow morning."),
        (priya, 3, "Sorry, yesterday got busy with the stock count. Sending the quote by 1 pm today."),
    ])
    await thread("direct", [owner, ramesh], [
        (ramesh, 30, "Forklift is leaking oil again. Mechanic says seal kit needed."),
        (owner, 29, "Raise the parts request in KONNTO, I'll approve it."),
        (ramesh, 4, "Request sent. ₹8,500."),
    ])
    await thread("direct", [owner, gupta], [
        (gupta, 50, f"Namaste Arjun ji, 500 bags OPC 53 confirmed for {dname(2)} afternoon."),
        (owner, 49, "Thanks Rajesh ji. Please send the challan photo once loaded."),
        (gupta, 8, "Rate goes up ₹12 from Monday. If you pay 50% advance this week I'll hold the old rate."),
    ])
    spotted = [{"card_id": new_id("crd"), "type": "proposal", "status": "pending", "data": {
        "kind": "task", "title": "Share the delivery photos with Mehta Builders", "details": "Spotted in the Mehta Tower team chat",
        "assignee_id": vikram["member_id"], "assignee_name": vikram["name"], "due_at": iso(L(2, 19)), "remind_at": None,
        "amount": None, "currency": None, "counterparty": "Mehta Builders", "project": "Mehta Tower — Phase 2 supply", "private": False}}]
    await thread("group", [owner, priya, ramesh, vikram], [
        (owner, 48, "Team — Mehta Phase 2 is our biggest order this quarter. Let's not slip on dates."),
        (ramesh, 47, f"Site is ready for unloading from {dname(2)}. Need 2 extra labourers."),
        (priya, 46, "I'll arrange the labourers through Sunil."),
        (vikram, 5, f"I'll send Karan the delivery photos on {dname(2)} after unloading.", spotted),
    ], name="Mehta Tower team")
    await thread("direct", [priya, vikram], [
        (vikram, 20, "Can you cover the Wakad visits on Friday if my leave is approved?"),
        (priya, 19, "Sure, send me the list."),
    ])

    # ---- activity log ----
    await db.activity_log.insert_one({"activity_id": new_id("act"), "org_id": org_id, "kind": "owner_instruction",
                                      "text": "OWNER INSTRUCTION — Arjun was at the cement expo. Priya managed operations. RESTRICTION: no payments above ₹10,000.",
                                      "by": owner["member_id"], "by_name": owner["name"], "to_member_id": priya["member_id"], "rule_id": None,
                                      "until": iso(ref - timedelta(days=6)), "created_at": iso(ref - timedelta(days=7))})

    # ---- K-BRAIN chat history (owner) ----
    def bm(mem, role, hrs, text, kind="message", cards=None, citations=None, buttons=None, link_path=None):
        return {"msg_id": new_id("bm"), "org_id": org_id, "member_id": mem["member_id"], "role": role, "kind": kind, "text": text,
                "cards": cards or [], "citations": citations or [], "buttons": buttons or [], "link_path": link_path, "channel": "app",
                "attachments": [], "created_at": iso(ref - timedelta(hours=hrs))}

    def cite(n, type_, id_, title, link):
        return {"n": n, "type": type_, "id": id_, "title": title, "link": link}

    def prop(title, who, kind="task", due=None, amount=None, counterparty=None, project=None, status="pending", item_key=None):
        c = {"card_id": new_id("crd"), "type": "proposal", "status": status, "data": {
            "kind": kind, "title": title, "details": "", "assignee_id": who["member_id"], "assignee_name": who["name"], "counterparty": counterparty,
            "due_at": iso(due) if due else None, "remind_at": None, "amount": amount, "currency": "INR" if amount else None, "project": project,
            "private": kind == "note"}}
        if item_key:
            c["item_id"] = items[item_key]
        return c

    def draft(type_, data, status="draft"):
        return {"card_id": new_id("crd"), "type": type_, "status": status, "data": data}

    ap_forklift = approvals[1]
    owner_chat = [
        bm(owner, "assistant", 52, f"Good morning, Arjun. **Mehra Build Supplies — {dname(-2)}**\n\n- 2 tasks are overdue — the forklift repair has been chased twice.\n"
                                   f"- Gupta confirmed 500 bags for {dname(2)} afternoon.\n- 2 approvals are waiting.\n\nWhat do you want to move first?", kind="brief"),
        bm(owner, "user", 50, f"Gupta will deliver 500 bags to the Mehta site on {dname(2)} afternoon. Ramesh should unload and count them once it arrives."),
        bm(owner, "assistant", 49.9, f"Two things drafted — tap **Save** on each:\n\n1. **Promise** — Gupta Cement: 500 bags OPC 53 to the Mehta Baner site, {dname(2)} afternoon.\n"
                                     "2. **Task** — Ramesh: unload and count, linked so it starts only after the delivery is marked done.\n\nI'll remind you " + dname(1) + " to confirm the truck.",
           cards=[prop("Deliver 500 bags OPC 53 to the Mehta Baner site", gupta, "promise", L(2, 15), 185000, "Gupta Cement", "Mehta Tower — Phase 2 supply", "saved", "gupta_delivery"),
                  prop("Unload and count the Gupta delivery at the Mehta site", ramesh, "task", L(2, 18), project="Mehta Tower — Phase 2 supply", status="saved", item_key="unload")]),
        bm(owner, "user", 30, "From now on, whenever a payment approval comes in, tell Anita."),
        bm(owner, "assistant", 29.9, "Drafted a **permanent company rule**: every new payment approval also goes to Anita (Accountant). Confirm to switch it on.",
           cards=[draft("rule", {"text": "Whenever a payment approval comes in, tell Anita.", "trigger": "approval", "keyword": "payment", "notify": "Anita",
                                 "duration": "permanent", "until": None, "scope_level": "company", "applies_to": None, "rule_id": rules[0]["rule_id"]}, "saved")]),
        bm(owner, "user", 6, "What's stuck or late right now?"),
        bm(owner, "assistant", 5.9, "**3 things need you today:**\n\n| What | Who | Why it matters |\n|---|---|---|\n"
                                    "| Mehta quote [1] | Priya | Overdue 1 day — ₹4.92 lakh order, they decide Friday |\n"
                                    "| Forklift leak [2] | Ramesh | Chased twice; parts request (₹8,500) is waiting on you |\n"
                                    "| Warehouse movers [3] | Ramesh | Stuck — 2 of 3 movers silent, lease signing depends on it |\n\n"
                                    "**My call:** approve the forklift parts now, and ping Priya — she said 1 pm for the quote. Want me to draft that message?",
           citations=[cite(1, "work", items["quote"], "Send Mehta Builders the revised quote for 1,200 cement bags", f"/app/work?item={items['quote']}"),
                      cite(2, "work", items["forklift"], "Fix the forklift hydraulic leak", f"/app/work?item={items['forklift']}"),
                      cite(3, "work", items["quotes3"], "Get 3 quotes for warehouse shifting", f"/app/work?item={items['quotes3']}")]),
        bm(owner, "user", 5.8, "Yes, message Priya. And remember that Mehta Builders usually pays within 45 days."),
        bm(owner, "assistant", 5.7, "Both drafted — nothing is sent or saved until you confirm:\n\n- **Message to Priya** — a short nudge on the quote.\n- **Remember** — Mehta's 45-day payment habit, so I can flag late payments.",
           cards=[draft("message", {"to_member_id": priya["member_id"], "to_name": priya["name"],
                                    "text": "Hi Priya — quick nudge on the Mehta Phase 2 quote. Can it go out by 1 pm today as planned? Karan decides on Friday."}),
                  draft("fact", {"text": "Karan Mehta's site manager signs for deliveries — always get his name on the challan.", "category": "other"})]),
        bm(owner, "user", 1.2, "I'm at the bank all afternoon tomorrow. Priya can run things, but no payments above ₹10,000."),
        bm(owner, "assistant", 1.1, "Handover prepared for **Priya Nair (Operations Lead)** until tomorrow night. She gets the message below only when you tap **Confirm**.\n\n"
                                    "- Restriction: no payments above ₹10,000\n- Anything bigger waits for you.",
           cards=[{"card_id": new_id("crd"), "type": "handover", "status": "pending", "data": {
               "to_member_id": priya["member_id"], "to_name": priya["name"], "to_job": priya["job"],
               "message": "Hi Priya, I'm at the bank tomorrow afternoon. Please run operations. No payments above ₹10,000 — those wait for me.",
               "restrictions": ["No payments above ₹10,000"], "escalation": "Call Arjun for anything urgent above ₹10,000.",
               "until": iso(L(1, 23, 59)), "log_text": "OWNER INSTRUCTION — Arjun at the bank tomorrow afternoon. Priya manages operations. RESTRICTION: no payments above ₹10,000."}}]),
        bm(owner, "assistant", 0.9, f"{ramesh['name']} asks: {ap_forklift['title']} (₹8,500).", kind="approval",
           buttons=[{"id": f"ap_once:{ap_forklift['approval_id']}", "label": "Allow once"}, {"id": f"ap_always:{ap_forklift['approval_id']}", "label": "Always allow"},
                    {"id": f"ap_deny:{ap_forklift['approval_id']}", "label": "Don't allow"}], link_path="/app/approvals"),
        bm(owner, "assistant", 0.5, "Good morning, Arjun. Here's today for **Mehra Build Supplies**:\n\n"
                                    "- **3 overdue** — Mehta quote (Priya), forklift (Ramesh), Mehta's ₹3.4 lakh payment.\n"
                                    "- **Due soon** — JSW price list (you), monsoon flyer (Vikram).\n"
                                    "- **5 approvals waiting** — the Gupta advance (₹42,000) is time-sensitive: rate rises Monday.\n"
                                    "- 1 handover is drafted and waiting for your confirm.\n\nTell me what to move first.", kind="brief"),
    ]
    priya_chat = [
        bm(priya, "assistant", 28, "Morning, Priya. You have **1 overdue** (Mehta quote) and the TMT stock check is done. Anything to update?", kind="brief"),
        bm(priya, "assistant", 24, "Arjun Mehra gave you: Send Mehta Builders the revised quote for 1,200 cement bags. Due yesterday 1:00 PM.", kind="task",
           buttons=[{"id": f"done:{items['quote']}", "label": "Done"}, {"id": f"delay:{items['quote']}", "label": "Delayed"}, {"id": f"help:{items['quote']}", "label": "Need help"}],
           link_path=f"/app/work?item={items['quote']}"),
    ]
    gupta_chat = [
        bm(gupta, "assistant", 70, "Hi Rajesh, welcome to Mehra Build Supplies on KONNTO. Message me any time — deliveries, updates, questions. I'll keep track.", kind="welcome"),
        bm(gupta, "assistant", 49, f"Arjun Mehra gave you: Deliver 500 bags OPC 53 to the Mehta Baner site. Due {dname(2)} 3:00 PM.", kind="task",
           buttons=[{"id": f"done:{items['gupta_delivery']}", "label": "Done"}, {"id": f"delay:{items['gupta_delivery']}", "label": "Delayed"},
                    {"id": f"help:{items['gupta_delivery']}", "label": "Need help"}], link_path=f"/app/work?item={items['gupta_delivery']}"),
    ]
    await db.brain_messages.insert_many([dict(m) for m in owner_chat + priya_chat + gupta_chat])

    # ---- a little usage history so admin + limits look real ----
    month = ref.strftime("%Y-%m")
    await db.usage.insert_many([{"usage_id": new_id("use"), "org_id": org_id, "feature": "brain_reply", "model": "claude-sonnet-4-6", "input_tokens": 3200,
                                 "output_tokens": 420, "units": 0, "cost_usd": 0.0159, "created_at": iso(ref - timedelta(hours=i * 7)), "month": month} for i in range(14)])

    return {"ok": True, "org_id": org_id, "wiped_previous": wiped, "people": len(people), "items": len(rows), "approvals": len(approvals),
            "rules": len(rules), "facts": len(facts), "documents": len(docs_spec), "threads": 5,
            "logins": {k: {"email": v["email"], "code": DEMO_CODE, "member": {"owner": "Arjun Mehra (Owner)", "priya": "Priya Nair (Operations Lead)",
                                                                              "partner": "Rajesh Gupta (Supplier, external)"}[k]} for k, v in DEMO_USERS.items()} if uids else {}}


if __name__ == "__main__":
    import json
    print(json.dumps(asyncio.run(build_demo()), indent=2))
