"""K-BRAIN: the thinking core. Claude for understanding + replies, Whisper for voice."""
import os
import re
import json
import uuid
import logging
from typing import Optional, AsyncGenerator

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent, TextDelta, StreamDone

from core import db, now, iso, org_tz, log_usage, SCOPES, SAFE_SCOPES, fmt_local

logger = logging.getLogger("konnto.brain")
KEY = os.environ.get("EMERGENT_LLM_KEY", "")
MODEL = "claude-sonnet-4-6"
FAST = "claude-haiku-4-5-20251001"

DEFAULT_BRAIN = {
    "personality": "You are KONNTO, a calm, warm and very practical business assistant. You speak in short, clear sentences. You never lecture. You sound like a trusted manager who remembers everything.",
    "rules": "Never invent facts, dates or amounts. Never say something was done unless it was. Never move money. Never share one person's private notes or one-to-one chats with anyone else. Keep replies short (1-3 sentences) unless asked for a list.",
    "knowledge": "KONNTO AI is one AI brain for any business, anywhere. People talk to it on WhatsApp or in the app. It turns messages into tasks, promises, reminders and approvals, follows up, and sends a morning brief. Outside partners (suppliers, contractors, clients) are always free.",
    "faqs": [
        {"q": "Is KONNTO free?", "a": "KONNTO is free during launch. Partners like suppliers and contractors are always free."},
        {"q": "Do my partners need the app?", "a": "No. Partners can work with KONNTO on WhatsApp only."},
        {"q": "Who can see my data?", "a": "Only people in your business, and only what their job needs. Personal notes and one-to-one chats stay private."},
    ],
    "pricing_answers": "KONNTO is free during launch. Paid plans will come later; nobody is charged without agreeing first. Do not quote any prices.",
    "welcome_message": "Hi {name}, I'm KONNTO. Tell me anything about your business — a task, a promise, a reminder, or a question. Start with one line about what your business does.",
}


async def get_brain_config(draft: bool = False) -> dict:
    doc = await db.platform_config.find_one({"_id": "brain"})
    if not doc:
        return dict(DEFAULT_BRAIN)
    src = doc.get("draft") if draft and doc.get("draft") else doc.get("published")
    return {**DEFAULT_BRAIN, **(src or {})}


def _chat(system: str, model: str = MODEL, session: Optional[str] = None) -> LlmChat:
    return LlmChat(api_key=KEY, session_id=session or f"kb-{uuid.uuid4().hex}", system_message=system).with_model("anthropic", model)


# ------------------------------------------------------------------ analysis (structured understanding)
ANALYZE_TOOL = {"type": "function", "function": {
    "name": "record_analysis",
    "description": "Record exactly what this business message means and what KONNTO should do.",
    "parameters": {"type": "object", "properties": {
        "language": {"type": "string", "description": "ISO 639-1 code of the language the person wrote in"},
        "intent": {"type": "string", "enum": ["tell", "ask", "do", "decide", "chat"]},
        "items": {"type": "array", "description": "Tasks, promises, reminders, decisions or personal notes to OFFER for saving. Only real commitments.", "items": {"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["task", "promise", "reminder", "decision", "note"]},
            "title": {"type": "string", "description": "Short title in the person's language, max 80 chars"},
            "details": {"type": "string"},
            "assignee": {"type": "string", "description": "Person name from the people list who must act, or 'me' for the speaker"},
            "counterparty": {"type": "string", "description": "Outside party involved, e.g. a supplier or client name"},
            "due_at": {"type": "string", "description": "Local ISO datetime or date when it is due"},
            "remind_at": {"type": "string", "description": "Local ISO datetime when to remind"},
            "amount": {"type": "number"}, "currency": {"type": "string"},
            "project": {"type": "string"},
            "private": {"type": "boolean", "description": "True for a personal note only the speaker should see"},
        }, "required": ["kind", "title"]}},
        "actions": {"type": "array", "items": {"type": "object", "properties": {
            "type": {"type": "string", "enum": ["invite_person", "message_person", "add_rule", "request_approval", "decide_approval", "update_item", "update_business", "remember_fact", "need_access"]},
            "name": {"type": "string", "description": "invite_person: person's name"},
            "job": {"type": "string", "description": "invite_person: what they do"},
            "member_type": {"type": "string", "enum": ["team", "partner"]},
            "phone": {"type": "string"},
            "person": {"type": "string", "description": "message_person: who to message (name from people list)"},
            "text": {"type": "string", "description": "message_person text / add_rule rule text / remember_fact fact / need_access question"},
            "trigger": {"type": "string", "enum": ["reminder", "task", "approval", "any"], "description": "add_rule: when the rule applies"},
            "keyword": {"type": "string", "description": "add_rule: only applies to items mentioning this word, e.g. payment"},
            "notify": {"type": "string", "description": "add_rule: who to also inform/copy, e.g. accounts"},
            "approval_kind": {"type": "string", "enum": ["order", "payment", "time_off", "work_done", "access", "other"]},
            "title": {"type": "string"}, "amount": {"type": "number"}, "currency": {"type": "string"},
            "approval_id": {"type": "string"},
            "decision": {"type": "string", "enum": ["once", "always", "deny"]},
            "max_amount": {"type": "number", "description": "decide_approval always: allow automatically under this amount"},
            "item_id": {"type": "string"},
            "status": {"type": "string", "enum": ["done", "in_progress", "delayed", "stuck", "cancelled"]},
            "reason": {"type": "string"}, "new_due_at": {"type": "string"},
            "business_name": {"type": "string"}, "industry": {"type": "string"}, "description": {"type": "string"}, "country": {"type": "string"},
            "scope": {"type": "string", "enum": list(SCOPES.keys())},
        }, "required": ["type"]}},
        "search_query": {"type": "string", "description": "Keywords to look up in the business memory to answer, or empty"},
    }, "required": ["language", "intent", "items", "actions"]}}}


