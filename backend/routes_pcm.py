"""KONNTO PCM: permission-enforced business coordination over the shared work engine.

PCM instructions are orchestration records linked to ordinary work items. They do
not create a second task engine and do not grant authority to move money or bind
the organisation.
"""
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, iso, now, new_id, parse_iso, get_ctx, has_scope, is_owner, audit
from channels import notify
import engine
from pcm_policy import can_issue as policy_can_issue, can_view as policy_can_view

router = APIRouter(prefix="/api/pcm")


def _can_issue(member: dict) -> bool:
    return policy_can_issue(member)


def _can_view(member: dict, instruction: dict) -> bool:
    return policy_can_view(member, instruction)


def _present(record: dict, member: dict) -> dict:
    out = dict(record)
    if not has_scope(member, "money"):
        out.pop("amount", None)
    return out


async def _get_instruction(member: dict, instruction_id: str) -> dict:
    record = await db.pcm_instructions.find_one(
        {"instruction_id": instruction_id, "org_id": member["org_id"], "deleted": {"$ne": True}},
        {"_id": 0},
    )
    if not record or not _can_view(member, record):
        raise HTTPException(404, "Instruction not found")
    return record


class InstructionIn(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    details: str = Field(default="", max_length=3000)
    assignee_id: str
    due_at: Optional[str] = None
    priority: str = "normal"
    department: str = "operations"
    objective: Optional[str] = None
    authority_class: str = "delegated"


class ProgressIn(BaseModel):
    status: str
    note: Optional[str] = Field(default=None, max_length=2000)
    evidence: Optional[str] = Field(default=None, max_length=2000)
    new_due_at: Optional[str] = None


@router.get("/overview")
async def pcm_overview(ctx: dict = Depends(get_ctx)):
    member, org = ctx["member"], ctx["org"]
    q = {"org_id": org["org_id"], "deleted": {"$ne": True}}
    if not is_owner(member) and not has_scope(member, "team_work"):
        q["$or"] = [{"assignee_id": member["member_id"]}, {"issued_by": member["member_id"]}]
    rows = await db.pcm_instructions.find(q, {"_id": 0}).sort("updated_at", -1).to_list(300)
    counts = {key: sum(1 for row in rows if row.get("status") == key)
              for key in ("issued", "acknowledged", "in_progress", "blocked", "completed", "cancelled")}
    return {
        "instructions": [_present(row, member) for row in rows],
        "counts": counts,
        "can_issue": _can_issue(member),
        "is_owner": is_owner(member),
        "org": {"name": org.get("name"), "timezone": org.get("timezone"), "currency": org.get("currency")},
    }


@router.post("/instructions")
async def create_instruction(body: InstructionIn, ctx: dict = Depends(get_ctx)):
    member, org = ctx["member"], ctx["org"]
    if not _can_issue(member):
        raise HTTPException(403, "You do not have authority to issue team instructions.")
    if body.authority_class not in ("routine", "delegated"):
        raise HTTPException(403, "Reserved decisions require a separate owner approval and cannot be issued as routine work.")
    if body.priority not in ("low", "normal", "high", "urgent"):
        raise HTTPException(400, "Invalid priority.")
    if body.department not in ("sales", "marketing", "finance", "operations", "people", "technology", "leadership", "growth", "other"):
        raise HTTPException(400, "Invalid department.")
    target = await db.members.find_one({
        "member_id": body.assignee_id, "org_id": org["org_id"], "status": "active", "member_type": "team"
    }, {"_id": 0})
    if not target:
        raise HTTPException(404, "Choose an active internal team member.")
    if not is_owner(member) and not has_scope(member, "manage_team"):
        if target.get("manager_id") != member["member_id"] and target.get("member_id") != member["member_id"]:
            raise HTTPException(403, "Managers may issue instructions only within their reporting line.")
    parsed_due = parse_iso(body.due_at) if body.due_at else None
    if body.due_at and not parsed_due:
        raise HTTPException(400, "Invalid due date.")
    due = iso(parsed_due) if parsed_due else None
    # Use the existing work engine; PCM is an orchestration layer, not a duplicate task engine.
    item = await engine.create_item(org, member, {
        "kind": "task", "title": body.title, "details": body.details,
        "assignee_id": target["member_id"], "due_at_utc": due,
        "is_request": True, "private": False,
    }, source={"type": "pcm"})
    record = {
        "instruction_id": new_id("pcm"), "org_id": org["org_id"],
        "title": body.title.strip(), "details": body.details.strip(),
        "objective": (body.objective or "").strip()[:500] or None,
        "department": body.department, "priority": body.priority,
        "authority_class": body.authority_class, "status": "issued",
        "item_id": item["item_id"], "issued_by": member["member_id"],
        "issued_by_name": member["name"], "assignee_id": target["member_id"],
        "assignee_name": target["name"], "due_at": due,
        "created_at": iso(), "updated_at": iso(), "history": [{
            "at": iso(), "actor_id": member["member_id"], "actor_name": member["name"],
            "event": "issued", "note": "Instruction issued through KONNTO PCM."
        }], "evidence": [], "deleted": False,
    }
    await db.pcm_instructions.insert_one(dict(record))
    await audit(org["org_id"], member["member_id"], "pcm_instruction_issued", {
        "instruction_id": record["instruction_id"], "item_id": item["item_id"], "assignee_id": target["member_id"]
    })
    return _present(record, member)


@router.post("/instructions/{instruction_id}/progress")
async def update_progress(instruction_id: str, body: ProgressIn, ctx: dict = Depends(get_ctx)):
    member, org = ctx["member"], ctx["org"]
    record = await _get_instruction(member, instruction_id)
    if member["member_id"] not in (record["assignee_id"], record["issued_by"]) and not is_owner(member):
        raise HTTPException(403, "Only the assignee, issuer or owner can update this instruction.")
    if record.get("status") in ("completed", "cancelled"):
        raise HTTPException(409, "This instruction is closed and cannot be changed.")
    if body.status not in ("acknowledged", "in_progress", "blocked", "completed"):
        raise HTTPException(400, "Unsupported progress state.")
    if body.status == "blocked" and not (body.note or "").strip():
        raise HTTPException(400, "Explain what is blocking the work.")
    if body.status == "completed" and not (body.evidence or body.note or "").strip():
        raise HTTPException(400, "Add a completion note or evidence before marking this complete.")
    event = {
        "at": iso(), "actor_id": member["member_id"], "actor_name": member["name"],
        "event": body.status, "note": (body.note or "").strip()[:2000],
    }
    upd = {"status": body.status, "updated_at": iso()}
    if body.status == "blocked":
        upd["blocker"] = (body.note or "").strip()[:2000]
    elif body.status in ("acknowledged", "in_progress"):
        upd["blocker"] = None
    if body.new_due_at:
        due = iso(parse_iso(body.new_due_at))
        if not due:
            raise HTTPException(400, "Invalid revised due date.")
        upd["due_at"] = due
    if body.evidence:
        event["evidence"] = body.evidence.strip()[:2000]
        await db.pcm_instructions.update_one(
            {"instruction_id": instruction_id, "org_id": org["org_id"]},
            {"$push": {"evidence": {"at": iso(), "by": member["name"], "text": body.evidence.strip()[:2000]}}},
        )
    await db.pcm_instructions.update_one(
        {"instruction_id": instruction_id, "org_id": org["org_id"]},
        {"$set": upd, "$push": {"history": event}},
    )
    # Keep the underlying Work item in sync with verified progress.
    if record.get("item_id"):
        item = await db.items.find_one({"item_id": record["item_id"], "org_id": org["org_id"]}, {"_id": 0})
        if item:
            mapped = {"in_progress": "in_progress", "blocked": "stuck", "completed": "done"}
            if body.status in mapped:
                await engine.set_item_status(org, member, item, mapped[body.status], body.note, via="pcm")
    if body.status == "blocked" or body.status == "completed":
        recipient_id = record["issued_by"] if member["member_id"] != record["issued_by"] else None
        recipient = await db.members.find_one({"member_id": recipient_id, "org_id": org["org_id"], "status": "active"}, {"_id": 0}) if recipient_id else None
        if not recipient and member["member_id"] == record["issued_by"]:
            recipient = await db.members.find_one({"org_id": org["org_id"], "member_type": "owner", "status": "active"}, {"_id": 0})
        if recipient and recipient["member_id"] != member["member_id"]:
            label = "blocked" if body.status == "blocked" else "completed"
            await notify(recipient, org=org, kind="pcm_update",
                         text=f"{member['name']} marked “{record['title']}” {label}. {body.note or body.evidence or ''}".strip(),
                         link_path="/app/pcm")
    await audit(org["org_id"], member["member_id"], "pcm_progress_updated", {
        "instruction_id": instruction_id, "status": body.status
    })
    fresh = await db.pcm_instructions.find_one({"instruction_id": instruction_id, "org_id": org["org_id"]}, {"_id": 0})
    return _present(fresh, member)


@router.post("/instructions/{instruction_id}/cancel")
async def cancel_instruction(instruction_id: str, ctx: dict = Depends(get_ctx)):
    member, org = ctx["member"], ctx["org"]
    record = await _get_instruction(member, instruction_id)
    if not is_owner(member) and member["member_id"] != record["issued_by"]:
        raise HTTPException(403, "Only the issuer or owner can cancel this instruction.")
    if record["status"] in ("completed", "cancelled"):
        raise HTTPException(409, "This instruction is already closed.")
    await db.pcm_instructions.update_one(
        {"instruction_id": instruction_id, "org_id": org["org_id"]},
        {"$set": {"status": "cancelled", "updated_at": iso()},
         "$push": {"history": {"at": iso(), "actor_id": member["member_id"], "actor_name": member["name"], "event": "cancelled"}}},
    )
    if record.get("item_id"):
        await db.items.update_one({"item_id": record["item_id"], "org_id": org["org_id"], "status": {"$nin": ["done", "cancelled"]}},
                                  {"$set": {"status": "cancelled", "updated_at": iso()}})
    await audit(org["org_id"], member["member_id"], "pcm_instruction_cancelled", {"instruction_id": instruction_id})
    return {"ok": True}
