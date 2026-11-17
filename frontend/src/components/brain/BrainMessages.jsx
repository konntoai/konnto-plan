import { Link } from "react-router-dom";
import { useState } from "react";
import { FileText, CheckSquare, BookOpen, MessageSquare, ShieldCheck, FolderKanban, Check, ArrowUpRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { KonntoOrb } from "@/components/common";
import { BrainMarkdown } from "@/components/brain/BrainMarkdown";
import { BrainCard } from "@/components/cards/BrainCard";
import { fmtTime } from "@/lib/format";
import { cn } from "@/lib/utils";

export const UserBubble = ({ msg, compact = false }) => (
  <div className={cn("ml-auto flex flex-col items-end animate-fade-up", compact ? "max-w-[86%]" : "max-w-[88%] sm:max-w-[78%]")} data-testid="chat-user-msg">
    <div className={cn(
      "rounded-[20px] rounded-tr-md px-4 py-2.5 leading-relaxed whitespace-pre-wrap text-left",
      compact
        ? "bg-primary/15 border border-primary/30 text-foreground text-[14px]"
        : "bg-brand-gradient text-white text-[15px] shadow-[0_14px_36px_-16px_hsl(var(--glow-blue))]"
    )}>{msg.text || "…"}</div>
    {msg.attachments?.length ? (
      <div className="mt-1.5 flex flex-wrap gap-1.5 justify-end">
        {msg.attachments.map((a, i) => (
          <span key={i} className="rounded-full glass px-2.5 py-1 text-xs text-muted-foreground">
            {a.type === "audio" ? "Voice" : a.type === "image" ? "Photo" : "Doc"}{a.filename ? `: ${a.filename}` : ""}
          </span>
        ))}
      </div>
    ) : null}
    {!compact && <div className="font-mono text-[10px] text-muted-foreground mt-1.5 tracking-wider">{fmtTime(msg.created_at) || "now"}</div>}
  </div>
);

const SRC_ICON = { work: CheckSquare, document: FileText, fact: BookOpen, chat: MessageSquare, approval: ShieldCheck, project: FolderKanban };

const Sources = ({ items }) => (
  <div className="mt-2 flex flex-wrap gap-1.5" data-testid="chat-sources">
    {items.map((c) => {
      const Icon = SRC_ICON[c.type] || BookOpen;
      return (
        <Link key={`${c.type}-${c.id}`} to={c.link || "#"} className="inline-flex max-w-[240px] items-center gap-1.5 rounded-full border border-border bg-[hsl(var(--surface-2))] px-2.5 py-1 text-[11px] text-muted-foreground hover:text-foreground hover:border-primary/40 transition-colors" data-testid="chat-source-chip">
          <span className="font-mono text-primary">{c.n}</span>
          <Icon className="h-3 w-3 shrink-0" />
          <span className="truncate">{c.title}</span>
        </Link>
      );
    })}
  </div>
);

const NoticeButtons = ({ msg, onPress }) => {
  const [busy, setBusy] = useState(null);
  const used = msg.buttons_used;
  if (used) {
    const label = msg.buttons_used_label || (msg.buttons || []).find((b) => b.id === used)?.label || "Answered";
    return (
      <div className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-border bg-[hsl(var(--surface-2))] px-3 py-1 text-xs text-muted-foreground" data-testid="notice-buttons-used">
        <Check className="h-3.5 w-3.5 text-primary" /> You chose: {label}
      </div>
    );
  }
  return (
    <div className="mt-2 flex flex-wrap gap-2" data-testid="notice-buttons">
      {msg.buttons.map((b, i) => (
        <Button
          key={b.id}
          size="sm"
          variant={i === 0 ? "default" : "outline"}
          disabled={!!busy || !onPress}
          onClick={async () => { setBusy(b.id); await onPress(msg, b); setBusy(null); }}
          className="h-9 rounded-full px-4"
          data-testid={`notice-btn-${b.id.split(":")[0]}`}
        >
          {busy === b.id && <Loader2 className="h-3.5 w-3.5 animate-spin" />}{b.label}
        </Button>
      ))}
    </div>
  );
};

export const AssistantBubble = ({ msg, people, onCardAction, onButton, compact = false }) => {
  const cards = msg.cards || [];
  const text = msg.text || "";
  const live = !!msg.streaming;
  const isBrief = msg.kind === "brief";
  return (
    <div className={cn("animate-fade-up", compact ? "max-w-full" : "max-w-[94%] sm:max-w-[86%]")} data-testid="chat-assistant-msg">
      <div className="flex items-start gap-3">
        {!compact && <KonntoOrb size={34} state={live ? "streaming" : "static"} className="mt-0.5" />}
        <div className="flex-1 min-w-0">
          {!compact && (
            <div className="eyebrow text-primary mb-1.5 flex items-center gap-2">
              K-BRAIN{isBrief && <span className="text-muted-foreground">· morning brief</span>}
              {live && <span className="text-muted-foreground normal-case tracking-normal font-sans text-[11px]">thinking…</span>}
            </div>
          )}
          {text ? (
            <div
              className={cn(
                "k-seam rounded-[20px] rounded-tl-md glass pl-5 pr-4 py-3 leading-relaxed",
                compact ? "text-[14px]" : "text-[15px] shadow-[0_14px_40px_-24px_hsl(var(--glass-shadow))]",
                live && "k-seam--live"
              )}
              data-testid="chat-assistant-text"
            >
              <BrainMarkdown text={text} />
              {live && <span className="cursor-blink" />}
            </div>
          ) : live ? (
            <div className="inline-flex items-center gap-2 text-muted-foreground text-sm py-1" data-testid="kbrain-thinking">
              <KonntoOrb size={18} state="thinking" />
              <span className="font-mono text-[11px] tracking-wider">K-BRAIN…</span>
            </div>
          ) : null}
          {!live && msg.citations?.length > 0 && <Sources items={msg.citations} />}
          {!live && msg.buttons?.length > 0 && <NoticeButtons msg={msg} onPress={onButton} />}
          {!live && msg.link_path && !msg.buttons?.length && (
            <Link to={msg.link_path} className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline" data-testid="notice-open-link">
              Open <ArrowUpRight className="h-3 w-3" />
            </Link>
          )}
          {cards.length > 0 && (
            <div className="mt-2.5 space-y-2.5">
              {cards.map((c) => <BrainCard key={c.card_id} card={c} people={people} onAction={onCardAction} />)}
            </div>
          )}
          {!compact && <div className="font-mono text-[10px] text-muted-foreground mt-1.5 tracking-wider">{fmtTime(msg.created_at) || "now"}</div>}
        </div>
      </div>
    </div>
  );
};
