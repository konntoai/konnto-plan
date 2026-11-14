import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { useApi } from "@/lib/api";

const BrainChatContext = createContext(null);

const TOAST_FOR = { save: "Saved", skip: "Skipped", undo: "Undone", confirm: "Confirmed — sent", dismiss: "Dismissed" };

/** One K-BRAIN conversation shared by the full Chat page and the floating panel. */
export function BrainChatProvider({ children }) {
  const api = useApi();
  const [messages, setMessages] = useState([]);
  const [people, setPeople] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [attachments, setAttachments] = useState([]);
  const [pendingUploads, setPendingUploads] = useState(0);
  const sendingRef = useRef(false);

  const load = useCallback(async () => {
    try {
      const [m, mem] = await Promise.all([api.get("/chat/messages?limit=60"), api.get("/members")]);
      setMessages(m.messages || []);
      setPeople(mem.members || []);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => { load(); }, [load]);

  const uploadFile = useCallback(async (file) => {
    setPendingUploads((n) => n + 1);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api.upload("/chat/upload", fd);
      setAttachments((a) => [...a, res]);
      toast.success(res.type === "audio" ? "Voice transcribed" : res.type === "image" ? "Photo attached" : "Document saved");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setPendingUploads((n) => n - 1);
    }
  }, [api]);

  const removeAttachment = useCallback((i) => setAttachments((a) => a.filter((_, idx) => idx !== i)), []);

  const patchStreaming = (fn) => setMessages((m) => {
    const copy = [...m];
    for (let i = copy.length - 1; i >= 0; i--) {
      if (copy[i].role === "assistant" && copy[i].streaming) { copy[i] = fn(copy[i]); break; }
    }
    return copy;
  });

  /** Returns true when the message went through, false to let the caller restore the typed text. */
  const send = useCallback(async (body) => {
    const text = (body || "").trim();
    if ((!text && attachments.length === 0) || sendingRef.current) return false;
    sendingRef.current = true;
    setSending(true);
    const sent = attachments.map((a) => ({ type: a.type, file_id: a.file_id, doc_id: a.doc_id, filename: a.filename, description: a.description, transcript: a.transcript, summary: a.summary }));
    setAttachments([]);
    let ok = true;
    try {
      await api.stream("/chat/stream", { text, attachments: sent }, (ev) => {
        if (ev.type === "user") {
          setMessages((m) => [...m, ev.message, { msg_id: `tmp-${Date.now()}`, role: "assistant", text: "", cards: [], streaming: true, created_at: new Date().toISOString() }]);
        } else if (ev.type === "cards") {
          patchStreaming((c) => ({ ...c, cards: ev.cards }));
        } else if (ev.type === "delta") {
          patchStreaming((c) => ({ ...c, text: (c.text || "") + ev.text }));
        } else if (ev.type === "done") {
          patchStreaming(() => ({ ...ev.message, streaming: false }));
        } else if (ev.type === "error") {
          toast.error(ev.message || "Something went wrong");
        }
      });
    } catch (e) {
      ok = false;
      toast.error(e.message || "Message failed");
      setMessages((m) => m.filter((x) => !x.streaming));
      setAttachments(sent);
    } finally {
      sendingRef.current = false;
      setSending(false);
    }
    return ok;
  }, [api, attachments]);

  const onCardAction = useCallback(async (cardId, op, edits) => {
    try {
      const res = await api.post(`/chat/cards/${cardId}/${op}`, edits ? { edits } : {});
      setMessages((msgs) => msgs.map((m) => (m.cards?.some((c) => c.card_id === cardId)
        ? { ...m, cards: m.cards.map((c) => (c.card_id === cardId ? res.card || c : c)) }
        : m)));
      toast.success(TOAST_FOR[op] || "Done");
    } catch (e) {
      toast.error(e.message);
    }
  }, [api]);

  const reset = useCallback(async () => {
    try {
      await api.post("/chat/reset", {});
      setMessages([]);
      toast.success("Fresh conversation started — your business data is untouched");
    } catch (e) {
      toast.error(e.message);
    }
  }, [api]);

  const value = { messages, people, loading, sending, attachments, pendingUploads, uploadFile, removeAttachment, send, onCardAction, reset, reload: load };
  return <BrainChatContext.Provider value={value}>{children}</BrainChatContext.Provider>;
}

export function useBrainChat() {
  const ctx = useContext(BrainChatContext);
  if (!ctx) throw new Error("useBrainChat must be used inside BrainChatProvider");
  return ctx;
}

/** Voice notes: records with MediaRecorder and hands the file to uploadFile. */
export function useVoiceRecorder(uploadFile) {
  const [recording, setRecording] = useState(false);
  const [secs, setSecs] = useState(0);
  const rec = useRef(null);
  const timer = useRef(null);

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const r = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "" });
      const chunks = [];
      r.ondataavailable = (e) => chunks.push(e.data);
      r.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        if (timer.current) clearInterval(timer.current);
        if (!chunks.length) return;
        const blob = new Blob(chunks, { type: r.mimeType || "audio/webm" });
        await uploadFile(new File([blob], `voice-${Date.now()}.webm`, { type: blob.type }));
      };
      rec.current = r;
      r.start();
      setRecording(true);
      setSecs(0);
      timer.current = setInterval(() => setSecs((s) => s + 1), 1000);
    } catch {
      toast.error("Microphone access denied");
    }
  };

  const stop = (cancel = false) => {
    if (!rec.current) return;
    if (cancel) rec.current.ondataavailable = null;
    rec.current.stop();
    setRecording(false);
  };

  return { recording, secs, start, stop };
}
