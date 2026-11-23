"""Durable claim policy for card actions. A claimed action is never replayed blindly."""


def card_operation_id(org_id: str, member_id: str, card_id: str, op: str, state: str, edits_key: str = "") -> str:
    return ":".join(("card-action", org_id, member_id, card_id, op, state, edits_key))


def card_operation_record(operation_id: str, org_id: str, member_id: str, card_id: str, op: str, timestamp: str) -> dict:
    return {
        "_id": operation_id,
        "org_id": org_id,
        "member_id": member_id,
        "card_id": card_id,
        "operation": op,
        "status": "processing",
        "attempts": 1,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def card_operation_outcome(status: str, result=None) -> dict:
    if status == "completed":
        return result if isinstance(result, dict) else {"result": result}
    if status == "needs_review":
        return {"error": "action_needs_review", "message": "This action may have partially completed. Review its outcome before trying again."}
    return {"error": "action_in_progress", "message": "This action is already being processed."}
