"""Durable, idempotent synchronization from PCM instructions to shared Work items."""
from datetime import timedelta

from core import db, iso, now
from pcm_policy import work_status_for_pcm


async def reconcile_pcm_work_sync(limit: int = 100) -> dict:
    """Apply pending PCM sync intents; safe to replay after a worker crash.

    The operation id is persisted on the Work item in the same atomic update
    as its status/history. A retry after that update becomes a no-op.
    """
    stamp = iso()
    stale = iso(now() - timedelta(minutes=10))
    rows = await db.pcm_instructions.find({
        "work_sync.status": {"$in": ["pending", "processing"]},
        "deleted": {"$ne": True},
    }, {"_id": 0}).sort("updated_at", 1).to_list(limit)
    stats = {"claimed": 0, "synced": 0, "missing_items": 0, "errors": 0}
    for row in rows:
        intent = row.get("work_sync") or {}
        op_id = intent.get("operation_id")
        if not op_id:
            continue
        claim = await db.pcm_instructions.find_one_and_update({
            "instruction_id": row["instruction_id"],
            "org_id": row["org_id"],
            "work_sync.operation_id": op_id,
            "$or": [
                {"work_sync.status": "pending"},
                {"work_sync.status": "processing", "work_sync.claimed_at": {"$lte": stale}},
                {"work_sync.status": "processing", "work_sync.claimed_at": {"$exists": False}},
            ],
        }, {"$set": {"work_sync.status": "processing", "work_sync.claimed_at": stamp},
            "$inc": {"work_sync.attempts": 1}}, {"_id": 0})
        if not claim:
            continue
        stats["claimed"] += 1
        try:
            intent = claim.get("work_sync") or {}
            item_id = claim.get("item_id")
            if not item_id:
                stats["missing_items"] += 1
                await db.pcm_instructions.update_one(
                    {"instruction_id": claim["instruction_id"], "org_id": claim["org_id"], "work_sync.operation_id": op_id},
                    {"$set": {"work_sync.status": "failed", "work_sync.last_error": "PCM instruction has no linked work item"},
                     "$unset": {"work_sync.claimed_at": ""}},
                )
                continue
            update = {"updated_at": stamp, "pcm_sync_operation_id": op_id}
            work_status = intent.get("work_status")
            if work_status:
                update["status"] = work_status
                if work_status == "done":
                    update["done_at"] = stamp
                elif work_status == "cancelled":
                    update["done_at"] = None
                if work_status == "stuck":
                    update["stuck_reason"] = intent.get("reason") or "Blocked through PCM"
            if intent.get("due_at") is not None:
                update["due_at"] = intent["due_at"]
            changed = await db.items.update_one(
                {"item_id": item_id, "org_id": claim["org_id"], "pcm_sync_operation_id": {"$ne": op_id}},
                {"$set": update, "$push": {"history": {
                    "at": stamp, "by": "KONNTO PCM",
                    "text": f"PCM synchronized status: {work_status}" if work_status else "PCM synchronized due date",
                    "operation_id": op_id,
                }}},
            )
            if not changed.matched_count:
                # Either the item was already synchronized by this operation or it is missing.
                existing = await db.items.find_one(
                    {"item_id": item_id, "org_id": claim["org_id"]},
                    {"_id": 0, "pcm_sync_operation_id": 1},
                )
                if not existing:
                    stats["missing_items"] += 1
                    await db.pcm_instructions.update_one(
                        {"instruction_id": claim["instruction_id"], "org_id": claim["org_id"], "work_sync.operation_id": op_id},
                        {"$set": {"work_sync.status": "failed", "work_sync.last_error": "Linked work item not found"},
                         "$unset": {"work_sync.claimed_at": ""}},
                    )
                    continue
            await db.pcm_instructions.update_one(
                {"instruction_id": claim["instruction_id"], "org_id": claim["org_id"], "work_sync.operation_id": op_id},
                {"$set": {"work_sync.status": "done", "work_sync.completed_at": iso()},
                 "$unset": {"work_sync.claimed_at": "", "work_sync.last_error": ""}},
            )
            stats["synced"] += 1
        except Exception as exc:
            stats["errors"] += 1
            await db.pcm_instructions.update_one(
                {"instruction_id": claim["instruction_id"], "org_id": claim["org_id"], "work_sync.operation_id": op_id},
                {"$set": {"work_sync.status": "pending", "work_sync.last_error": str(exc)[:300]},
                 "$unset": {"work_sync.claimed_at": ""}},
            )
    return stats
