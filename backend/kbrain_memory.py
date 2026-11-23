"""Consistent K-Memory record construction for user-confirmed business facts."""


def build_user_confirmed_fact(
    *,
    fact_id: str,
    org_id: str,
    text: str,
    category: str,
    member: dict,
    source: str,
    created_at: str,
) -> dict:
    """Create a provenance-rich record without implying independent verification."""
    clean_text = (text or "").strip()[:400]
    if not clean_text:
        raise ValueError("A memory fact cannot be empty")
    return {
        "fact_id": fact_id,
        "org_id": org_id,
        "text": clean_text,
        "category": category,
        "source": source,
        "source_type": "conversation" if source.startswith("chat") else "manual",
        "evidence_type": "user_confirmed_fact",
        "verification_status": "user_confirmed_not_independently_verified",
        "confidence": "user_attested",
        "visibility": "org",
        "confirmed": True,
        "created_by": member["member_id"],
        "created_by_name": member["name"],
        "created_at": created_at,
        "updated_at": created_at,
        "version": 1,
        "lifecycle_status": "active",
        "supersedes_fact_id": None,
    }


def build_fact_correction_metadata(previous: dict, *, corrected_at: str, corrected_by: dict) -> dict:
    """Metadata to close a prior fact after its replacement has been safely inserted."""
    return {
        "lifecycle_status": "superseded",
        "superseded_at": corrected_at,
        "superseded_by": corrected_by["member_id"],
    }