def _people_block(people: list) -> str:
    return "\n".join(f"- {p['name']} | {p.get('member_type')} | job: {p.get('job') or '-'} | id {p['member_id']}" for p in people) or "- (only the speaker so far)"


def analysis_system(org: dict, member: dict, people: list, open_items: list, approvals: list, rules: list, cfg: dict) -> str:
    tz = org_tz(org)
    local = now().astimezone(tz)
    items_txt = "\n".join(f"- {i['item_id']}: {i['title']} ({i.get('kind')}, {i.get('status')}, for {i.get('assignee_name') or '-'}, due {fmt_local(i.get('due_at'), org) or '-'})" for i in open_items[:40]) or "- none"
    ap_txt = "\n".join(f"- {a['approval_id']}: {a.get('kind')} — {a['title']} by {a.get('requested_by_name')} amount {a.get('amount') or '-'}" for a in approvals[:20]) or "- none"
    rules_txt = "\n".join(f"- {r['text']}" for r in rules[:30]) or "- none"
    access = ", ".join(sorted(set((member.get("access") or []) + ["own_work"]))) if member.get("member_type") != "owner" else "everything (owner)"
    return f"""You are K-BRAIN, the understanding layer of KONNTO AI for the business "{org.get('name')}" ({org.get('industry') or 'industry unknown'}; {org.get('description') or ''}).
Local time now: {local.strftime('%A %Y-%m-%d %H:%M')} ({tz.key}). Business currency: {org.get('currency') or 'USD'}.
Speaker: {member['name']} ({member.get('member_type')}, job: {member.get('job') or '-'}). Speaker access: {access}.

People in this business:
{_people_block(people)}

Open work the speaker can see:
{items_txt}

Approvals waiting for a decision (only the owner/approvers decide):
{ap_txt}

Business rules already saved:
{rules_txt}

Platform rules: {cfg.get('rules')}

Read the message and call record_analysis exactly once.
Guidance:
- items: offer every real task/promise/reminder/decision. "X promised Y by Thursday" = promise (due Thursday). "remind me Wednesday" = reminder (remind_at Wednesday 09:00 local) for 'me'. "Tell Ramesh to send the quote by Friday" = task assigned to Ramesh due Friday. Resolve weekdays to the NEXT such date. Use local ISO like 2026-11-18T09:00.
- invite_person when the speaker wants to add someone ("Add Ramesh, he handles purchasing"). Suppliers/contractors/clients are member_type partner.
- message_person only for a plain message to someone (not a task).
- add_rule for standing instructions like "From now on, always copy accounts on payment reminders".
- request_approval only when the speaker (not owner) asks permission for an order, payment, time off, finished work, or similar.
- decide_approval when the owner/approver answers a waiting approval in words (once / always / deny, with max_amount if they say "under X").
- update_item when someone reports progress on an existing item (use its id). Delayed/stuck need a reason.
- update_business when the owner describes the business (name, industry, what it does, country).
- remember_fact only for lasting facts about the business ("Our main supplier is Sharma Traders", "We close on Sundays"). Never for things already captured as items.
- need_access when the speaker asks for information outside their access (money, staff details, others' work, documents) — never for the owner.
- search_query: keywords to find what is needed to answer questions.
Return empty lists when nothing applies. Never invent people; if an assignee is not in the people list, still write their name."""


