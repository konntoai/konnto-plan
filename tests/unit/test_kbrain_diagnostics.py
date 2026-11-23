from datetime import datetime, timezone

from backend.kbrain_diagnostics import build_operational_diagnostics


def test_diagnostics_count_overdue_stuck_and_dependencies_without_score():
    result = build_operational_diagnostics(
        [
            {"item_id": "a", "status": "open", "due_at": "2026-11-20T00:00:00Z", "assignee_name": "A"},
            {"item_id": "b", "status": "stuck", "depends_on": ["a"], "assignee_name": "B"},
            {"item_id": "c", "status": "done"},
        ],
        reference_time="2026-11-24T00:00:00Z",
    )
    metrics = result["metrics"]
    assert metrics["open_work_items"] == 2
    assert metrics["overdue_work_items"] == 1
    assert metrics["stuck_work_items"] == 1
    assert metrics["work_items_with_unresolved_dependencies"] == 1
    assert result["is_business_health_score"] is False


def test_diagnostics_report_aged_approvals_and_explain_scope():
    result = build_operational_diagnostics(
        [],
        [{"status": "pending", "created_at": "2026-11-10T00:00:00Z"}],
        reference_time=datetime(2026, 11, 24, tzinfo=timezone.utc),
    )
    assert result["metrics"]["pending_approvals_older_than_7_days"] == 1
    assert "not a full accounting" in result["metrics"]["scope"]


def test_diagnostics_ignore_completed_and_cancelled_items_and_unknown_dates():
    result = build_operational_diagnostics(
        [
            {"item_id": "done", "status": "done", "due_at": "2020-01-01T00:00:00Z"},
            {"item_id": "cancel", "status": "cancelled", "due_at": "2020-01-01T00:00:00Z"},
            {"item_id": "unknown", "status": "open", "due_at": "not-a-date"},
        ],
        reference_time="2026-11-24T00:00:00Z",
    )
    assert result["metrics"]["open_work_items"] == 1
    assert result["metrics"]["overdue_work_items"] == 0
