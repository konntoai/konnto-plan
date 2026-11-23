"""Scheduled work (platform cron every 15 min): reminders, chasing late items up the line, morning brief, evening check-in."""
import os
import hmac
import asyncio
import logging
from datetime import timedelta

from fastapi import APIRouter, Request, HTTPException

from core import db, now, iso, parse_iso, org_tz, fmt_local, item_scope_query, item_state, has_scope, is_owner, new_id
from channels import notify, dispatch_notification_jobs
import engine
from pcm_sync import reconcile_pcm_work_sync

logger = logging.getLogger("konnto.cron")
router = APIRouter(prefix="/api")


@router.post("/cron/tick")
async def cron_tick(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    secret = os.environ.get("WEBHOOK_CRON_SECRET", "")
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else ""
    if not secret or not token or not hmac.compare_digest(token, secret):
        raise HTTPException(401, "unauthorized")
    try:
        envelope = await request.json()
    except Exception:
        envelope = {}
    if envelope is not None and not isinstance(envelope, dict):
        raise HTTPException(400, "invalid body")
    run_id = request.headers.get("x-webhook-id") or (envelope or {}).get("run_id") or iso()
    try:
        await db.cron_runs.insert_one({"run_id": run_id, "received_at": iso(), "status": "queued"})
    except Exception as e:
        if "duplicate" in str(e).lower():
            return {"ok": True, "duplicate": True}
        raise HTTPException(500, "could not record run")
    asyncio.create_task(run_tick(run_id))
    return {"ok": True, "run_id": run_id}


async def run_tick(run_id: str):
    stats = {}
    try:
        stats["reminders"] = await send_reminders()
        stats["chased"] = await chase_late()
        stats["pcm_followups"] = await followup_pcm()
        stats["pcm_work_sync"] = await reconcile_pcm_work_sync(database=db)
        stats["notifications"] = await dispatch_notification_jobs(limit=100)
        # Stale action claims are quarantined, not replayed: a previous process
        # may have completed an external side effect before crashing.
        stale_actions = iso(now() - timedelta(minutes=10))
        result = await db.action_operations.update_many(
            {"status": "processing", "created_at": {"$lte": stale_actions}},
            {"$set": {"status": "needs_review", "updated_at": iso(),
                      "review_reason": "processing_lease_expired"}},
        )
        stats["action_operations_needing_review"] = getattr(result, "modified_count", 0)
        stats["briefs"] = await send_briefs()
        await db.cron_runs.update_one({"run_id": run_id}, {"$set": {"status": "done", "stats": stats, "finished_at": iso()}})
    except Exception as e:
        logger.exception("tick failed: %s", e)
        await db.cron_runs.update_one({"run_id": run_id}, {"$set": {"status": "failed", "error": str(e)[:300]}})


async def _org(org_id, cache):
    if org_id not in cache:
        cache[org_id] = await db.orgs.find_one({"org_id": org_id, "deleted": {"$ne": True}}, {"_id": 0})
    return cache[org_id]


async def send_reminders() -> int:
    t = iso()
    cache, n = {}, 0
    due = await db.items.find({"remind_at": {"$ne": None, "$lte": t}, "reminded_at": None, "status": {"$nin": ["done", "cancelled"]},
                               "deleted": {"$ne": True}}, {"_id": 0}).to_list(500)
    for it in due:
        org = await _org(it["org_id"], cache)
        if not org:
            continue
        target_id = it.get("assignee_id") or it.get("created_by")
        target = await db.members.find_one({"member_id": target_id, "org_id": it["org_id"], "status": "active"}, {"_id": 0})
        if not target:
            continue
        extra = f" (due {fmt_local(it['due_at'], org)})" if it.get("due_at") else ""
        who = f" — {it['counterparty']}" if it.get("counterparty") else ""
        text = f"Reminder: {it['title']}{who}{extra}."
        delivery = await notify(target, org=org, kind="reminder", text=text, buttons=engine.TASK_BUTTONS(it["item_id"]), template="konnto_reminder",
                                params=[org["name"], f"{it['title']}{extra}"], email_subject=f"Reminder: {it['title'][:60]}", link_path=f"/app/work?item={it['item_id']}", idempotency_key=f"reminder:{it['item_id']}:{it.get('remind_at') or 'due'}")
        # Mark as reminded only after at least one supported channel confirms delivery.
        delivered = bool(delivery.get("in_app") or delivery.get("whatsapp") == "sent" or delivery.get("email") == "sent")
        if not delivered:
            continue
        await db.items.update_one(
            {"item_id": it["item_id"], "org_id": it["org_id"], "reminded_at": None},
            {"$set": {"reminded_at": t}, "$push": {"history": engine._hist("KONNTO", "Reminder sent")}}
        )
        await engine.apply_behaviour_rules(org, "reminder", it, target)
        n += 1
    return n


async def followup_pcm() -> int:
    """Two-stage, rate-limited PCM follow-up: assignee reminder, then issuer escalation."""
    t = now()
    stamp = iso(t)
    due = iso(t - timedelta(minutes=30))
    rows = await db.pcm_instructions.find({
        "status": {"$in": ["issued", "acknowledged", "in_progress", "blocked"]},
        "due_at": {"$ne": None, "$lte": due},
        "deleted": {"$ne": True},
        "followup_level": {"$lt": 2},
    }, {"_id": 0}).to_list(300)
    sent = 0
    for row in rows:
        level = int(row.get("followup_level") or 0)
        if level == 1 and row.get("last_followup_at"):
            last = parse_iso(row["last_followup_at"])
            if last and last > t - timedelta(hours=24):
                continue
        # Atomic short lease prevents concurrent cron invocations from sending duplicates.
        lease_before = iso(t - timedelta(minutes=10))
        claim = await db.pcm_instructions.find_one_and_update({
            "instruction_id": row["instruction_id"],
            "org_id": row["org_id"],
            "followup_level": level,
            "status": {"$in": ["issued", "acknowledged", "in_progress", "blocked"]},
            "$or": [{"followup_claimed_at": None}, {"followup_claimed_at": {"$lte": lease_before}}, {"followup_claimed_at": {"$exists": False}}],
        }, {"$set": {"followup_claimed_at": stamp}})
        if not claim:
            continue
        try:
            org = await _org(row["org_id"], {})
            if not org:
                await db.pcm_instructions.update_one({"instruction_id": row["instruction_id"]}, {"$unset": {"followup_claimed_at": ""}})
                continue
            if level == 0:
                target_id = row.get("assignee_id")
                kind = "pcm_followup"
                message = f"PCM follow-up: “{row['title']}” is past its deadline. Please update the status or report the blocker in KONNTO PCM."
                event = "assignee_followup"
            else:
                target_id = row.get("issued_by")
                kind = "pcm_escalation"
                message = f"PCM escalation: “{row['title']}” remains unresolved after the follow-up window. Current status: {row.get('status')}. Please review ownership or remove the blocker."
                event = "issuer_escalation"
            target = await db.members.find_one({"member_id": target_id, "org_id": row["org_id"], "status": "active"}, {"_id": 0}) if target_id else None
            if not target and level == 1:
                target = await db.members.find_one({"org_id": row["org_id"], "member_type": "owner", "status": "active"}, {"_id": 0})
            if not target:
                await db.pcm_instructions.update_one({"instruction_id": row["instruction_id"]}, {"$unset": {"followup_claimed_at": ""}})
                continue
            result = await notify(target, org=org, kind=kind, text=message, link_path="/app/pcm",
                                  idempotency_key=f"pcm-followup:{row['instruction_id']}:{level}")
            delivered = bool(result.get("in_app") or result.get("whatsapp") == "sent" or result.get("email") == "sent")
            if not delivered:
                await db.pcm_instructions.update_one({"instruction_id": row["instruction_id"]}, {"$unset": {"followup_claimed_at": ""}})
                continue
            await db.pcm_instructions.update_one(
                {"instruction_id": row["instruction_id"], "org_id": row["org_id"], "followup_level": level},
                {"$set": {"followup_level": level + 1, "last_followup_at": stamp},
                 "$unset": {"followup_claimed_at": ""},
                 "$push": {"history": {"at": stamp, "actor_id": "konnto_pcm", "actor_name": "KONNTO PCM", "event": event}}},
            )
            sent += 1
        except Exception:
            logger.exception("PCM follow-up failed for %s", row.get("instruction_id"))
            await db.pcm_instructions.update_one({"instruction_id": row["instruction_id"]}, {"$unset": {"followup_claimed_at": ""}})
    return sent


async def chase_late() -> int:
    t = now()
    cache, n = {}, 0
    late = await db.items.find({"due_at": {"$ne": None, "$lte": iso(t)}, "status": {"$in": ["open", "in_progress"]}, "kind": {"$in": ["task", "promise"]},
                                "deleted": {"$ne": True}, "chase_level": {"$lt": 3}}, {"_id": 0}).to_list(500)
    for it in late:
        org = await _org(it["org_id"], cache)
        if not org:
            continue
        level = it.get("chase_level") or 0
        last = parse_iso(it.get("last_chased_at"))
        if level > 0 and last and last > t - timedelta(hours=24):
            continue
        assignee = await db.members.find_one({"member_id": it.get("assignee_id"), "status": "active"}, {"_id": 0}) if it.get("assignee_id") else None
        creator = await db.members.find_one({"member_id": it.get("created_by"), "status": "active"}, {"_id": 0})
        due_txt = fmt_local(it["due_at"], org)
        if level == 0:
            target = assignee or creator
            if not target:
                continue
            if target is creator and it.get("counterparty"):
                text = f"{it['counterparty']} promised: {it['title']} (due {due_txt}). Did it happen?"
            else:
                text = f"Late: {it['title']} was due {due_txt}. What's happening?"
            await notify(target, org=org, kind="chase", text=text, buttons=engine.TASK_BUTTONS(it["item_id"]), template="konnto_reminder",
                         params=[org["name"], f"Late: {it['title']} (due {due_txt})"], email_subject=f"Late: {it['title'][:60]}", link_path=f"/app/work?item={it['item_id']}",
                         idempotency_key=f"chase:{it['item_id']}:{level}")
            hist = "Asked for an update (late)"
        else:
            # chase up the line: manager, then owner(s)
            ups = []
            if assignee and assignee.get("manager_id") and level == 1:
                mgr = await db.members.find_one({"member_id": assignee["manager_id"], "status": "active"}, {"_id": 0})
                if mgr and mgr["member_id"] != assignee["member_id"]:
                    ups = [mgr]
            if not ups:
                ups = [o for o in await engine.owners(org["org_id"]) if not assignee or o["member_id"] != assignee["member_id"]]
            if not ups or not assignee:
                await db.items.update_one({"item_id": it["item_id"]}, {"$set": {"chase_level": 3}})
                continue
            reason = it.get("delay_reason") or "no reason given yet"
            for u in ups:
                await notify(u, org=org, kind="escalation", text=f"Still late: {it['title']} ({assignee['name']}, due {due_txt}). Reason: {reason}.",
                             template="konnto_brief", params=[org["name"], f"Still late: {it['title']} ({assignee['name']})"],
                             email_subject=f"Still late: {it['title'][:50]}", link_path=f"/app/work?item={it['item_id']}",
                             idempotency_key=f"escalation:{it['item_id']}:{level}:{u['member_id']}")
            hist = "Chased up the line: " + ", ".join(u["name"] for u in ups)
        await db.items.update_one({"item_id": it["item_id"]}, {"$set": {"chase_level": level + 1, "last_chased_at": iso(t)},
                                                               "$push": {"history": engine._hist("KONNTO", hist)}})
        n += 1
    return n


async def build_brief(org: dict, member: dict) -> str:
    items = await db.items.find(item_scope_query(member), {"_id": 0, "history": 0}).to_list(2000)
    ref = now()
    tz = org_tz(org)
    today = ref.astimezone(tz).date()
    for i in items:
        i["state"] = item_state(i, ref)
    open_ = [i for i in items if i["state"] not in ("done", "cancelled")]
    if not has_scope(member, "team_work"):
        open_ = [i for i in open_ if member["member_id"] in (i.get("assignee_id"), i.get("created_by"))]
    overdue = [i for i in open_ if i["state"] == "overdue"]
    due_today = [i for i in open_ if i.get("due_at") and parse_iso(i["due_at"]).astimezone(tz).date() == today and i["state"] != "overdue"]
    stuck = [i for i in open_ if i["state"] == "stuck"]
    approvals = await db.approvals.count_documents({"org_id": org["org_id"], "status": "pending"}) if has_scope(member, "approve") else 0
    first = member["name"].split()[0]
    if not (overdue or due_today or stuck or approvals):
        return f"Good morning {first}. Nothing due today and nothing late. Tell me anything new and I'll keep track."
    lines = [f"Good morning {first}. Today: {len(due_today)} due, {len(overdue)} late, {len(stuck)} stuck" + (f", {approvals} approvals waiting." if approvals else ".")]
    for i in overdue[:3]:
        lines.append(f"- Late: {i['title']}" + (f" ({i['assignee_name']})" if i.get("assignee_name") and i.get("assignee_id") != member["member_id"] else ""))
    for i in due_today[:3]:
        lines.append(f"- Today: {i['title']}" + (f" ({i['assignee_name']})" if i.get("assignee_name") and i.get("assignee_id") != member["member_id"] else ""))
    for i in stuck[:2]:
        lines.append(f"- Stuck: {i['title']}" + (f" — {i['stuck_reason']}" if i.get("stuck_reason") else ""))
    return "\n".join(lines)


async def _claim_brief(key: str, org_id: str, stamp: str):
    """Claim a daily brief delivery; legacy key-only records remain retryable."""
    token = new_id("briefclaim")
    lease_until = iso(now() + timedelta(minutes=20))
    eligible = {
        "key": key,
        "status": {"$ne": "sent"},
        "$or": [
            {"lease_until": None},
            {"lease_until": {"$exists": False}},
            {"lease_until": {"$lte": stamp}},
        ],
    }
    update = {"$set": {"status": "sending", "claim_token": token, "lease_until": lease_until,
                       "last_attempt_at": stamp, "org_id": org_id},
              "$inc": {"attempts": 1}}
    try:
        claimed = await db.briefs_sent.find_one_and_update(eligible, update)
        if claimed:
            return token
        await db.briefs_sent.insert_one({
            "key": key, "org_id": org_id, "status": "sending", "claim_token": token,
            "lease_until": lease_until, "created_at": stamp, "last_attempt_at": stamp, "attempts": 1,
        })
        return token
    except Exception as exc:
        # A concurrent first insert can win the unique-key race. Try to claim its
        # now-existing retryable record; otherwise another worker owns it or it is sent.
        if "duplicate" not in str(exc).lower():
            logger.exception("Could not claim daily brief %s", key)
            return None
        try:
            claimed = await db.briefs_sent.find_one_and_update(eligible, update)
            return token if claimed else None
        except Exception:
            logger.exception("Could not reclaim daily brief %s", key)
            return None


async def send_briefs() -> int:
    n = 0
    orgs = await db.orgs.find({"deleted": {"$ne": True}, "briefs.enabled": {"$ne": False}}, {"_id": 0}).to_list(5000)
    t = now()
    for org in orgs:
        local = t.astimezone(org_tz(org))
        b = org.get("briefs") or {}
        for kind, hour in (("brief", int(b.get("morning_hour", 8))), ("evening", int(b.get("evening_hour", 19)))):
            if not (hour <= local.hour < hour + 2):
                continue
            day = local.strftime("%Y-%m-%d")
            members = await db.members.find({"org_id": org["org_id"], "status": "active"}, {"_id": 0}).to_list(500)
            for m in members:
                key = f"{m['member_id']}:{kind}:{day}"
                stamp = iso(t)
                claim_token = await _claim_brief(key, org["org_id"], stamp)
                if not claim_token:
                    continue
                try:
                    if kind == "brief":
                        message = await build_brief(org, m)
                        result = await notify(m, org=org, kind="brief", text=message, template="konnto_brief",
                                              params=[org["name"], message.replace("\n", " ")[:600]],
                                              email_subject=f"Your morning brief — {org['name']}", link_path="/app/dashboard",
                                              email_fallback=is_owner(m))
                    else:
                        done_today = await db.items.count_documents({
                            "org_id": org["org_id"], "status": "done",
                            "done_at": {"$gte": iso(t - timedelta(hours=14))},
                            "$or": [{"assignee_id": m["member_id"]}, {"created_by": m["member_id"]}],
                        })
                        message = f"Anything to remember from today, {m['name'].split()[0]}? Just reply with it." + (f" ({done_today} things done today.)" if done_today else "")
                        result = await notify(m, org=org, kind="evening", text=message, template="konnto_brief",
                                              params=[org["name"], message], email_fallback=False)
                    delivered = bool(result.get("in_app") or result.get("whatsapp") == "sent" or result.get("email") == "sent")
                    if delivered:
                        await db.briefs_sent.update_one(
                            {"key": key, "claim_token": claim_token},
                            {"$set": {"status": "sent", "sent_at": iso(), "delivery": result},
                             "$unset": {"claim_token": "", "lease_until": ""}},
                        )
                        n += 1
                    else:
                        await db.briefs_sent.update_one(
                            {"key": key, "claim_token": claim_token},
                            {"$set": {"status": "failed", "last_error": "No delivery channel confirmed"},
                             "$unset": {"claim_token": "", "lease_until": ""}},
                        )
                except Exception as exc:
                    logger.exception("Daily brief delivery failed for %s", key)
                    await db.briefs_sent.update_one(
                        {"key": key, "claim_token": claim_token},
                        {"$set": {"status": "failed", "last_error": str(exc)[:300]},
                         "$unset": {"claim_token": "", "lease_until": ""}},
                    )
    return n
