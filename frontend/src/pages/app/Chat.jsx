import { useEffect, useRef } from "react";
import { Bell, AlertTriangle, Sparkles, UserCheck } from "lucide-react";
import { KonntoOrb } from "@/components/common";
import { useBrainChat } from "@/context/BrainChatContext";
import { useMe } from "@/context/MeContext";
import { UserBubble, AssistantBubble } from "@/components/brain/BrainMessages";
import { BrainComposer } from "@/components/brain/BrainComposer";
import { PersonaSelect } from "@/components/brain/PersonaSelect";
import { ResetConversation } from "@/components/brain/KBrainPanel";

const SUGGESTIONS = [
  { text: "What needs my attention today?", icon: Sparkles, label: "Briefing" },
  { text: "What is really urgent for today?", icon: AlertTriangle, label: "Priorities" },
  { text: "Remind me to call Ramesh tomorrow at 10am", icon: Bell, label: "Reminder" },
  { text: "I'm out tomorrow — ask Priya to manage, no payments without me", icon: UserCheck, label: "Handover" },
];

export default function ChatPage() {
  const { me } = useMe();
  const { messages, people, loading, send, sending, onCardAction } = useBrainChat();
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const firstName = (me?.member?.name || me?.user?.name || "there").split(" ")[0];

  return (
    <div className="relative h-[calc(100dvh-56px-68px-env(safe-area-inset-bottom))] lg:h-[calc(100dvh-64px)] flex flex-col" data-testid="chat-page">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-64 bg-grid opacity-70" aria-hidden />

      <div className="relative border-b border-border/60">
        <div className="max-w-[780px] mx-auto px-4 sm:px-6 py-2.5 flex items-center gap-3">
          <KonntoOrb size={28} state={sending ? "streaming" : "idle"} />
          <div className="min-w-0 flex-1">
            <div className="font-display font-bold text-sm leading-tight">K-BRAIN</div>
            <div className="eyebrow text-muted-foreground text-[10px] truncate">KONNTO intelligence layer</div>
          </div>
          <span className="hidden sm:inline text-xs text-muted-foreground">Talks like your</span>
          <PersonaSelect testid="chat-persona-select" />
        </div>
      </div>

      <div ref={scrollRef} className="relative flex-1 overflow-y-auto scrollbar-thin">
        <div className="max-w-[780px] mx-auto px-4 sm:px-6 py-6">
          {loading ? (
            <div className="flex flex-col items-center gap-4 py-16 text-muted-foreground"><KonntoOrb size={56} state="thinking" /><span className="eyebrow">Loading your conversation</span></div>
          ) : messages.length === 0 ? (
            <div className="pt-8 sm:pt-12 flex flex-col items-center text-center" data-testid="chat-empty-state">
              <KonntoOrb size={112} state="idle" ripple />
              <div className="eyebrow text-primary mt-8">K-BRAIN · online</div>
              <h2 className="mt-3 text-3xl sm:text-4xl font-display font-extrabold tracking-tight">Hi {firstName}. <span className="text-gradient">What should we look at?</span></h2>
              <p className="mt-3 text-muted-foreground max-w-md">I have your live work, pending approvals and signals from your team. Ask for a rundown, hand something over, or just tell me what happened.</p>
              <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-xl text-left">
                {SUGGESTIONS.map((s) => (
                  <button key={s.text} onClick={() => send(s.text)} className="group rounded-2xl surface surface-hover p-3.5 flex gap-3 items-start" data-testid="chat-suggestion-chip">
                    <span className="h-8 w-8 shrink-0 rounded-xl bg-accent text-primary grid place-items-center ring-1 ring-primary/15"><s.icon className="h-4 w-4" /></span>
                    <span className="min-w-0"><span className="eyebrow text-muted-foreground block">{s.label}</span><span className="text-sm font-medium leading-snug">{s.text}</span></span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((m) => (
                <div key={m.msg_id}>
                  {m.role === "user" ? <UserBubble msg={m} /> : <AssistantBubble msg={m} people={people} onCardAction={onCardAction} />}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="relative px-3 sm:px-6 pb-3 pt-2">
        <div className="max-w-[780px] mx-auto">
          <BrainComposer prefix="chat" />
          <div className="flex items-center justify-between pt-2 px-1">
            <span className="font-mono text-[10px] tracking-[0.14em] uppercase text-muted-foreground/80">Powered by K-BRAIN · KONNTO intelligence<span className="hidden sm:inline"> · Enter to send</span></span>
            <ResetConversation testid="chat-reset-button" />
          </div>
        </div>
      </div>
    </div>
  );
}
