import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Send, ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { PersonAvatar } from "@/components/common";
import { useApi } from "@/lib/api";
import { fmtTime, fmtWhen } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function ThreadPage() {
  const api = useApi();
  const navigate = useNavigate();
  const { threadId } = useParams();
  const [data, setData] = useState(null);
  const [me, setMe] = useState(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const [t, m] = await Promise.all([api.get(`/threads/${threadId}/messages`), api.get("/me")]);
      setData(t);
      setMe(m.member);
    } catch (e) { toast.error(e.message); navigate("/app/team"); }
  }, [api, threadId, navigate]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [data]);

  const send = async () => {
    if (!text.trim() || sending) return;
    setSending(true);
    try {
      await api.post(`/threads/${threadId}/messages`, { text });
      setText("");
      await load();
    } catch (e) { toast.error(e.message); } finally { setSending(false); }
  };

  if (!data) return <div className="p-8 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin inline" /> Loading…</div>;
  const others = data.people.filter((p) => p.member_id !== me?.member_id);
  const title = data.thread.name || others.map((o) => o.name).join(", ");

  return (
    <div className="h-[calc(100vh-56px)] lg:h-[calc(100vh-64px)] flex flex-col bg-background" data-testid="thread-page">
      <div className="flex items-center gap-3 px-3 py-2 border-b border-border bg-card">
        <Button size="icon" variant="ghost" onClick={() => navigate("/app/team")} aria-label="Back" data-testid="thread-back"><ArrowLeft className="h-5 w-5" /></Button>
        <div className="min-w-0 flex-1">
          <div className="font-semibold truncate" data-testid="thread-title">{title}</div>
          <div className="text-xs text-muted-foreground truncate">{others.map((o) => `${o.name}${o.on_whatsapp ? " · on WhatsApp" : o.has_app ? " · app" : ""}`).join(" • ") || "Direct chat"}</div>
        </div>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="max-w-[720px] mx-auto px-4 py-4 space-y-3">
          {data.messages.map((m) => {
            const mine = m.sender_id === me?.member_id;
            return (
              <div key={m.msg_id} className={cn("flex items-end gap-2", mine && "flex-row-reverse")} data-testid="thread-message">
                {!mine && <PersonAvatar name={m.sender_name} size={28} />}
                <div className={cn("max-w-[80%]", mine && "text-right")}>
                  {!mine && <div className="text-[11px] text-muted-foreground mb-0.5 px-1">{m.sender_name}</div>}
                  <div className={cn("rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap inline-block text-left", mine ? "bg-primary/10 border border-primary/15 rounded-tr-md" : "bg-card border border-border rounded-tl-md")}>
                    {m.item?.title ? <><div className="text-[11px] font-semibold uppercase tracking-wide text-primary">{m.kind === "request" ? "Request" : "Task"}</div>{m.item.title}{m.item.due_at ? <div className="text-xs text-muted-foreground mt-1">Due {fmtWhen(m.item.due_at)}</div> : null}</> : m.text}
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-1 px-1">{fmtTime(m.created_at)}</div>
                </div>
              </div>
            );
          })}
          {data.messages.length === 0 && <div className="text-sm text-muted-foreground text-center py-8">Say hello — messages reach everyone wherever they prefer.</div>}
        </div>
      </div>
      <div className="border-t border-border bg-background/95 backdrop-blur">
        <div className="max-w-[720px] mx-auto px-3 py-2 flex items-end gap-2">
          <Textarea rows={1} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder="Message…" className="resize-none min-h-[44px] max-h-[140px] rounded-xl" data-testid="thread-composer" />
          <Button size="icon" onClick={send} disabled={sending || !text.trim()} aria-label="Send" data-testid="thread-send">{sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}</Button>
        </div>
      </div>
    </div>
  );
}
