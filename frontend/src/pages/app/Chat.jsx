import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Send, Paperclip, Mic, Square, Loader2, Smile, Image as ImgIcon, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { KonntoMark, EmptyState } from "@/components/common";
import { BrainCard } from "@/components/cards/BrainCard";
import { useApi } from "@/lib/api";
import { useMe } from "@/context/MeContext";
import { fmtTime } from "@/lib/format";
import { cn } from "@/lib/utils";

const SUGGESTIONS = [
  "Remind me to call Ramesh tomorrow at 10am",
  "Supplier promised 200 cement bags by Thursday, remind me Wednesday",
  "What's overdue right now?",
  "Set a rule: always allow stationery under 1000",
];

function UserBubble({ msg }) {
  return (
    <div className="ml-auto max-w-[85%] text-right" data-testid="chat-user-msg">
      <div className="inline-block rounded-2xl rounded-tr-md bg-primary/10 border border-primary/15 px-3 py-2 text-sm whitespace-pre-wrap text-left">{msg.text || "\u2026"}</div>
      {msg.attachments?.length ? (
        <div className="mt-1.5 flex flex-wrap gap-1.5 justify-end">
          {msg.attachments.map((a, i) => (
            <span key={i} className="rounded-full border border-border bg-card px-2.5 py-1 text-xs text-muted-foreground">
              {a.type === "audio" ? "Voice" : a.type === "image" ? "Photo" : "Doc"}{a.filename ? `: ${a.filename}` : ""}
            </span>
          ))}
        </div>
      ) : null}
      <div className="text-[11px] text-muted-foreground mt-1">{fmtTime(msg.created_at) || "now"}</div>
    </div>
  );
}