async def analyze(org, member, text, people, open_items, approvals, rules, cfg) -> dict:
    system = analysis_system(org, member, people, open_items, approvals, rules, cfg)
    chat = _chat(system).with_tools([ANALYZE_TOOL], tool_choice={"type": "function", "function": {"name": "record_analysis"}})
    try:
        r = await chat.send_message_with_tools(UserMessage(text=text[:6000]))
        await log_usage(org["org_id"], "brain_analyze", MODEL, r.usage)
        if r.tool_calls:
            a = r.tool_calls[0].arguments or {}
            a.setdefault("items", [])
            a.setdefault("actions", [])
            return a
    except Exception as e:
        logger.error("analyze failed: %s", e)
    return {"language": "en", "intent": "chat", "items": [], "actions": [], "search_query": text[:100], "failed": True}


# ------------------------------------------------------------------ reply (streamed)

def reply_system(org, member, cfg, sources: list, cards_summary: list, extra: str = "") -> str:
    tz = org_tz(org)
    src_txt = "\n".join(f"[{s['n']}] ({s['type']}) {s['title']}: {s.get('snippet', '')[:400]}" for s in sources) or "(no matching records)"
    cards_txt = "\n".join(f"- {c}" for c in cards_summary) or "- nothing"
    return f"""{cfg.get('personality')}
{cfg.get('rules')}
About KONNTO: {cfg.get('knowledge')}

You work for the business "{org.get('name')}". Local time: {now().astimezone(tz).strftime('%A %d %b %Y %H:%M')}.
You are talking to {member['name']} ({member.get('member_type')}, job: {member.get('job') or '-'}).

Business memory you may use (only these; cite with [n] right after the fact you use):
{src_txt}

What KONNTO already did or prepared for this message (cards are shown to the person under your reply; do not repeat their details at length):
{cards_txt}
{extra}
Write the reply:
- Same language as the person's message.
- 1-3 short sentences, or a short bullet list when listing work. No headings. No emojis.
- If something is prepared for saving, say it is ready and NOT saved yet ("Tap Save to keep it."). Never say it is saved or logged.
- If you don't know, say so and suggest what to tell you. Never invent records."""


async def stream_reply(org, member, text, cfg, sources, cards_summary, history: list, extra: str = "") -> AsyncGenerator:
    system = reply_system(org, member, cfg, sources, cards_summary, extra)
    initial = [{"role": "system", "content": system}]
    for h in history[-8:]:
        if h.get("text"):
            initial.append({"role": "user" if h["role"] == "user" else "assistant", "content": h["text"][:1500]})
    chat = LlmChat(api_key=KEY, session_id=f"kr-{uuid.uuid4().hex}", system_message=system, initial_messages=initial).with_model("anthropic", MODEL)
    usage = None
    try:
        async for ev in chat.stream_message(UserMessage(text=text[:6000])):
            if isinstance(ev, TextDelta):
                yield ev.content
            elif isinstance(ev, StreamDone):
                usage = ev.usage
    except Exception as e:
        logger.error("reply stream failed: %s", e)
        yield "\n\nSorry — I couldn't finish that reply. Please try again."
    await log_usage(org["org_id"], "brain_reply", MODEL, usage)


async def complete_text(system: str, text: str, org_id: Optional[str], feature: str, model: str = MODEL) -> str:
    out = []
    usage = None
    chat = _chat(system, model)
    try:
        async for ev in chat.stream_message(UserMessage(text=text)):
            if isinstance(ev, TextDelta):
                out.append(ev.content)
            elif isinstance(ev, StreamDone):
                usage = ev.usage
    except Exception as e:
        logger.error("%s failed: %s", feature, e)
        return ""
    await log_usage(org_id, feature, model, usage)
    return "".join(out).strip()


# ------------------------------------------------------------------ access decision (AI decides, starting small)
ACCESS_TOOL = {"type": "function", "function": {"name": "set_access", "description": "Choose the smallest access this person needs for their job.",
    "parameters": {"type": "object", "properties": {
        "scopes": {"type": "array", "items": {"type": "string", "enum": sorted(SAFE_SCOPES)}},
        "reason": {"type": "string", "description": "One short sentence for the owner, e.g. 'Ramesh will see his own work and the purchase documents.'"}},
        "required": ["scopes", "reason"]}}}


