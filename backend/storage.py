"""Private file storage (Emergent object storage). All access goes through permission-checked API routes."""
import os
import io
import csv
import logging
import requests
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger("konnto.storage")

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "konnto"
_state = {"key": None}

MAX_BYTES = 20 * 1024 * 1024
DOC_TYPES = {
    "pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "csv": "text/csv", "txt": "text/plain", "md": "text/markdown",
}
IMAGE_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}
AUDIO_TYPES = {"webm": "audio/webm", "mp3": "audio/mpeg", "m4a": "audio/mp4", "mp4": "audio/mp4", "wav": "audio/wav", "ogg": "audio/ogg", "mpeg": "audio/mpeg", "opus": "audio/ogg"}


def init_storage(force: bool = False):
    if _state["key"] and not force:
        return _state["key"]
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _state["key"] = resp.json()["storage_key"]
    return _state["key"]


def _put(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _get(path: str) -> tuple:
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


async def put_object(path: str, data: bytes, content_type: str) -> dict:
    return await run_in_threadpool(_put, path, data, content_type)


async def get_object(path: str) -> tuple:
    return await run_in_threadpool(_get, path)


def ext_of(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if filename and "." in filename else ""


def extract_text(filename: str, data: bytes) -> str:
    ext = ext_of(filename)
    try:
        if ext == "pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            return "\n".join((p.extract_text() or "") for p in reader.pages[:60])
        if ext == "docx":
            import docx
            d = docx.Document(io.BytesIO(data))
            parts = [p.text for p in d.paragraphs]
            for t in d.tables:
                for row in t.rows:
                    parts.append(" | ".join(c.text for c in row.cells))
            return "\n".join(parts)
        if ext == "xlsx":
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            out = []
            for ws in wb.worksheets[:5]:
                out.append(f"# Sheet {ws.title}")
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    if i > 400:
                        break
                    out.append(" | ".join("" if v is None else str(v) for v in row))
            return "\n".join(out)
        if ext == "csv":
            text = data.decode("utf-8", errors="ignore")
            rows = list(csv.reader(io.StringIO(text)))[:500]
            return "\n".join(" | ".join(r) for r in rows)
        if ext in ("txt", "md"):
            return data.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error("extract_text failed for %s: %s", filename, e)
    return ""
