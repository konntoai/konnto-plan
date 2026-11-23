import asyncio
from datetime import datetime, timezone, timedelta

import pcm_sync


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, *_args):
        return self

    async def to_list(self, limit):
        return self.rows[:limit]


class FakeInstructions:
    def __init__(self, row):
        self.row = row

    def find(self, query, _projection):
        assert query["work_sync.status"]["$in"] == ["pending", "processing"]
        return Cursor([dict(self.row)])

    async def find_one_and_update(self, query, update, _projection=None):
        intent = self.row["work_sync"]
        if query["work_sync.operation_id"] != intent["operation_id"]:
            return None
        for key, value in update["$set"].items():
            if key.startswith("work_sync."):
                self.row["work_sync"][key.split(".", 1)[1]] = value
        self.row["work_sync"]["attempts"] += update["$inc"]["work_sync.attempts"]
        return dict(self.row)

    async def update_one(self, query, update):
        assert query["work_sync.operation_id"] == self.row["work_sync"]["operation_id"]
        for key, value in update.get("$set", {}).items():
            if key.startswith("work_sync."):
                self.row["work_sync"][key.split(".", 1)[1]] = value
        for key in update.get("$unset", {}):
            if key.startswith("work_sync."):
                self.row["work_sync"].pop(key.split(".", 1)[1], None)
        return type("Result", (), {"matched_count": 1})()


class FakeItems:
    def __init__(self):
        self.row = {"item_id": "item_1", "org_id": "org_1"}

    async def update_one(self, query, update):
        if query["item_id"] != self.row["item_id"] or query["org_id"] != self.row["org_id"]:
            return type("Result", (), {"matched_count": 0})()
        if self.row.get("pcm_sync_operation_id") == query["pcm_sync_operation_id"]["$ne"]:
            return type("Result", (), {"matched_count": 0})()
        self.row.update(update["$set"])
        self.row.setdefault("history", []).append(update["$push"]["history"])
        return type("Result", (), {"matched_count": 1})()

    async def find_one(self, query, _projection):
        if query["item_id"] == self.row["item_id"]:
            return {"pcm_sync_operation_id": self.row.get("pcm_sync_operation_id")}
        return None


class FakeDB:
    def __init__(self, instruction):
        self.pcm_instructions = FakeInstructions(instruction)
        self.items = FakeItems()


def test_worker_applies_status_and_marks_intent_done(monkeypatch):
    instruction = {
        "instruction_id": "pcm_1", "org_id": "org_1", "item_id": "item_1",
        "updated_at": "2026-11-24T00:00:00Z",
        "work_sync": {
            "operation_id": "sync_1", "status": "pending", "work_status": "stuck",
            "due_at": None, "reason": "Material missing", "attempts": 0,
        },
    }
    db = FakeDB(instruction)
    monkeypatch.setattr(pcm_sync, "db", db)
    result = asyncio.run(pcm_sync.reconcile_pcm_work_sync())
    assert result["synced"] == 1
    assert db.items.row["status"] == "stuck"
    assert db.items.row["stuck_reason"] == "Material missing"
    assert db.items.row["pcm_sync_operation_id"] == "sync_1"
    assert db.pcm_instructions.row["work_sync"]["status"] == "done"


def test_worker_replay_does_not_duplicate_item_history(monkeypatch):
    instruction = {
        "instruction_id": "pcm_1", "org_id": "org_1", "item_id": "item_1",
        "updated_at": "2026-11-24T00:00:00Z",
        "work_sync": {
            "operation_id": "sync_1", "status": "pending", "work_status": "done",
            "due_at": None, "reason": "", "attempts": 0,
        },
    }
    db = FakeDB(instruction)
    db.items.row["pcm_sync_operation_id"] = "sync_1"
    monkeypatch.setattr(pcm_sync, "db", db)
    result = asyncio.run(pcm_sync.reconcile_pcm_work_sync())
    assert result["synced"] == 1
    assert db.items.row.get("history", []) == []
    assert db.pcm_instructions.row["work_sync"]["status"] == "done"