async def decide_access(org: dict, name: str, job: str, member_type: str) -> dict:
    default = {"scopes": ["own_work"] + (["documents"] if member_type == "team" else []),
               "reason": f"{name} will see their own work{' and business documents' if member_type == 'team' else ''}. Ask me if they need more."}
    system = (f"You set access for a new {member_type} member of the business '{org.get('name')}'. Start small. "
              "own_work = their own tasks; team_work = everyone's tasks (only for managers/supervisors); documents = shared business documents (staff who need files). "
              "Partners (suppliers, contractors, clients) get own_work only. Money, staff details, approvals and team management are NEVER given here.")
    chat = _chat(system, MODEL).with_tools([ACCESS_TOOL], tool_choice={"type": "function", "function": {"name": "set_access"}})
    try:
        r = await chat.send_message_with_tools(UserMessage(text=f"Name: {name}. Job: {job or 'not given'}."))
        await log_usage(org["org_id"], "access_decision", MODEL, r.usage)
        if r.tool_calls:
            a = r.tool_calls[0].arguments
            scopes = [s for s in a.get("scopes", []) if s in SAFE_SCOPES]
            if member_type == "partner":
                scopes = ["own_work"]
            if "own_work" not in scopes:
                scopes.insert(0, "own_work")
            return {"scopes": scopes, "reason": a.get("reason") or default["reason"]}
    except Exception as e:
        logger.error("decide_access failed: %s", e)
    return default


# ------------------------------------------------------------------ documents, photos, team-chat spotting
DOC_TOOL = {"type": "function", "function": {"name": "record_document", "description": "Summarise a business document.",
    "parameters": {"type": "object", "properties": {
        "summary": {"type": "string", "description": "2-4 short bullet points joined by newlines"},
        "doc_type": {"type": "string", "description": "e.g. invoice, quote, contract, price list, report, photo"},
        "key_details": {"type": "array", "items": {"type": "object", "properties": {"label": {"type": "string"}, "value": {"type": "string"}}, "required": ["label", "value"]}},
        "items": {"type": "array", "description": "Deadlines/promises/payments found that could be saved", "items": {"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["task", "promise", "reminder", "decision"]}, "title": {"type": "string"},
            "due_at": {"type": "string"}, "amount": {"type": "number"}, "currency": {"type": "string"}, "counterparty": {"type": "string"}}, "required": ["kind", "title"]}}},
        "required": ["summary", "doc_type", "key_details"]}}}


async def summarize_document(org: dict, filename: str, text: str) -> dict:
    tz = org_tz(org)
    system = (f"You read business documents for '{org.get('name')}'. Today is {now().astimezone(tz).strftime('%Y-%m-%d')}. "
              "Pull out the key details (parties, amounts, dates, numbers, terms). Be exact; never invent.")
    chat = _chat(system).with_tools([DOC_TOOL], tool_choice={"type": "function", "function": {"name": "record_document"}})
    try:
        r = await chat.send_message_with_tools(UserMessage(text=f"File: {filename}\n\n{text[:24000]}"))
        await log_usage(org["org_id"], "document", MODEL, r.usage)
        if r.tool_calls:
            return r.tool_calls[0].arguments
    except Exception as e:
        logger.error("summarize_document failed: %s", e)
    return {"summary": "", "doc_type": "document", "key_details": [], "items": []}


async def describe_image(org: dict, image_b64: str, hint: str = "") -> str:
    chat = _chat("You look at photos sent to a business assistant. Describe what matters for the business in 2-4 sentences and copy any visible text, numbers, dates and amounts exactly.")
    try:
        txt = await chat.send_message(UserMessage(text=hint or "What is in this photo?", file_contents=[ImageContent(image_base64=image_b64)]))
        await log_usage(org["org_id"], "photo", MODEL, None, cost=0.004)
        return (txt or "").strip()
    except Exception as e:
        logger.error("describe_image failed: %s", e)
        return ""


SPOT_TOOL = {"type": "function", "function": {"name": "record_commitments", "description": "Promises, tasks or decisions stated in a team chat message.",
    "parameters": {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {
        "kind": {"type": "string", "enum": ["task", "promise", "decision"]}, "title": {"type": "string"},
        "assignee": {"type": "string"}, "due_at": {"type": "string"}}, "required": ["kind", "title"]}}}, "required": ["items"]}}}

_SPOT_HINT = re.compile(r"\b(will|i'll|we'll|promise|by |tomorrow|today|tonight|monday|tuesday|wednesday|thursday|friday|saturday|sunday|deadline|deliver|send|pay|confirm|decided|agree|kal|parso|karunga|karenge|bhej)\b", re.I)


