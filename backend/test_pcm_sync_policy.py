from pcm_policy import work_status_for_pcm, work_sync_intent


def test_pcm_status_mapping_is_explicit():
    assert work_status_for_pcm("in_progress") == "in_progress"
    assert work_status_for_pcm("blocked") == "stuck"
    assert work_status_for_pcm("completed") == "done"
    assert work_status_for_pcm("cancelled") == "cancelled"
    assert work_status_for_pcm("acknowledged") is None


def test_work_sync_intent_has_stable_id_and_retry_state():
    intent = work_sync_intent(
        "blocked", operation_id="sync_123",
        due_at="2026-11-25T10:00:00Z", reason="Waiting for material",
    )
    assert intent["operation_id"] == "sync_123"
    assert intent["status"] == "pending"
    assert intent["work_status"] == "stuck"
    assert intent["due_at"] == "2026-11-25T10:00:00Z"
    assert intent["attempts"] == 0
