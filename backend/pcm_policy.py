"""Pure policy helpers for PCM visibility and issuing authority."""


def can_issue(member: dict) -> bool:
    return bool(member) and (member.get("member_type") == "owner" or (member.get("member_type") == "team" and "team_work" in (member.get("access") or [])))


def can_view(member: dict, instruction: dict) -> bool:
    if not member or not instruction:
        return False
    if member.get("member_type") == "owner" or (member.get("member_type") == "team" and "team_work" in (member.get("access") or [])):
        return True
    member_id = member.get("member_id")
    return member_id in (instruction.get("assignee_id"), instruction.get("issued_by"))


def progress_update_filter(instruction_id: str, org_id: str, record: dict) -> dict:
    """Compare-and-set filter for a progress write based on the version read by caller."""
    return {
        "instruction_id": instruction_id,
        "org_id": org_id,
        "status": {"$nin": ["completed", "cancelled"]},
        "updated_at": record.get("updated_at"),
        "deleted": {"$ne": True},
    }


def progress_update_document(status: str, updated_at: str, event: dict, *,
                             blocker=None, due_at=None, evidence_entry=None) -> dict:
    """Build one atomic Mongo update for PCM status, history, and evidence."""
    fields = {"status": status, "updated_at": updated_at}
    if status == "blocked":
        fields["blocker"] = blocker
    elif status in ("acknowledged", "in_progress"):
        fields["blocker"] = None
    if due_at is not None:
        fields["due_at"] = due_at
    pushes = {"history": event}
    if evidence_entry is not None:
        pushes["evidence"] = evidence_entry
    return {"$set": fields, "$push": pushes}


def work_status_for_pcm(status: str):
    """Map PCM progress into the shared Work status model."""
    return {"in_progress": "in_progress", "blocked": "stuck", "completed": "done", "cancelled": "cancelled"}.get(status)


def work_sync_intent(status: str, *, operation_id: str, due_at=None, reason=None) -> dict:
    """Durable intent embedded in the same atomic write as PCM progress."""
    return {
        "operation_id": operation_id,
        "status": "pending",
        "work_status": work_status_for_pcm(status),
        "due_at": due_at,
        "reason": (reason or "")[:2000],
        "created_at": None,
        "attempts": 0,
    }
