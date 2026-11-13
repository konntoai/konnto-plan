"""KONNTO AI core POC: K-BRAIN analysis (Claude tool call), streaming reply, email, storage, whisper."""
import asyncio, json, os, sys, time, io, uuid
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
import requests, httpx
from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone
from emergentintegrations.llm.openai import OpenAISpeechToText, OpenAITextToSpeech

KEY = os.environ["EMERGENT_LLM_KEY"]
RESULTS = {}

ANALYZE_TOOL = {"type": "function", "function": {
    "name": "record_analysis",
    "description": "Record what the business message means.",
    "parameters": {"type": "object", "properties": {
        "language": {"type": "string"},
        "intent": {"type": "string", "enum": ["tell", "ask", "do", "chat"]},
        "items": {"type": "array", "items": {"type": "object", "properties": {
            "kind": {"type": "string", "enum": ["task", "promise", "reminder", "decision", "note"]},
            "title": {"type": "string"}, "assignee_name": {"type": "string"},
            "counterparty": {"type": "string"}, "due_at": {"type": "string"}, "remind_at": {"type": "string"},
            "amount": {"type": "number"}, "currency": {"type": "string"}}, "required": ["kind", "title"]}},
        "actions": {"type": "array", "items": {"type": "object", "properties": {
            "type": {"type": "string", "enum": ["invite_member", "message_person", "add_rule", "approval_request"]},
            "name": {"type": "string"}, "job": {"type": "string"}, "text": {"type": "string"}}, "required": ["type"]}}},
        "required": ["language", "intent", "items", "actions"]}}}


async def model_try(model):
    chat = LlmChat(api_key=KEY, session_id=f"poc-{uuid.uuid4()}", system_message=(
        "You are K-BRAIN. Today is Monday 2026-11-16, timezone Asia/Kolkata. Always call record_analysis."))
    chat.with_model("anthropic", model).with_tools([ANALYZE_TOOL], tool_choice={"type": "function", "function": {"name": "record_analysis"}})
    t = time.time()
    r = await chat.send_message_with_tools(UserMessage(text="Supplier Sharma promised stock by Thursday, remind me Wednesday. Also add Ramesh, he handles purchasing."))
    args = r.tool_calls[0].arguments if r.tool_calls else None
    return args, r.usage, round(time.time() - t, 1)


async def test_analyze():
    for model in ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-sonnet-5-5"]:
        try:
            args, usage, secs = await model_try(model)
            ok = bool(args) and any(i.get("kind") in ("promise", "reminder") for i in args.get("items", [])) and any(a.get("type") == "invite_member" for a in args.get("actions", []))
            print(f"[analyze:{model}] ok={ok} {secs}s usage={usage}\n  {json.dumps(args)[:600]}")
            RESULTS[f"analyze_{model}"] = ok
        except Exception as e:
            print(f"[analyze:{model}] FAIL {e}")
            RESULTS[f"analyze_{model}"] = False


async def test_stream():
    chat = LlmChat(api_key=KEY, session_id="poc-stream", system_message="You are KONNTO, a calm business assistant. Reply in the user's language, in 2 sentences.")
    chat.with_model("anthropic", "claude-sonnet-4-6")
    out, usage = [], None
    async for ev in chat.stream_message(UserMessage(text="नमस्ते, कल का काम क्या है?")):
        if isinstance(ev, TextDelta):
            out.append(ev.content)
        elif isinstance(ev, StreamDone):
            usage = ev.usage
    txt = "".join(out)
    print(f"[stream] chunks={len(out)} usage={usage}\n  {txt[:300]}")
    RESULTS["stream"] = len(txt) > 10


async def test_email():
    payload = {"to": ["delivered@resend.dev"], "subject": "KONNTO AI test", "html": "<p>Hello from KONNTO AI</p>", "from_name": os.environ["EMAIL_FROM_NAME"]}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post("https://integrations.emergentagent.com/api/v1/email/send", headers={"X-Email-Key": os.environ["EMERGENT_EMAIL_KEY"]}, json=payload)
    print(f"[email] {r.status_code} {r.text[:200]}")
    RESULTS["email"] = r.status_code in (200, 202)


def test_storage():
    base = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
    url = base.rstrip("/") + "/objstore/api/v1/storage"
    k = requests.post(f"{url}/init", json={"emergent_key": KEY}, timeout=30).json()["storage_key"]
    path = f"konnto/poc/{uuid.uuid4()}.txt"
    p = requests.put(f"{url}/objects/{path}", headers={"X-Storage-Key": k, "Content-Type": "text/plain"}, data=b"konnto storage ok", timeout=60)
    p.raise_for_status()
    g = requests.get(f"{url}/objects/{p.json()['path']}", headers={"X-Storage-Key": k}, timeout=60)
    print(f"[storage] put={p.status_code} get={g.status_code} body={g.content[:40]}")
    RESULTS["storage"] = g.content == b"konnto storage ok"


async def test_whisper():
    tts = OpenAITextToSpeech(api_key=KEY)
    audio = await tts.generate_speech(text="Remind me tomorrow at ten to call Sharma Traders about the cement order.", model="tts-1", voice="alloy", response_format="mp3")
    path = "/tmp/poc_voice.mp3"
    open(path, "wb").write(audio)
    stt = OpenAISpeechToText(api_key=KEY)
    with open(path, "rb") as f:
        r = await stt.transcribe(file=f, model="whisper-1", response_format="json")
    print(f"[whisper] {r.text}")
    RESULTS["whisper"] = "sharma" in r.text.lower()


async def main():
    await test_analyze()
    await test_stream()
    await test_email()
    try:
        test_storage()
    except Exception as e:
        print("[storage] FAIL", e); RESULTS["storage"] = False
    try:
        await test_whisper()
    except Exception as e:
        print("[whisper] FAIL", e); RESULTS["whisper"] = False
    print("\nRESULTS", json.dumps(RESULTS, indent=1))

asyncio.run(main())
