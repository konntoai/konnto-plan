import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ChevronDown, ChevronUp, Maximize2, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { KonntoOrb } from "@/components/common";
import { useBrainChat } from "@/context/BrainChatContext";
import { useMe } from "@/context/MeContext";
import { UserBubble, AssistantBubble } from "@/components/brain/BrainMessages";
import { BrainComposer } from "@/components/brain/BrainComposer";
import { PersonaSelect } from "@/components/brain/PersonaSelect";
import { cn } from "@/lib/utils";

export const QUICK_ASKS = [
  "What needs my attention today?",
  "What is really urgent for today?",
  "Status",
  "Who is behind on their work?",
];

export function ResetConversation({ testid = "kbrain-reset-button", className = "" }) {
  const { reset, messages } = useBrainChat();
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <button disabled={!messages.length} className={cn("font-mono text-[10px] tracking-[0.14em] uppercase text-muted-foreground hover:text-foreground disabled:opacity-40 disabled:pointer-events-none inline-flex items-center gap-1 transition-colors", className)} data-testid={testid}>
          <RotateCcw className="h-3 w-3" /> Reset
        </button>
      </AlertDialogTrigger>
      <AlertDialogContent data-testid="kbrain-reset-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle>Start a fresh conversation?</AlertDialogTitle>
          <AlertDialogDescription>K-BRAIN clears this chat window. Your work, approvals, team and everything K-BRAIN remembers about the business stay exactly as they are.</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel data-testid="kbrain-reset-cancel">Keep chatting</AlertDialogCancel>
          <AlertDialogAction onClick={reset} data-testid="kbrain-reset-confirm">Start fresh</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export function KBrainGreeting({ firstName, onAsk, compact = false }) {
  return (
    <div className="animate-fade-up" data-testid="kbrain-greeting">
      <div className={cn("k-seam rounded-[20px] rounded-tl-md glass pl-5 pr-4 py-3 leading-relaxed", compact ? "text-[14px]" : "text-[15px]")}>
        I'm online{firstName ? `, ${firstName}` : ""}. I have your live work, pending approvals and signals from your team. Tell me what to look at — or just say ‘status’ for the rundown.
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {QUICK_ASKS.map((q) => (
          <button key={q} onClick={() => onAsk(q)} className="rounded-full border border-border bg-[hsl(var(--surface-2))] px-3 py-1.5 text-xs font-medium hover:border-primary/40 hover:text-primary transition-colors" data-testid="kbrain-quick-ask">
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

/** Floating K-BRAIN panel, available on every app page except the full Chat page. */
export function KBrainPanel() {
  const location = useLocation();
  const navigate = useNavigate();
  const { me } = useMe();
  const { messages, people, loading, send, sending, onCardAction, pressButton } = useBrainChat();
  const [open, setOpen] = useState(false);
  const scrollRef = useRef(null);
  const firstName = (me?.member?.name || me?.user?.name || "").split(" ")[0];
  const hidden = location.pathname === "/app/chat";

  useEffect(() => {
    if (open && scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === "Escape" && !document.querySelector('[role="dialog"]:not([data-testid="kbrain-panel"]),[role="alertdialog"],[role="listbox"]')) setOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (hidden) return null;
  const recent = messages.slice(-40);
  const ask = (q) => { setOpen(true); send(q); };

  if (!open) {
    return (
      <div className="fixed z-50 inset-x-3 bottom-[calc(76px+env(safe-area-inset-bottom))] lg:bottom-5 lg:inset-x-auto lg:left-[calc(136px_+_50vw)] lg:-translate-x-1/2 lg:w-[min(760px,calc(100vw_-_320px))]" data-testid="kbrain-dock">
        <div className="rounded-[22px] glass-strong p-1.5 flex items-center gap-1 shadow-[0_24px_60px_-20px_hsl(var(--glow-blue))]">
          <Button variant="ghost" size="icon" className="shrink-0 rounded-full" onClick={() => setOpen(true)} aria-label="Open K-BRAIN" data-testid="kbrain-open-button">
            {sending ? <KonntoOrb size={22} state="thinking" /> : <ChevronUp className="h-5 w-5" />}
          </Button>
          <div className="flex-1 min-w-0">
            <BrainComposer prefix="kbrain" compact onFocus={() => setOpen(true)} onSent={() => setOpen(true)} />
          </div>
          <Button variant="ghost" size="icon" className="shrink-0 rounded-full hidden sm:inline-flex" onClick={() => navigate("/app/chat")} aria-label="Open full chat" data-testid="kbrain-dock-expand">
            <Maximize2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="fixed inset-0 z-50 bg-[hsl(228_80%_4%/0.35)] backdrop-blur-[2px] animate-in fade-in-0 duration-200" onClick={() => setOpen(false)} aria-hidden data-testid="kbrain-backdrop" />
      <section
        role="dialog"
        aria-label="K-BRAIN"
        className="fixed z-50 flex flex-col overflow-hidden rounded-3xl glass-strong shadow-[0_40px_120px_-30px_hsl(var(--glow-blue)),0_0_0_1px_hsl(var(--primary)/0.12)] animate-in fade-in-0 slide-in-from-bottom-4 duration-200
                   inset-x-2 top-16 bottom-[calc(76px+env(safe-area-inset-bottom))]
                   lg:inset-x-auto lg:top-auto lg:bottom-5 lg:left-[calc(136px_+_50vw)] lg:-translate-x-1/2 lg:w-[min(780px,calc(100vw_-_320px))] lg:h-[min(78vh,720px)]"
        data-testid="kbrain-panel"
      >
        <header className="flex items-center gap-3 px-4 py-3 border-b border-border/70">
          <KonntoOrb size={34} state={sending ? "streaming" : "idle"} />
          <div className="min-w-0 flex-1">
            <div className="font-display font-bold text-[15px] leading-tight" data-testid="kbrain-panel-title">K-BRAIN</div>
            <div className="eyebrow text-muted-foreground text-[10px] truncate">KONNTO intelligence layer</div>
          </div>
          <PersonaSelect testid="kbrain-panel-persona" className="hidden sm:flex" />
          <Button variant="ghost" size="icon" className="rounded-full h-9 w-9" onClick={() => navigate("/app/chat")} aria-label="Open full chat" data-testid="kbrain-panel-expand"><Maximize2 className="h-4 w-4" /></Button>
          <Button variant="ghost" size="icon" className="rounded-full h-9 w-9" onClick={() => setOpen(false)} aria-label="Minimise" data-testid="kbrain-panel-minimize"><ChevronDown className="h-5 w-5" /></Button>
        </header>
        <div className="sm:hidden px-4 pt-2"><PersonaSelect testid="kbrain-panel-persona-mobile" /></div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin px-4 py-4 space-y-4" data-testid="kbrain-panel-messages">
          {loading ? (
            <div className="flex items-center gap-2 text-muted-foreground text-sm"><KonntoOrb size={20} state="thinking" /> Loading…</div>
          ) : recent.length === 0 ? (
            <KBrainGreeting firstName={firstName} onAsk={ask} compact />
          ) : (
            recent.map((m) => (
              <div key={m.msg_id}>
                {m.role === "user" ? <UserBubble msg={m} compact /> : <AssistantBubble msg={m} people={people} onCardAction={onCardAction} onButton={pressButton} compact />}
              </div>
            ))
          )}
        </div>

        <footer className="px-3 pb-2 pt-2 border-t border-border/70">
          <BrainComposer prefix="kbrain-panel" compact autoFocus />
          <div className="flex items-center justify-between px-1 pt-2">
            <span className="font-mono text-[10px] tracking-[0.14em] uppercase text-muted-foreground/80">Powered by K-BRAIN · KONNTO intelligence</span>
            <ResetConversation testid="kbrain-panel-reset" />
          </div>
        </footer>
      </section>
    </>
  );
}

export default KBrainPanel;
