from kbrain_workflow import BRANCHES, branch_context, normalise_branch


def test_all_branches_have_guidance():
    for name in BRANCHES:
        context = branch_context({"branch": name})
        assert f"ACTIVE K-BRAIN BRANCH: {name.upper()}" in context
        assert "does not grant data access" in context


def test_unknown_branch_falls_back_to_general():
    assert normalise_branch("not-a-real-branch") == "general"
    assert "ACTIVE K-BRAIN BRANCH: GENERAL" in branch_context({"branch": "not-a-real-branch"})


def test_invalid_subdomain_is_safely_normalised():
    context = branch_context({"branch": "business", "subdomain": "superuser"})
    assert "ACTIVE SUBDOMAIN: other" in context


def test_response_mode_and_reasoning_level_are_carried_forward():
    context = branch_context({
        "branch": "analyst",
        "subdomain": "finance",
        "response_mode": "analyse",
        "reasoning_level": "deep",
    })
    assert "ACTIVE SUBDOMAIN: finance" in context
    assert "RESPONSE MODE: analyse; REASONING DEPTH: deep" in context
