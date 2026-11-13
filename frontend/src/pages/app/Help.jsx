import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Send, LifeBuoy, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { KonntoMark, PageHeader, SectionCard } from "@/components/common";
import { useApi } from "@/lib/api";

export default function HelpPage() {
  const api = useApi();
  const [msgs, setMsgs] = useState([{ role: "assistant", text: "Hi! Ask me anything about KONNTO — how to use it, what it does, settings…" }]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

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
    <div className="p-4 lg:p-6 max-w-[900px] mx-auto space-y-5" data-testid="help-page">
      <PageHeader title="Help" subtitle="Ask KONNTO anything, or send us a note. We read every one." />

      <SectionCard title="Ask KONNTO" testid="help-chat-card">
        <div className="space-y-3">
          <div className="min-h-[220px] max-h-[380px] overflow-y-auto scrollbar-thin space-y-2">
            {msgs.map((m, i) => (
              m.role === "user"
                ? <div key={i} className="ml-auto max-w-[85%] rounded-2xl rounded-tr-md bg-primary/10 border border-primary/15 px-3 py-2 text-sm">{m.text}</div>
                : <div key={i} className="flex gap-2 items-start"><KonntoMark size={26} /><div className="max-w-[85%] rounded-2xl rounded-tl-md bg-card border border-border px-3 py-2 text-sm whitespace-pre-wrap">{m.text || <span className="flex gap-1 py-1"><span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" /></span>}</div></div>
            ))}
            <div ref={endRef} />
          </div>
          <div className="flex gap-2">
            <Input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); send(); } }} placeholder="Type a question" data-testid="help-chat-input" />
            <Button onClick={send} disabled={busy || !text.trim()} data-testid="help-chat-send">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}</Button>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Send us feedback" testid="help-feedback-card">
        <Textarea rows={3} value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="What could be better? A bug, idea, or just a note." data-testid="feedback-text" />
        <Button className="mt-2" onClick={sendFeedback} disabled={!feedback.trim()} data-testid="feedback-send">Send</Button>
      </SectionCard>
    </div>
  );
}
