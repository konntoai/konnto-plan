from backend.kbrain_retrieval import rank_sources


def test_title_matches_rank_above_incidental_body_matches():
    sources = [
        {"n": 1, "type": "chat", "title": "General update", "snippet": "supplier invoice was mentioned"},
        {"n": 2, "type": "document", "title": "Supplier invoice", "snippet": "Payment terms and due date"},
    ]
    ranked = rank_sources("supplier invoice", sources)
    assert ranked[0]["title"] == "Supplier invoice"


def test_ranking_is_stable_for_equal_scores():
    sources = [{"title": "Alpha", "snippet": "project status"}, {"title": "Beta", "snippet": "project status"}]
    assert [s["title"] for s in rank_sources("project", sources)] == ["Alpha", "Beta"]


def test_empty_query_preserves_retrieval_order():
    sources = [{"title": "B"}, {"title": "A"}]
    assert [s["title"] for s in rank_sources("", sources)] == ["B", "A"]


def test_ranking_does_not_mutate_source_records():
    source = {"n": 9, "title": "invoice", "snippet": "supplier"}
    rank_sources("supplier", [source])
    assert source["n"] == 9
