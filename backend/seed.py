"""Demo seed: populate a fresh org with sample projects, tasks, approvals, team members and a direct thread."""
from datetime import timedelta
from core import db, now, iso, new_id, short_code, SCOPES, norm_phone, fact_category
import engine

SAMPLE_PEOPLE = [
    {"name": "Priya Nair", "job": "Operations Lead", "member_type": "team", "phone": "+919000000001", "email": None},
    {"name": "Ramesh Kumar", "job": "Site Supervisor", "member_type": "team", "phone": "+919000000002", "email": None},
    {"name": "Gupta Cement", "job": "Supplier", "member_type": "partner", "phone": None, "email": None},
]


async def seed_demo_org(org: dict, owner_member: dict) -> dict:
    """Idempotent: only seeds if the org has no items yet."""
    existing_items = await db.items.count_documents({"org_id": org["org_id"]})
    if existing_items:
        return {"seeded": False, "reason": "already has items"}

    # Make sure industry + description get something friendly so dashboards look lived-in.
    if not org.get("industry"):
        await db.orgs.update_one({"org_id": org["org_id"]},
                                 {"$set": {"industry": org.get("industry") or "Retail & wholesale",
                                           "description": org.get("description") or "A small team using KONNTO AI to keep the day moving.",
                                           "profile_learned": True}})
        org["industry"] = "Retail & wholesale"
        org["profile_learned"] = True

    # ---- People ----
    created_people = []
    for p in SAMPLE_PEOPLE:
        existing = await db.members.find_one({"org_id": org["org_id"], "name": p["name"]}, {"_id": 0})
        if existing:
            created_people.append(existing)
            continue
        m = {
            "member_id": new_id("mem"),
            "org_id": org["org_id"],
            "user_id": None,
            "name": p["name"],
            "job": p["job"],
            "member_type": p["member_type"],
            "phone": norm_phone(p["phone"]) if p["phone"] else None,
            "email": p["email"],
            "access": ["own_work", "team_work"] if p["member_type"] == "team" else ["own_work"],
            "access_reason": "Sample access set for the demo.",
            "status": "active",
            "wa_opt_in": False,
            "invited_by": owner_member["member_id"],
            "invited_by_name": owner_member["name"],
            "manager_id": owner_member["member_id"],
            "joined_via": "demo_seed",
            "created_at": iso(),
            "joined_at": iso(),
        }
        await db.members.insert_one(dict(m))
        m.pop("_id", None)
        created_people.append(m)

    priya, ramesh, gupta = created_people[0], created_people[1], created_people[2]

    # ---- Project ----
    proj_id = await engine.ensure_project(org["org_id"], "This week", owner_member)

    # ---- Items with varied states ----
    ref = now()
    ccy = org.get("currency") or "INR"
    items_to_create = [
        # Overdue task assigned to Priya
        {"kind": "task", "title": "Send Mehta Builders the quote for cement",
         "details": "They asked on Monday. Priority — they have a deadline on Friday.",
         "assignee_id": priya["member_id"], "assignee_name": priya["name"],
         "due_at": iso(ref - timedelta(days=1, hours=2)),
         "status": "open", "project_id": proj_id, "chase_level": 1},
        # Due today task assigned to owner
        {"kind": "task", "title": "Review the new price list before sending",
         "details": "Updated wholesale rates for Q3. Make sure the margin table is correct.",
         "assignee_id": owner_member["member_id"], "assignee_name": owner_member["name"],
         "due_at": iso(ref + timedelta(hours=3)),
         "status": "open", "project_id": proj_id},
        # Due tomorrow task
        {"kind": "task", "title": "Call Ramesh about the warehouse inventory count",
         "details": "Monthly stock check — should take 15 minutes.",
         "assignee_id": ramesh["member_id"], "assignee_name": ramesh["name"],
         "due_at": iso(ref + timedelta(days=1, hours=5)),
         "status": "open", "project_id": proj_id},
        # Promise from supplier
        {"kind": "promise", "title": "Gupta Cement — 200 bags delivery",
         "details": "Promised on the call Monday. Delivery slot: afternoon.",
         "assignee_id": owner_member["member_id"], "assignee_name": owner_member["name"],
         "counterparty": "Gupta Cement",
         "due_at": iso(ref + timedelta(days=2, hours=4)),
         "remind_at": iso(ref + timedelta(days=1, hours=12)),
         "status": "open", "amount": 48000, "currency": ccy, "project_id": proj_id},
        # Stuck task
        {"kind": "task", "title": "Fix the leaking tap at the shop",
         "details": "Plumber said tomorrow. Might need new fittings.",
         "assignee_id": ramesh["member_id"], "assignee_name": ramesh["name"],
         "due_at": iso(ref - timedelta(days=3)),
         "status": "stuck", "stuck_reason": "Waiting for the plumber to confirm the time."},
        # Reminder for owner
        {"kind": "reminder", "title": "Pay the electricity bill before 25th",
         "assignee_id": owner_member["member_id"], "assignee_name": owner_member["name"],
         "due_at": iso(ref + timedelta(days=3, hours=12)),
         "remind_at": iso(ref + timedelta(days=2, hours=10)),
         "status": "open", "amount": 4200, "currency": ccy},
        # A done item (last week)
        {"kind": "task", "title": "Order new boxes from the packaging guy",
         "assignee_id": owner_member["member_id"], "assignee_name": owner_member["name"],
         "status": "done",
         "due_at": iso(ref - timedelta(days=5)),
         "done_at": iso(ref - timedelta(days=4))},
        # Personal note (private)
        {"kind": "note", "title": "Idea: run a monsoon sale — 10% off cement + steel",
         "assignee_id": owner_member["member_id"], "assignee_name": owner_member["name"],
         "status": "open", "visibility": "private"},
    ]

    for data in items_to_create:
        item = {
            "item_id": new_id("itm"),
            "org_id": org["org_id"],
            "kind": data["kind"],
            "title": data["title"],
            "details": data.get("details", ""),
            "status": data.get("status", "open"),
            "assignee_id": data.get("assignee_id"),
            "assignee_name": data.get("assignee_name"),
            "created_by": owner_member["member_id"],
            "created_by_name": owner_member["name"],
            "counterparty": data.get("counterparty"),
            "due_at": data.get("due_at"),
            "remind_at": data.get("remind_at"),
            "reminded_at": None,
            "amount": data.get("amount"),
            "currency": data.get("currency"),
            "depends_on": [],
            "project_id": data.get("project_id") or proj_id,
            "is_request": False,
            "visibility": data.get("visibility", "org"),
            "watchers": [owner_member["member_id"]],
            "source": {"type": "demo_seed"},
            "chase_level": data.get("chase_level", 0),
            "last_chased_at": None,
            "delay_reason": None,
            "stuck_reason": data.get("stuck_reason"),
            "history": [engine._hist(owner_member["name"], "Added as part of your demo workspace")],
            "created_at": iso(ref - timedelta(days=2)),
            "updated_at": iso(),
            "done_at": data.get("done_at"),
        }
        await db.items.insert_one(dict(item))

    # ---- Pending approvals (varied amounts + requesters so K-BRAIN can prioritise) ----
    approvals_to_create = [
        {"kind": "payment", "title": "Advance to Gupta Cement for the Mehta Builders order",
         "details": "Gupta wants 50% upfront to lock this week's rate before the price rise on Monday. Mehta's order depends on it.",
         "by": priya, "amount": 42000, "hours": 20},
        {"kind": "expense", "title": "Buy a replacement drill for the shop",
         "details": "The old one broke yesterday. This model is well reviewed and still within last quarter's budget.",
         "by": ramesh, "amount": 8500, "hours": 4},
        {"kind": "payment", "title": "Refund for damaged bags — Sharma Hardware",
         "details": "6 bags arrived torn. Customer is waiting on a call-back before they place next month's order.",
         "by": priya, "amount": 6800, "hours": 30},
    ]
    for a in approvals_to_create:
        await db.approvals.insert_one({
            "approval_id": new_id("apr"), "org_id": org["org_id"], "kind": a["kind"], "title": a["title"], "details": a["details"],
            "requested_by": a["by"]["member_id"], "requested_by_name": a["by"]["name"], "amount": a["amount"], "currency": ccy,
            "status": "pending", "source": {"type": "demo_seed"}, "created_at": iso(ref - timedelta(hours=a["hours"])),
        })

    # ---- A direct thread with Priya ----
    thread = await engine.get_or_create_direct_thread(org["org_id"], owner_member, priya)
    sample_messages = [
        {"sender": priya, "text": "Hi — Mehta Builders asked when they'll get the quote. I said by EOD. Is that okay?"},
        {"sender": owner_member, "text": "Yes, let's send it today. I'll review after lunch and share the final numbers."},
        {"sender": priya, "text": "Got it. I'll have the draft ready by 2pm."},
    ]
    for i, m in enumerate(sample_messages):
        await db.thread_messages.insert_one({
            "msg_id": new_id("tm"),
            "thread_id": thread["thread_id"],
            "org_id": org["org_id"],
            "sender_id": m["sender"]["member_id"],
            "sender_name": m["sender"]["name"],
            "kind": "text",
            "text": m["text"],
            "item_id": None,
            "cards": [],
            "deliveries": [],
            "created_at": iso(ref - timedelta(hours=2 - i * 0.1)),
        })
    await db.threads.update_one({"thread_id": thread["thread_id"]},
                                {"$set": {"last_message_at": iso(ref - timedelta(hours=2)),
                                          "last_message_preview": f"Priya: {sample_messages[-1]['text'][:80]}"}})

    # ---- A few knowledge facts ----
    for text in [
        "Our wholesale margin on cement is usually 8–12%.",
        "Deliveries from Gupta Cement always come in the afternoon slot.",
        "The warehouse is closed every Sunday.",
        "Cash on hand is about 24.1 lakh this week (owner's estimate, demo figure).",
    ]:
        await db.knowledge.insert_one({
            "fact_id": new_id("fct"),
            "org_id": org["org_id"],
            "text": text,
            "category": fact_category(text),
            "confirmed": True,
            "source": "demo_seed",
            "created_by": owner_member["member_id"],
            "created_by_name": owner_member["name"],
            "created_at": iso(),
        })

    # ---- A KONNTO brief in brain_messages so the Dashboard has a "This morning" card ----
    brief_lines = [
        f"Good morning. Here's what matters today for {org['name']}:",
        "• 1 task is overdue — Mehta Builders quote. Who's picking it up?",
        "• 1 task is due today — Review the new price list.",
        "• 3 approvals are waiting — the Gupta Cement advance is the time-sensitive one.",
        "Reply with anything you want to talk through — I'll keep up.",
    ]
    await db.brain_messages.insert_one({
        "msg_id": new_id("bm"),
        "org_id": org["org_id"],
        "member_id": owner_member["member_id"],
        "role": "assistant",
        "kind": "brief",
        "text": "\n".join(brief_lines),
        "cards": [],
        "citations": [],
        "channel": "app",
        "created_at": iso(ref - timedelta(hours=8)),
    })

    return {"seeded": True, "people": len(created_people), "items": len(items_to_create),
            "approvals": len(approvals_to_create), "threads": 1, "project_id": proj_id}
