from backend.kbrain_memory import build_user_confirmed_fact, build_fact_correction_metadata


def test_new_facts_start_active_and_linkless():
    fact = build_user_confirmed_fact(
        fact_id="fct_new", org_id="org_1", text="Main supplier is ABC", category="operations",
        member={"member_id": "mem_1", "name": "Owner"}, source="manual", created_at="2026-11-24T00:00:00Z",
    )
    assert fact["lifecycle_status"] == "active"
    assert fact["supersedes_fact_id"] is None


def test_correction_metadata_supersedes_old_fact_without_erasing_provenance():
    previous = {"fact_id": "fct_old", "created_by": "mem_1", "version": 1}
    metadata = build_fact_correction_metadata(
        previous, corrected_at="2026-11-24T00:00:00Z", corrected_by={"member_id": "mem_2"}
    )
    assert metadata == {
        "lifecycle_status": "superseded",
        "superseded_at": "2026-11-24T00:00:00Z",
        "superseded_by": "mem_2",
    }
    assert previous["created_by"] == "mem_1"
