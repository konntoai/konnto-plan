import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Send, ArrowLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { PersonAvatar, KonntoOrb } from "@/components/common";
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

  if (!data) return <div className="p-10 flex flex-col items-center gap-3 text-muted-foreground"><KonntoOrb size={48} state="thinking" /><span className="eyebrow">Loading chat</span></div>;
  const others = data.people.filter((p) => p.member_id !== me?.member_id);
  const title = data.thread.name || others.map((o) => o.name).join(", ");

  return (
    <div className="h-[calc(100dvh-56px-68px-env(safe-area-inset-bottom))] lg:h-[calc(100dvh-64px)] flex flex-col" data-testid="thread-page">
      <div className="flex items-center gap-3 px-3 sm:px-5 py-2.5 glass border-x-0 border-t-0">
        <Button size="icon" variant="ghost" className="rounded-full" onClick={() => navigate("/app/team")} aria-label="Back" data-testid="thread-back"><ArrowLeft className="h-5 w-5" /></Button>
        <div className="flex -space-x-2">{others.slice(0, 3).map((o) => <div key={o.member_id} className="ring-2 ring-background rounded-full"><PersonAvatar name={o.name} size={34} /></div>)}</div>
        <div className="min-w-0 flex-1">
          <div className="font-display font-bold truncate" data-testid="thread-title">{title}</div>
          <div className="text-xs text-muted-foreground truncate">{others.map((o) => `${o.name}${o.on_whatsapp ? " · on WhatsApp" : o.has_app ? " · app" : ""}`).join(" • ") || "Direct chat"}</div>
        </div>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="max-w-[760px] mx-auto px-4 py-5 space-y-4">
          {data.messages.map((m) => {
            const mine = m.sender_id === me?.member_id;
            return (
              <div key={m.msg_id} className={cn("flex items-end gap-2 animate-fade-up", mine && "flex-row-reverse")} data-testid="thread-message">
                {!mine && <PersonAvatar name={m.sender_name} size={30} />}
                <div className={cn("max-w-[80%] flex flex-col", mine ? "items-end" : "items-start")}>
                  {!mine && <div className="eyebrow text-muted-foreground mb-1 px-1">{m.sender_name}</div>}
                  <div className={cn("rounded-[20px] px-4 py-2.5 text-[15px] leading-relaxed whitespace-pre-wrap text-left", mine ? "bg-brand-gradient text-white rounded-tr-md shadow-[0_12px_30px_-16px_hsl(var(--glow-blue))]" : "glass rounded-tl-md")}>
                    {m.item?.title ? <><div className={cn("eyebrow mb-0.5", mine ? "text-white/80" : "text-primary")}>{m.kind === "request" ? "Request" : "Task"}</div>{m.item.title}{m.item.due_at ? <div className={cn("text-xs mt-1 font-mono", mine ? "text-white/75" : "text-muted-foreground")}>Due {fmtWhen(m.item.due_at)}</div> : null}</> : m.text}
                  </div>
                  <div className="font-mono text-[10px] tracking-wider text-muted-foreground mt-1 px-1">{fmtTime(m.created_at)}</div>
                </div>
              </div>
            );
          })}
          {data.messages.length === 0 && <div className="text-sm text-muted-foreground text-center py-10">Say hello — messages reach everyone wherever they prefer.</div>}
        </div>
      </div>
      <div className="px-3 sm:px-5 pb-3 pt-2">
        <div className="max-w-[760px] mx-auto rounded-[24px] glass-strong p-1.5 flex items-end gap-1 transition-[box-shadow,border-color] duration-200 focus-within:border-primary/50 focus-within:shadow-[0_0_0_4px_hsl(var(--primary)/0.10)]">
          <Textarea rows={1} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder="Message…" className="resize-none min-h-[44px] max-h-[140px] flex-1 border-0 bg-transparent px-3 py-2.5 hover:border-0 focus-visible:ring-0 focus-visible:border-0 text-[15px]" data-testid="thread-composer" />
          <Button size="icon" className="rounded-full shrink-0" onClick={send} disabled={sending || !text.trim()} aria-label="Send" data-testid="thread-send">{sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}</Button>
        </div>
      </div>
    </div>
  );
}