function AssistantBubble({ msg, people, onCardAction }) {
  const cards = msg.cards || [];
  const text = msg.text || "";
  return (
    <div className="max-w-[90%]" data-testid="chat-assistant-msg">
      <div className="flex items-start gap-2">
        <KonntoMark size={28} />
        <div className="flex-1 min-w-0">
          {text ? (
            <div className="rounded-2xl rounded-tl-md bg-card border border-border px-3 py-2 text-sm whitespace-pre-wrap shadow-[0_1px_0_rgba(16,24,40,0.04)]" data-testid="chat-assistant-text">
              {text}
              {msg.streaming && <span className="inline-flex ml-2 align-middle gap-1"><span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" /></span>}
            </div>
          ) : msg.streaming ? (
            <div className="rounded-2xl rounded-tl-md bg-card border border-border px-3 py-2 text-sm"><span className="inline-flex gap-1"><span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" /></span></div>
          ) : null}
          {cards.length > 0 && (
            <div className="mt-2 space-y-2">
              {cards.map((c) => <BrainCard key={c.card_id} card={c} people={people} onAction={onCardAction} />)}
            </div>
          )}
          <div className="text-[11px] text-muted-foreground mt-1">{fmtTime(msg.created_at) || "now"}</div>
        </div>
      </div>
    </div>
  );
}

export default function ChatPage() {
  const api = useApi();
  const { me } = useMe();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [attachments, setAttachments] = useState([]);
  const [pendingUploads, setPendingUploads] = useState(0);
  const [recording, setRecording] = useState(false);
  const [recordSecs, setRecordSecs] = useState(0);
  const mediaRecorder = useRef(null);
  const scrollRef = useRef(null);
  const fileInput = useRef(null);
  const recordTimer = useRef(null);

  const [people, setPeople] = useState([]);

  useEffect(() => {
    let cancel = false;
    (async () => {
      try {
        const [m, mem] = await Promise.all([api.get("/chat/messages?limit=60"), api.get("/members")]);
        if (cancel) return;
        setMessages(m.messages || []);
        setPeople(mem.members || []);
      } catch (e) {
        toast.error(e.message);
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => { cancel = true; };
  }, [api]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    });
  };

  const uploadFile = async (file) => {
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
  };

  const handleFilePick = async (e) => {
    const files = Array.from(e.target.files || []);
    for (const f of files) await uploadFile(f);
    if (fileInput.current) fileInput.current.value = "";
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "" });
      const chunks = [];
      rec.ondataavailable = (e) => chunks.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        if (recordTimer.current) clearInterval(recordTimer.current);
        const blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
        const file = new File([blob], `voice-${Date.now()}.webm`, { type: blob.type });
        await uploadFile(file);
      };
      mediaRecorder.current = rec;
      rec.start();
      setRecording(true);
      setRecordSecs(0);
      recordTimer.current = setInterval(() => setRecordSecs((s) => s + 1), 1000);
    } catch (e) {
      toast.error("Microphone access denied");
    }
  };

  const stopRecording = (cancel = false) => {
    if (!mediaRecorder.current) return;
    if (cancel) mediaRecorder.current.ondataavailable = null;
    mediaRecorder.current.stop();
    setRecording(false);
  };

  const removeAttachment = (i) => setAttachments((a) => a.filter((_, idx) => idx !== i));

  const send = useCallback(async (overrideText) => {
    const body = (overrideText ?? text).trim();
    if (!body && attachments.length === 0) return;
    if (sending) return;
    setSending(true);
    const tempText = body;
    const sentAttachments = attachments.map((a) => ({
      type: a.type,
      file_id: a.file_id,
      doc_id: a.doc_id,
      filename: a.filename,
      description: a.description,
      transcript: a.transcript,
      summary: a.summary,
    }));
    setText("");
    setAttachments([]);

    let assistantPlaceholderIdx = null;
    try {
      await api.stream("/chat/stream", { text: tempText, attachments: sentAttachments }, (ev) => {
        if (ev.type === "user") {
          setMessages((m) => [...m, ev.message, { msg_id: `tmp-${Date.now()}`, role: "assistant", text: "", cards: [], streaming: true, created_at: new Date().toISOString() }]);
          assistantPlaceholderIdx = "created";
          scrollToBottom();
        } else if (ev.type === "cards") {
          setMessages((m) => {
            const copy = [...m];
            for (let i = copy.length - 1; i >= 0; i--) {
              if (copy[i].role === "assistant" && copy[i].streaming) { copy[i] = { ...copy[i], cards: ev.cards }; break; }
            }
            return copy;
          });
          scrollToBottom();
        } else if (ev.type === "delta") {
          setMessages((m) => {
            const copy = [...m];
            for (let i = copy.length - 1; i >= 0; i--) {
              if (copy[i].role === "assistant" && copy[i].streaming) { copy[i] = { ...copy[i], text: (copy[i].text || "") + ev.text }; break; }
            }
            return copy;
          });
          scrollToBottom();
        } else if (ev.type === "done") {
          setMessages((m) => {
            const copy = [...m];
            for (let i = copy.length - 1; i >= 0; i--) {
              if (copy[i].role === "assistant" && copy[i].streaming) { copy[i] = { ...ev.message, streaming: false }; break; }
            }
            return copy;
          });
          scrollToBottom();
        } else if (ev.type === "error") {
          toast.error(ev.message || "Something went wrong");
        }
      });
    } catch (e) {
      toast.error(e.message || "Message failed");
      setMessages((m) => m.filter((x) => !x.streaming));
      setText(tempText);
      setAttachments(sentAttachments);
    } finally {
      setSending(false);
    }
  }, [api, text, attachments, sending]);

  const onCardAction = useCallback(async (cardId, op, edits) => {
    try {
      const body = edits ? { edits } : {};
      const res = await api.post(`/chat/cards/${cardId}/${op}`, body);
      setMessages((msgs) => msgs.map((m) => {
        if (!m.cards) return m;
        const found = m.cards.some((c) => c.card_id === cardId);
        if (!found) return m;
        return { ...m, cards: m.cards.map((c) => c.card_id === cardId ? res.card || c : c) };
      }));
      toast.success(op === "save" ? "Saved" : op === "skip" ? "Skipped" : "Undone");
    } catch (e) {
      toast.error(e.message);
    }
  }, [api]);

  const canSend = (text.trim().length > 0 || attachments.length > 0) && !sending && pendingUploads === 0;

  return (
    <div className="h-[calc(100vh-56px)] lg:h-[calc(100vh-64px)] flex flex-col bg-background" data-testid="chat-page">
      <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="max-w-[760px] mx-auto px-4 py-5">
          {loading ? (
            <div className="flex justify-center py-10 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" /></div>
          ) : messages.length === 0 ? (
            <div className="pt-6">
              <EmptyState icon={Sparkles} title={`Hi ${me?.user?.name?.split(" ")[0] || "there"}. Talk to KONNTO.`} body="Tell me anything about your business — a task, a promise, a reminder, or a question. I'll handle the rest." testid="chat-empty-state">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => send(s)} className="rounded-full border border-border bg-card px-3 py-1.5 text-xs hover:bg-accent" data-testid="chat-suggestion-chip">{s}</button>
                ))}
              </EmptyState>
            </div>
          ) : (
            <div className="space-y-5">
              {messages.map((m) => (
                <div key={m.msg_id}>
                  {m.role === "user" ? <UserBubble msg={m} /> : <AssistantBubble msg={m} people={people} onCardAction={onCardAction} />}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-border bg-background/95 backdrop-blur">
        <div className="max-w-[760px] mx-auto px-3 py-2">
          {attachments.length > 0 && (
            <div className="flex flex-wrap gap-2 py-2" data-testid="chat-attachments-strip">
              {attachments.map((a, i) => (
                <span key={i} className="inline-flex items-center gap-2 rounded-full border border-border bg-secondary text-foreground px-3 py-1 text-xs">
                  {a.type === "audio" ? <Mic className="h-3.5 w-3.5" /> : a.type === "image" ? <ImgIcon className="h-3.5 w-3.5" /> : <Paperclip className="h-3.5 w-3.5" />}
                  <span className="max-w-[180px] truncate">{a.filename || (a.type === "audio" ? "Voice note" : a.type === "image" ? a.description?.slice(0, 40) || "Photo" : "File")}</span>
                  <button className="text-muted-foreground hover:text-foreground" aria-label="Remove" data-testid="chat-attachment-remove" onClick={() => removeAttachment(i)}>✕</button>
                </span>
              ))}
            </div>
          )}
          {recording ? (
            <div className="flex items-center gap-3 py-2" data-testid="chat-recording-bar">
              <span className="rec-dot" />
              <span className="tabular font-medium text-sm">{String(Math.floor(recordSecs / 60)).padStart(2, "0")}:{String(recordSecs % 60).padStart(2, "0")}</span>
              <span className="text-sm text-muted-foreground flex-1">Recording…</span>
              <Button size="sm" variant="outline" onClick={() => stopRecording(true)} data-testid="chat-record-cancel">Cancel</Button>
              <Button size="sm" onClick={() => stopRecording(false)} data-testid="chat-record-stop"><Square className="h-4 w-4 mr-1" /> Stop</Button>
            </div>
          ) : (
            <div className="flex items-end gap-2">
              <input ref={fileInput} type="file" onChange={handleFilePick} className="hidden" accept="image/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.csv,.txt" multiple data-testid="chat-file-input" />
              <Button type="button" variant="ghost" size="icon" className="shrink-0" aria-label="Attach" data-testid="chat-attach-button" onClick={() => fileInput.current?.click()} disabled={pendingUploads > 0}>
                {pendingUploads > 0 ? <Loader2 className="h-5 w-5 animate-spin" /> : <Paperclip className="h-5 w-5" />}
              </Button>
              <Textarea
                data-testid="chat-composer-textarea"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(); } }}
                placeholder={"Type, send a voice note, or share a file…"}
                rows={1}
                className="resize-none min-h-[44px] max-h-[140px] rounded-xl flex-1"
              />
              <Button type="button" variant="ghost" size="icon" aria-label="Record voice" data-testid="chat-mic-button" onClick={startRecording}><Mic className="h-5 w-5" /></Button>
              <Button type="button" size="icon" aria-label="Send" data-testid="chat-composer-send-button" disabled={!canSend} onClick={() => send()} className={cn("btn-lift", !canSend && "opacity-70")}>
                {sending ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          )}
          <div className="text-[11px] text-muted-foreground text-center pt-1 pb-0.5">Enter to send · Shift+Enter for a new line</div>
        </div>
      </div>
    </div>
  );
}
