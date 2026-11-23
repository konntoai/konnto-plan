import unittest

from backend.pcm_policy import can_issue, can_view


class PCMPolicyTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
