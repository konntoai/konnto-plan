"""Pure policy helpers for idempotent K-BRAIN action claims."""


def button_claim_query(msg_id: str, member_id: str, action_id: str) -> dict:
    """Match only a valid, unused button so one concurrent request wins."""
    return {
        "msg_id": msg_id,
        "member_id": member_id,
        "buttons.id": action_id,
        "$or": [
            {"buttons_used": None},
            {"buttons_used": {"$exists": False}},
        ],
    }


def button_claim_update(action_id: str, label: str, timestamp: str) -> dict:
    return {
        "$set": {
            "buttons_used": action_id,
            "buttons_used_label": label,
            "buttons_used_at": timestamp,
            "button_action_status": "processing",
        }
    }


def button_completion_update(result: str, timestamp: str) -> dict:
    return {
        "$set": {
            "button_action_status": "completed",
            "button_action_result": result,
            "button_action_completed_at": timestamp,
        }
    }
