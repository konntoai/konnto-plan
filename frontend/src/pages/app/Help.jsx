import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Send, Loader2, MessageCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { KonntoOrb, PageHeader, SectionCard } from "@/components/common";
import { useApi } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function HelpPage() {
  const api = useApi();
  const [msgs, setMsgs] = useState([{ role: "assistant", text: "Hi! Ask me anything about KONNTO — how to use it, what it does, settings…" }]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [msgs]);

  const send = async () => {
    if (!text.trim() || busy) return;
    const q = text;
    setText("");
    setMsgs((m) => [...m, { role: "user", text: q }, { role: "assistant", text: "" }]);
    setBusy(true);
    try {
      await api.stream("/help/chat", { text: q }, (ev) => {
        if (ev.type === "delta") setMsgs((m) => { const c = [...m]; c[c.length - 1] = { ...c[c.length - 1], text: c[c.length - 1].text + ev.text }; return c; });
      });
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  const sendFeedback = async () => {
    if (!feedback.trim()) return;
    try { await api.post("/feedback", { text: feedback, page: "/app/help" }); toast.success("Sent — thank you"); setFeedback(""); } catch (e) { toast.error(e.message); }
  };

  return (
    <div className="p-4 lg:p-8 max-w-[900px] mx-auto space-y-5" data-testid="help-page">
      <PageHeader eyebrow="Support" title="Help" subtitle="Ask KONNTO anything, or send us a note. We read every one." />

      <div className="k-shimmer k-shimmer--calm" data-testid="help-chat-card">
        <div className="relative rounded-[inherit] bg-card/95 p-4 sm:p-5">
          <div className="flex items-center gap-3 mb-4">
            <KonntoOrb size={40} state={busy ? "streaming" : "idle"} />
            <div><div className="eyebrow text-primary">Help assistant</div><div className="font-display font-bold">Ask KONNTO</div></div>
          </div>
          <div className="min-h-[220px] max-h-[380px] overflow-y-auto scrollbar-thin space-y-3 pr-1">
            {msgs.map((m, i) => (
              m.role === "user"
                ? <div key={i} className="ml-auto max-w-[85%] rounded-[18px] rounded-tr-md bg-brand-gradient text-white px-4 py-2.5 text-sm w-fit">{m.text}</div>
                : <div key={i} className={cn("k-seam max-w-[90%] rounded-[18px] rounded-tl-md glass pl-5 pr-4 py-2.5 text-sm whitespace-pre-wrap w-fit", busy && i === msgs.length - 1 && "k-seam--live")}>{m.text || <span className="flex gap-1.5 py-1"><span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" /></span>}</div>
            ))}
            <div ref={endRef} />
          </div>
          <div className="mt-4 flex gap-2">
            <Input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); send(); } }} placeholder="Type a question" data-testid="help-chat-input" />
            <Button size="icon" onClick={send} disabled={busy || !text.trim()} data-testid="help-chat-send" aria-label="Send">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}</Button>
          </div>
        </div>
      </div>

      <SectionCard title="Send us feedback" icon={MessageCircle} testid="help-feedback-card">
        <Textarea rows={3} value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="What could be better? A bug, idea, or just a note." data-testid="feedback-text" />
        <Button className="mt-3" onClick={sendFeedback} disabled={!feedback.trim()} data-testid="feedback-send">Send</Button>
      </SectionCard>
    </div>
  );
}
