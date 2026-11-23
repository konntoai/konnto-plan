"""Evidence-bounded operational diagnostics derived from authorised live records.

These are observable indicators, not a synthetic business-health score. Counts
describe only the records supplied by the caller and must retain that scope.
"""
from datetime import datetime, timedelta, timezone


def _parse_time(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def build_operational_diagnostics(items, approvals=None, *, reference_time=None):
    """Return transparent operational indicators from the supplied authorised records."""
    ref = _parse_time(reference_time) or datetime.now(timezone.utc)
    rows = [row for row in (items or []) if isinstance(row, dict) and not row.get("deleted")]
    open_rows = [row for row in rows if row.get("status", "open") not in ("done", "cancelled")]
    overdue = []
    due_24h = []
    stuck = []
    unresolved_dependencies = []
    status_by_id = {row.get("item_id"): row.get("status", "open") for row in rows if row.get("item_id")}
    for row in open_rows:
        due = _parse_time(row.get("due_at"))
        if due and due < ref:
            overdue.append(row)
        elif due and due <= ref + timedelta(hours=24):
            due_24h.append(row)
        if row.get("status") == "stuck":
            stuck.append(row)
        dependencies = row.get("depends_on") or []
        if any(status_by_id.get(dep) != "done" for dep in dependencies):
            unresolved_dependencies.append(row)
    approval_rows = [row for row in (approvals or []) if isinstance(row, dict) and row.get("status") == "pending"]
    aged_approvals = []
    for row in approval_rows:
        created = _parse_time(row.get("created_at"))
        if created and created < ref - timedelta(days=7):
            aged_approvals.append(row)
    by_assignee = {}
    for row in open_rows:
        label = row.get("assignee_name") or "Unassigned"
        by_assignee[label] = by_assignee.get(label, 0) + 1
    most_loaded = sorted(by_assignee.items(), key=lambda pair: (-pair[1], pair[0]))[:3]
    metrics = {
        "scope": "Only the authorised work items and approval records supplied to this function; not a full accounting or business audit.",
        "open_work_items": len(open_rows),
        "overdue_work_items": len(overdue),
        "due_within_24_hours": len(due_24h),
        "stuck_work_items": len(stuck),
        "work_items_with_unresolved_dependencies": len(unresolved_dependencies),
        "pending_approvals": len(approval_rows),
        "pending_approvals_older_than_7_days": len(aged_approvals),
        "largest_open_workloads": [{"assignee": name, "open_items": count} for name, count in most_loaded],
    }
    evidence = []
    for key, label in (
        ("overdue_work_items", "Overdue work items"),
        ("due_within_24_hours", "Work items due within 24 hours"),
        ("stuck_work_items", "Stuck work items"),
        ("work_items_with_unresolved_dependencies", "Work items with unresolved dependencies"),
        ("pending_approvals_older_than_7_days", "Pending approvals older than 7 days"),
    ):
        if metrics[key]:
            evidence.append({"indicator": key, "label": label, "count": metrics[key], "severity": "attention"})
    return {"metrics": metrics, "attention_indicators": evidence, "is_business_health_score": False}
