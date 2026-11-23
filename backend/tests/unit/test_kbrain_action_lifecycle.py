from kbrain_action_lifecycle import (
    card_operation_id,
    card_operation_record,
    card_operation_outcome,
)


def test_card_operation_identity_is_stable_for_same_transition():
    first = card_operation_id("org", "member", "card", "confirm", "draft", "edit-hash")
    second = card_operation_id("org", "member", "card", "confirm", "draft", "edit-hash")
    assert first == second
    assert first != card_operation_id("org", "member", "card", "confirm", "saved", "edit-hash")
    assert first != card_operation_id("org", "member", "card", "confirm", "draft", "other-edit")


def test_card_operation_record_starts_in_processing_state():
    record = card_operation_record("op-1", "org", "member", "card", "confirm", "2026-11-24T00:00:00Z")
    assert record["_id"] == "op-1"
    assert record["status"] == "processing"
    assert record["attempts"] == 1


def test_completed_operation_replays_stored_result_not_side_effect():
    result = {"card": {"card_id": "card", "status": "saved"}, "item": {"item_id": "item"}}
    assert card_operation_outcome("completed", result) == result


def test_interrupted_operation_is_quarantined_for_review():
    outcome = card_operation_outcome("needs_review")
    assert outcome["error"] == "action_needs_review"
    assert "Review its outcome" in outcome["message"]