async def spot_commitments(org: dict, sender_name: str, text: str, people_names: list) -> list:
    if len(text) < 12 or not _SPOT_HINT.search(text):
        return []
    tz = org_tz(org)
    system = (f"Business '{org.get('name')}'. Today {now().astimezone(tz).strftime('%A %Y-%m-%d')}. Find only clear promises, tasks or decisions in this chat message from {sender_name}. "
              f"People: {', '.join(people_names)}. Use local ISO dates. Return empty list for small talk.")
    chat = _chat(system, FAST).with_tools([SPOT_TOOL], tool_choice={"type": "function", "function": {"name": "record_commitments"}})
    try:
        r = await chat.send_message_with_tools(UserMessage(text=text[:2000]))
        await log_usage(org["org_id"], "spot", FAST, r.usage)
        if r.tool_calls:
            return (r.tool_calls[0].arguments or {}).get("items", [])[:3]
    except Exception as e:
        logger.error("spot failed: %s", e)
    return []


# ------------------------------------------------------------------ help assistant (Ask KONNTO about the platform)

def help_system(cfg: dict) -> str:
    faqs = "\n".join(f"Q: {f.get('q')}\nA: {f.get('a')}" for f in (cfg.get("faqs") or []))
    return f"""{cfg.get('personality')}
You are the KONNTO AI help assistant. Answer questions about using KONNTO AI.
About KONNTO: {cfg.get('knowledge')}
Rules: {cfg.get('rules')}
Pricing instructions (follow exactly): {cfg.get('pricing_answers')}
FAQs:
{faqs}
Keep answers to 1-4 short sentences. If you don't know, say the KONNTO team will help and suggest using the feedback form."""


async def stream_help(question: str, history: list, cfg: dict, org_id: Optional[str]) -> AsyncGenerator:
    system = help_system(cfg)
    initial = [{"role": "system", "content": system}]
    for h in history[-6:]:
        if h.get("text") and h.get("role") in ("user", "assistant"):
            initial.append({"role": h["role"], "content": str(h["text"])[:1000]})
    chat = LlmChat(api_key=KEY, session_id=f"kh-{uuid.uuid4().hex}", system_message=system, initial_messages=initial).with_model("anthropic", MODEL)
    usage = None
    try:
        async for ev in chat.stream_message(UserMessage(text=question[:2000])):
            if isinstance(ev, TextDelta):
                yield ev.content
            elif isinstance(ev, StreamDone):
                usage = ev.usage
    except Exception as e:
        logger.error("help failed: %s", e)
        yield "Sorry, I couldn't answer right now. Please try again."
    await log_usage(org_id, "help", MODEL, usage)


# ------------------------------------------------------------------ approvals answered in words
DECIDE_TOOL = {"type": "function", "function": {"name": "record_decision", "description": "What did the approver decide?",
    "parameters": {"type": "object", "properties": {
        "decision": {"type": "string", "enum": ["once", "always", "deny", "unclear"]},
        "max_amount": {"type": "number", "description": "For 'always' with a limit like 'under 15000'"},
        "note": {"type": "string", "description": "Any condition or message for the requester, short"}},
        "required": ["decision"]}}}


async def interpret_decision(org: dict, ap: dict, text: str) -> dict:
    system = (f"An approver replied in words to this request at '{org.get('name')}': {ap['requested_by_name']} asks: {ap['title']}"
              f"{' amount ' + str(ap.get('amount')) if ap.get('amount') is not None else ''} ({ap['kind']}). "
              "'yes'/'ok this time' = once. 'always'/'from now on'/'don't ask again' = always (with max_amount if they give a limit). 'no' = deny.")
    chat = _chat(system).with_tools([DECIDE_TOOL], tool_choice={"type": "function", "function": {"name": "record_decision"}})
    try:
        r = await chat.send_message_with_tools(UserMessage(text=text[:1000]))
        await log_usage(org["org_id"], "decision", MODEL, r.usage)
        if r.tool_calls:
            return r.tool_calls[0].arguments
    except Exception as e:
        logger.error("interpret_decision failed: %s", e)
    return {"decision": "unclear"}


# ------------------------------------------------------------------ voice
async def transcribe_audio(org_id: Optional[str], path: str) -> str:
    from emergentintegrations.llm.openai import OpenAISpeechToText
    stt = OpenAISpeechToText(api_key=KEY)
    with open(path, "rb") as f:
        r = await stt.transcribe(file=f, model="whisper-1", response_format="json")
    await log_usage(org_id, "voice", "whisper-1", None, cost=0.006)
    return (getattr(r, "text", "") or "").strip()
