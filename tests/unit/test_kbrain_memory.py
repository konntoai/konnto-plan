import pytest

from backend.kbrain_memory import build_user_confirmed_fact


def test_confirmed_fact_records_provenance_without_claiming_verification():
    member = {"member_id": "m1", "name": "Asha"}
    fact = build_user_confirmed_fact(
        fact_id="f1",
        org_id="o1",
        text="  Main supplier is ABC Traders  ",
        category="vendor",
        member=member,
        source="chat (user confirmed)",
        created_at="2026-11-24T10:00:00Z",
    )
    assert fact["text"] == "Main supplier is ABC Traders"
    assert fact["source_type"] == "conversation"
    assert fact["evidence_type"] == "user_confirmed_fact"
    assert fact["verification_status"] == "user_confirmed_not_independently_verified"
    assert fact["confidence"] == "user_attested"
    assert fact["version"] == 1


def test_confirmed_fact_rejects_empty_content():
    with pytest.raises(ValueError):
        build_user_confirmed_fact(
            fact_id="f1", org_id="o1", text=" ", category="other",
            member={"member_id": "m1", "name": "Asha"},
            source="manual", created_at="2026-11-24T10:00:00Z",
        )
