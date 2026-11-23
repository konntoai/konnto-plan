from pathlib import Path


def test_analysis_entrypoint_accepts_and_forwards_business_context():
    source = Path("backend/brain.py").read_text(encoding="utf-8")
    assert 'business_context: str = ""' in source
    assert "system = analysis_system(org, member, people, open_items, approvals, rules, cfg, role, business_context)" in source


def test_analysis_prompt_includes_retrieved_evidence():
    source = Path("backend/brain.py").read_text(encoding="utf-8")
    assert "AUTHORISED BUSINESS EVIDENCE" in source
    assert "{business_context or" in source
