"""Deterministic relevance ranking for permission-scoped K-BRAIN retrieval."""
import re

_STOP = set("""the a an and or to of for in on at by with is are was were be been this that these those what which who whom when where why how do does did can could should would will shall may might must have has had i me my we our you your he she it they them their there here from about into please tell show give get any all some today tomorrow""".split())


def _terms(text):
    return {w for w in re.findall(r"[\w₹$€£]{3,}", (text or "").lower()) if w not in _STOP}


def rank_sources(query, sources):
    """Return copies sorted by query relevance, preserving stable order on ties."""
    terms = _terms(query)
    if not terms:
        return [dict(source) for source in sources]
    phrase = " ".join((query or "").lower().split())
    scored = []
    for index, source in enumerate(sources):
        title = (source.get("title") or "").lower()
        body = (source.get("snippet") or "").lower()
        title_terms = _terms(title)
        body_terms = _terms(body)
        score = len(terms & title_terms) * 5 + len(terms & body_terms)
        if phrase and phrase in title:
            score += 12
        elif phrase and phrase in body:
            score += 6
        if terms.issubset(title_terms | body_terms):
            score += 3
        scored.append((score, index, dict(source)))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in scored]
