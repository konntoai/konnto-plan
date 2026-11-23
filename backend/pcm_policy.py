"""Pure policy helpers for PCM visibility and issuing authority."""


def can_issue(member: dict) -> bool:
    return bool(member) and (member.get("member_type") == "owner" or (member.get("member_type") == "team" and "team_work" in (member.get("access") or [])))


def can_view(member: dict, instruction: dict) -> bool:
    if not member or not instruction:
        return False
    if member.get("member_type") == "owner" or (member.get("member_type") == "team" and "team_work" in (member.get("access") or [])):
        return True
    member_id = member.get("member_id")
    return member_id in (instruction.get("assignee_id"), instruction.get("issued_by"))
