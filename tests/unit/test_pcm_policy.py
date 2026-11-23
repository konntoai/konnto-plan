import unittest

from backend.pcm_policy import (
    can_issue,
    can_view,
    progress_update_filter,
    progress_update_document,
    work_status_for_pcm,
    work_sync_intent,
)


class PCMPolicyTests(unittest.TestCase):
    def test_progress_filter_is_org_scoped_and_compare_and_set(self):
        record = {"updated_at": "2026-11-23T10:00:00.000Z", "status": "in_progress"}
        query = progress_update_filter("pcm_1", "org_1", record)
        self.assertEqual(query["instruction_id"], "pcm_1")
        self.assertEqual(query["org_id"], "org_1")
        self.assertEqual(query["updated_at"], record["updated_at"])
        self.assertEqual(query["status"], {"$nin": ["completed", "cancelled"]})
        self.assertEqual(query["deleted"], {"$ne": True})

    def test_progress_update_document_persists_status_history_and_evidence_together(self):
        event = {"event": "completed", "note": "Verified"}
        evidence = {"text": "Photo checked"}
        update = progress_update_document(
            "completed", "2026-11-23T10:05:00.000Z", event,
            evidence_entry=evidence,
        )
        self.assertEqual(update["$set"]["status"], "completed")
        self.assertEqual(update["$push"]["history"], event)
        self.assertEqual(update["$push"]["evidence"], evidence)
        self.assertNotIn("blocker", update["$set"])

    def test_progress_update_document_clears_blocker_when_work_resumes(self):
        update = progress_update_document(
            "in_progress", "2026-11-23T10:05:00.000Z", {"event": "in_progress"},
            due_at="2026-11-25T10:00:00.000Z",
        )
        self.assertIsNone(update["$set"]["blocker"])
        self.assertEqual(update["$set"]["due_at"], "2026-11-25T10:00:00.000Z")

    def test_only_owner_or_team_work_can_issue(self):
        self.assertTrue(can_issue({"member_type": "owner", "access": []}))
        self.assertTrue(can_issue({"member_type": "team", "access": ["own_work", "team_work"]}))
        self.assertFalse(can_issue({"member_type": "team", "access": ["own_work"]}))
        self.assertFalse(can_issue({"member_type": "partner", "access": ["team_work"]}))
        self.assertFalse(can_issue({}))

    def test_owner_and_team_work_can_view_all_instructions(self):
        record = {"assignee_id": "a", "issued_by": "b"}
        self.assertTrue(can_view({"member_type": "owner", "member_id": "x"}, record))
        self.assertTrue(can_view({"member_type": "team", "member_id": "x", "access": ["team_work"]}, record))

    def test_individuals_can_only_view_their_own_issued_or_assigned_records(self):
        record = {"assignee_id": "a", "issued_by": "b"}
        self.assertTrue(can_view({"member_type": "team", "member_id": "a", "access": []}, record))
        self.assertTrue(can_view({"member_type": "team", "member_id": "b", "access": []}, record))
        self.assertFalse(can_view({"member_type": "team", "member_id": "c", "access": []}, record))
        self.assertFalse(can_view({"member_type": "partner", "member_id": "a", "access": []}, {"assignee_id": "z", "issued_by": "b"}))


    def test_pcm_work_sync_intent_is_replayable_and_maps_states(self):
        intent = work_sync_intent(
            "blocked", operation_id="sync_123", due_at="2026-11-25T10:00:00Z",
            reason="Waiting for material",
        )
        self.assertEqual(intent["operation_id"], "sync_123")
        self.assertEqual(intent["status"], "pending")
        self.assertEqual(intent["work_status"], "stuck")
        self.assertEqual(intent["due_at"], "2026-11-25T10:00:00Z")
        self.assertEqual(intent["reason"], "Waiting for material")
        self.assertEqual(intent["attempts"], 0)

    def test_pcm_status_mapping_is_explicit_and_does_not_guess(self):
        self.assertEqual(work_status_for_pcm("in_progress"), "in_progress")
        self.assertEqual(work_status_for_pcm("blocked"), "stuck")
        self.assertEqual(work_status_for_pcm("completed"), "done")
        self.assertEqual(work_status_for_pcm("cancelled"), "cancelled")
        self.assertIsNone(work_status_for_pcm("acknowledged"))
        self.assertIsNone(work_status_for_pcm("unknown"))

if __name__ == "__main__":
    unittest.main()
