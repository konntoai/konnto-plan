from kbrain_action_policy import (
    button_claim_query,
    button_claim_update,
    button_completion_update,
)


def test_button_claim_is_scoped_to_message_member_and_valid_button():
    query = button_claim_query("msg-1", "member-2", "done:item-3")
    assert query["msg_id"] == "msg-1"
    assert query["member_id"] == "member-2"
    assert query["buttons.id"] == "done:item-3"
    assert query["$or"] == [
        {"buttons_used": None},
        {"buttons_used": {"$exists": False}},
    ]


def test_button_claim_marks_processing_before_execution():
    update = button_claim_update("done:item-3", "Done", "2026-11-24T10:00:00Z")
    assert update["$set"]["buttons_used"] == "done:item-3"
    assert update["$set"]["button_action_status"] == "processing"
    assert update["$set"]["buttons_used_label"] == "Done"


def test_button_completion_persists_result_for_reconciliation():
    update = button_completion_update("Marked done", "2026-11-24T10:01:00Z")
    assert update["$set"] == {
        "button_action_status": "completed",
        "button_action_result": "Marked done",
        "button_action_completed_at": "2026-11-24T10:01:00Z",
    }
