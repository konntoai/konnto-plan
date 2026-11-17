import { useState } from "react";
import { Save, Pencil, X, Undo2, Check, UserPlus, FileText, Scale, BookMarked, MessageCircle, ShieldCheck, Link as LinkIcon, Copy, Bell, Handshake, StickyNote, CalendarClock, User, IndianRupee, Lock, UserCheck, Sparkles, PhoneForwarded } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TonePill } from "@/components/common";
import { fmtWhen, money, toLocalInput, fromLocalInput, KIND_LABEL } from "@/lib/format";
import { cn } from "@/lib/utils";

const ICONS = {
  proposal: FileText,
  invite: UserPlus,
  approval: ShieldCheck,
  access_request: ShieldCheck,
  rule: BookMarked,
  decision: Scale,
  message: MessageCircle,
  update: Check,
  fact: BookMarked,
  business: BookMarked,
  doc: FileText,
  persona: Sparkles,
  handover: UserCheck,
};

const KIND_ICON = { task: Check, promise: Handshake, reminder: Bell, decision: Scale, note: StickyNote };

const copy = (text) => {
  navigator.clipboard.writeText(text);
  toast.success("Copied");
};

const Meta = ({ icon: Icon, label, value }) => (
  <span className="inline-flex items-center gap-1.5 rounded-lg bg-[hsl(var(--surface-2))] border border-border px-2 py-1 text-xs">
    <Icon className="h-3.5 w-3.5 text-primary" />
    <span className="text-muted-foreground">{label}</span>
    <span className="font-semibold text-foreground">{value}</span>
  </span>
);

function ProposalCard({ card, people, onSave, onSkip, onUndo }) {
  const d = card.data || {};
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ title: d.title, details: d.details, assignee_id: d.assignee_id, due_at: d.due_at, remind_at: d.remind_at, kind: d.kind });
  const saved = card.status === "saved";
  const skipped = card.status === "skipped";
  const pending = !saved && !skipped;
  const KindIcon = KIND_ICON[d.kind] || FileText;
  return (
    <div className={cn("k-shimmer", !pending && "k-shimmer--calm opacity-95")} data-testid={`chat-card-proposal-${card.card_id}`}>
      <div className={cn("relative rounded-[inherit] bg-card/95 p-4", skipped && "opacity-60")}>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 eyebrow text-primary">
            <span className="h-6 w-6 rounded-lg bg-accent grid place-items-center"><KindIcon className="h-3.5 w-3.5" /></span>
            {KIND_LABEL[d.kind] || "Task"} · ready to save
          </div>
          {saved && <TonePill tone="done" icon={Check}>Saved</TonePill>}
          {skipped && <TonePill tone="stuck" icon={X}>Skipped</TonePill>}
        </div>
        <div className="mt-2.5 font-display font-bold text-[16px] leading-snug" data-testid="proposal-title">{d.title}</div>
        {d.details && <div className="mt-1 text-sm text-muted-foreground leading-relaxed">{d.details}</div>}
        <div className="mt-3 flex flex-wrap gap-1.5">
          {d.assignee_name && <Meta icon={User} label="For" value={d.assignee_name} />}
          {d.counterparty && <Meta icon={Handshake} label="With" value={d.counterparty} />}
          {d.due_at && <Meta icon={CalendarClock} label="Due" value={fmtWhen(d.due_at)} />}
          {d.remind_at && <Meta icon={Bell} label="Remind" value={fmtWhen(d.remind_at)} />}
          {d.amount != null && <Meta icon={IndianRupee} label="Amount" value={money(d.amount, d.currency)} />}
          {d.private && <Meta icon={Lock} label="" value="Private" />}
        </div>
        {pending && (
          <div className="mt-4 grid grid-cols-3 gap-2">
            <Button size="sm" onClick={() => onSave?.(card.card_id, null)} data-testid={`proposal-save-${card.card_id}`} className="h-10"><Save className="h-4 w-4" /> Save</Button>
            <Button size="sm" variant="outline" onClick={() => setOpen(true)} data-testid={`proposal-edit-${card.card_id}`} className="h-10"><Pencil className="h-4 w-4" /> Edit</Button>
            <Button size="sm" variant="ghost" onClick={() => onSkip?.(card.card_id)} data-testid={`proposal-skip-${card.card_id}`} className="h-10 border border-transparent hover:border-border"><X className="h-4 w-4" /> Skip</Button>
          </div>
        )}
        {saved && (
          <div className="mt-3 flex items-center gap-2 text-sm text-status-done">
            <Check className="h-4 w-4" /> Saved to Work.
            <button className="ml-1 inline-flex items-center gap-1 text-primary font-semibold hover:underline" data-testid={`proposal-undo-${card.card_id}`} onClick={() => onUndo?.(card.card_id)}>
              <Undo2 className="h-3.5 w-3.5" /> Undo
            </button>
          </div>
        )}
        {skipped && <div className="mt-3 text-sm text-muted-foreground">Skipped — nothing was saved.</div>}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="proposal-edit-dialog">
          <DialogHeader><DialogTitle>Edit before saving</DialogTitle><DialogDescription>Fix anything KONNTO got slightly wrong.</DialogDescription></DialogHeader>
          <div className="space-y-3">
            <label className="block text-sm font-medium">Title<Input className="mt-1.5" value={form.title || ""} onChange={(e) => setForm({ ...form, title: e.target.value })} data-testid="proposal-edit-title" /></label>
            <label className="block text-sm font-medium">Details<Textarea className="mt-1.5" rows={3} value={form.details || ""} onChange={(e) => setForm({ ...form, details: e.target.value })} data-testid="proposal-edit-details" /></label>
            <label className="block text-sm font-medium">Kind
              <Select value={form.kind} onValueChange={(v) => setForm({ ...form, kind: v })}>
                <SelectTrigger className="mt-1.5" data-testid="proposal-edit-kind"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {["task", "promise", "reminder", "decision", "note"].map((k) => <SelectItem key={k} value={k}>{KIND_LABEL[k]}</SelectItem>)}
                </SelectContent>
              </Select>
            </label>
            <label className="block text-sm font-medium">Assignee
              <Select value={form.assignee_id || ""} onValueChange={(v) => setForm({ ...form, assignee_id: v })}>
                <SelectTrigger className="mt-1.5" data-testid="proposal-edit-assignee"><SelectValue placeholder="Pick someone" /></SelectTrigger>
                <SelectContent>{(people || []).map((p) => <SelectItem key={p.member_id} value={p.member_id}>{p.name}</SelectItem>)}</SelectContent>
              </Select>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="block text-sm font-medium">Due<Input type="datetime-local" className="mt-1.5" value={toLocalInput(form.due_at)} onChange={(e) => setForm({ ...form, due_at: fromLocalInput(e.target.value) })} data-testid="proposal-edit-due" /></label>
              <label className="block text-sm font-medium">Remind<Input type="datetime-local" className="mt-1.5" value={toLocalInput(form.remind_at)} onChange={(e) => setForm({ ...form, remind_at: fromLocalInput(e.target.value) })} data-testid="proposal-edit-remind" /></label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={() => { setOpen(false); onSave?.(card.card_id, form); }} data-testid="proposal-edit-save"><Save className="h-4 w-4" /> Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function InviteCard({ card, onAction }) {
  const d = card.data || {};
  return (
    <div className="k-shimmer k-shimmer--calm" data-testid={`chat-card-invite-${card.card_id}`}>
      <div className="relative rounded-[inherit] bg-card/95 p-4">
        <div className="flex items-center gap-2 eyebrow text-primary"><span className="h-6 w-6 rounded-lg bg-accent grid place-items-center"><UserPlus className="h-3.5 w-3.5" /></span> Invite ready</div>
        <div className="mt-2.5 font-display font-bold text-[16px]">{d.name}</div>
        {d.job && <div className="text-sm text-muted-foreground">{d.job}</div>}
        {d.access_reason && <div className="mt-1.5 text-xs text-muted-foreground">{d.access_reason}</div>}
        {card.status === "created" && <div className="mt-1"><UndoLink card={card} onAction={onAction} /></div>}
        {d.invite_url && (
          <div className="mt-3 space-y-2">
            <div className="flex gap-2">
              <Input value={d.invite_url} readOnly data-testid="invite-url-input" className="text-xs font-mono" />
              <Button size="icon" variant="outline" onClick={() => copy(d.invite_url)} aria-label="Copy" data-testid="invite-copy-url"><Copy className="h-4 w-4" /></Button>
            </div>
            {d.share_url && <Button asChild size="sm" variant="outline" data-testid="invite-share-wa"><a href={d.share_url} target="_blank" rel="noreferrer"><LinkIcon className="h-4 w-4" /> Share on WhatsApp</a></Button>}
          </div>
        )}
      </div>
    </div>
  );
}

function SimpleCard({ card, label, children }) {
  const Icon = ICONS[card.type] || BookMarked;
  return (
    <div className="rounded-2xl surface p-3.5 flex gap-3" data-testid={`chat-card-${card.type}-${card.card_id}`}>
      <span className="h-9 w-9 shrink-0 rounded-xl bg-accent text-primary grid place-items-center ring-1 ring-primary/15"><Icon className="h-4 w-4" /></span>
      <div className="min-w-0">
        <div className="eyebrow text-primary">{label}</div>
        <div className="mt-1 text-sm leading-relaxed">{children}</div>
      </div>
    </div>
  );
}

const DRAFT_LABEL = {
  message: "Message", rule: "Business rule", fact: "K-MEMORY fact", decision: "Approval decision",
  update: "Status change", business: "Business profile", invite: "Invite",
};

function DraftBody({ card }) {
  const d = card.data || {};
  switch (card.type) {
    case "message":
      return (<><div className="text-xs text-muted-foreground">To <span className="font-semibold text-foreground">{d.to_name}</span></div>
        <blockquote className="mt-1.5 rounded-xl border-l-2 border-primary/50 bg-[hsl(var(--surface-2))] px-3 py-2 text-sm whitespace-pre-wrap" data-testid="draft-message-text">{d.text}</blockquote></>);
    case "rule":
      return (<><div className="text-sm font-medium">{d.text}</div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          <Meta icon={BookMarked} label="" value={d.duration === "temporary" ? "Temporary" : "Permanent"} />
          <Meta icon={User} label="Applies to" value={d.scope_level === "company" || !d.scope_level ? "Whole company" : `${d.scope_level}${d.applies_to ? `: ${d.applies_to}` : ""}`} />
          {d.until && <Meta icon={CalendarClock} label="Until" value={fmtWhen(d.until)} />}
        </div></>);
    case "fact":
      return (<><div className="text-sm font-medium">{d.text}</div>{d.category && <div className="mt-1.5 eyebrow text-muted-foreground">{d.category}</div>}</>);
    case "decision":
      return (<><div className="text-sm font-medium">{d.summary}</div>
        {d.amount != null && <div className="mt-2"><Meta icon={IndianRupee} label="Amount" value={money(d.amount, d.currency)} /></div>}</>);
    case "update":
      return <div className="text-sm">“{d.title}” → <span className="font-semibold">{d.new_status}</span>{d.reason ? ` — ${d.reason}` : ""}</div>;
    case "business":
      return <div className="text-sm">{Object.entries(d).map(([k, v]) => <div key={k}><span className="text-muted-foreground">{k}:</span> <span className="font-semibold">{String(v)}</span></div>)}</div>;
    case "invite":
      return <div className="text-sm"><span className="font-semibold">{d.name}</span>{d.job ? ` — ${d.job}` : ""} <span className="text-muted-foreground">({d.member_type === "partner" ? "partner" : "team"})</span></div>;
    default:
      return null;
  }
}

function DraftCard({ card, onAction }) {
  const [busy, setBusy] = useState(false);
  const Icon = ICONS[card.type] || BookMarked;
  const dismissed = card.status === "dismissed";
  const run = async (op) => { setBusy(true); try { await onAction?.(card.card_id, op); } finally { setBusy(false); } };
  return (
    <div className={cn("rounded-2xl border p-4", dismissed ? "border-border bg-card/70 opacity-60" : "border-primary/35 bg-primary/[0.05] shadow-[0_18px_50px_-30px_hsl(var(--glow-blue))]")} data-testid={`chat-card-draft-${card.type}-${card.card_id}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="eyebrow text-primary flex items-center gap-2"><Icon className="h-3.5 w-3.5" /> K-BRAIN drafted · {DRAFT_LABEL[card.type] || card.type}</div>
        {dismissed ? <TonePill tone="stuck" icon={X}>Dismissed</TonePill> : <TonePill tone="pending">Waiting for you</TonePill>}
      </div>
      <div className="mt-2.5"><DraftBody card={card} /></div>
      {!dismissed ? (
        <div className="mt-3.5 flex flex-wrap gap-2">
          <Button size="sm" disabled={busy} onClick={() => run("confirm")} className="h-10 rounded-full" data-testid={`draft-confirm-${card.card_id}`}><Check className="h-4 w-4" /> Confirm</Button>
          <Button size="sm" variant="outline" disabled={busy} onClick={() => run("dismiss")} className="h-10 rounded-full" data-testid={`draft-dismiss-${card.card_id}`}><X className="h-4 w-4" /> Dismiss</Button>
        </div>
      ) : <div className="mt-2 text-sm text-muted-foreground">Nothing was done.</div>}
    </div>
  );
}

const UndoLink = ({ card, onAction }) => (
  <button className="ml-2 inline-flex items-center gap-1 text-primary font-semibold text-xs hover:underline" onClick={() => onAction?.(card.card_id, "undo")} data-testid={`card-undo-${card.card_id}`}>
    <Undo2 className="h-3 w-3" /> Undo
  </button>
);

function HandoverCard({ card, onAction }) {
  const d = card.data || {};
  const [busy, setBusy] = useState(false);
  const pending = card.status === "pending";
  const confirmed = card.status === "confirmed";
  const run = async (op) => {
    setBusy(true);
    try { await onAction?.(card.card_id, op); } finally { setBusy(false); }
  };
  return (
    <div
      className={cn(
        "rounded-2xl border p-4 transition-[opacity,border-color] duration-200",
        pending ? "border-status-due/45 bg-status-due/[0.07] shadow-[0_18px_50px_-28px_hsl(var(--status-due)/0.7)]" : "border-border bg-card/80",
        card.status === "dismissed" && "opacity-60"
      )}
      data-testid={`chat-card-handover-${card.card_id}`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="eyebrow text-status-due flex items-center gap-2">
          <UserCheck className="h-3.5 w-3.5" /> K-BRAIN proposes · handover
        </div>
        {confirmed && <TonePill tone="done" icon={Check} testid="handover-status-confirmed">In effect</TonePill>}
        {card.status === "dismissed" && <TonePill tone="stuck" icon={X} testid="handover-status-dismissed">Dismissed</TonePill>}
        {card.status === "ended" && <TonePill tone="stuck" icon={Undo2} testid="handover-status-ended">Ended</TonePill>}
      </div>
      <div className="mt-2 font-display font-bold text-[15px] leading-snug" data-testid="handover-title">
        {d.to_name} manages operations{d.until ? ` until ${fmtWhen(d.until)}` : " today"}
      </div>
      {d.to_job && <div className="text-xs text-muted-foreground">{d.to_job}</div>}

      {d.message && (
        <blockquote className="mt-3 rounded-xl border-l-2 border-status-due/60 bg-[hsl(var(--surface-2))] px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap" data-testid="handover-message">
          {d.message}
        </blockquote>
      )}

      {d.restrictions?.length > 0 && (
        <ul className="mt-3 space-y-1.5" data-testid="handover-restrictions">
          {d.restrictions.map((r, i) => (
            <li key={i} className="flex items-start gap-2 text-sm"><Lock className="h-3.5 w-3.5 mt-0.5 text-status-due shrink-0" /><span>{r}</span></li>
          ))}
        </ul>
      )}
      {d.escalation && (
        <div className="mt-2 flex items-start gap-2 text-sm text-muted-foreground"><PhoneForwarded className="h-3.5 w-3.5 mt-0.5 shrink-0" /><span>{d.escalation}</span></div>
      )}
      {d.log_text && (
        <div className="mt-3 font-mono text-[11px] leading-relaxed text-muted-foreground line-clamp-4" data-testid="handover-log">{d.log_text}</div>
      )}

      {pending && (
        <div className="mt-4 flex flex-wrap gap-2">
          <Button size="sm" disabled={busy} onClick={() => run("confirm")} className="h-10 rounded-full bg-status-due text-[hsl(30_40%_8%)] hover:bg-status-due/90 font-semibold" data-testid={`handover-confirm-${card.card_id}`}>
            <Check className="h-4 w-4" /> Confirm
          </Button>
          <Button size="sm" variant="outline" disabled={busy} onClick={() => run("dismiss")} className="h-10 rounded-full" data-testid={`handover-dismiss-${card.card_id}`}>
            <X className="h-4 w-4" /> Dismiss
          </Button>
        </div>
      )}
      {confirmed && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-status-done">
          <Check className="h-4 w-4" /> Sent to {d.to_name}. The restriction is active and logged.
          <button className="inline-flex items-center gap-1 text-primary font-semibold hover:underline" data-testid={`handover-end-${card.card_id}`} onClick={() => run("undo")}>
            <Undo2 className="h-3.5 w-3.5" /> End handover now
          </button>
        </div>
      )}
      {card.status === "dismissed" && <div className="mt-3 text-sm text-muted-foreground">Nothing was sent.</div>}
    </div>
  );
}

export function BrainCard({ card, people, onAction }) {
  const t = card.type;
  if (card.status === "draft" || (card.status === "dismissed" && DRAFT_LABEL[t])) return <DraftCard card={card} onAction={onAction} />;
  if (t === "proposal") return <ProposalCard card={card} people={people} onSave={(id, edits) => onAction?.(id, "save", edits)} onSkip={(id) => onAction?.(id, "skip")} onUndo={(id) => onAction?.(id, "undo")} />;
  if (t === "invite" && card.status === "undone") return <SimpleCard card={card} label="Invite cancelled">{card.data?.name}</SimpleCard>;
  if (t === "invite") return <InviteCard card={card} onAction={onAction} />;
  if (t === "approval") {
    const d = card.data || {};
    return <SimpleCard card={card} label={card.status === "allowed_by_rule" ? "Approved by rule" : "Sent for approval"}>{d.title}{d.rule_text ? ` — ${d.rule_text}` : ""}</SimpleCard>;
  }
  if (t === "access_request") return <SimpleCard card={card} label="Access request sent">We asked the owner to grant: <span className="font-semibold text-foreground">{card.data?.label}</span>.</SimpleCard>;
  const undone = card.status === "undone";
  if (t === "rule") return <SimpleCard card={card} label={undone ? "Rule removed" : "Rule saved"}>{card.data?.text}{!undone && <UndoLink card={card} onAction={onAction} />}</SimpleCard>;
  if (t === "fact") return <SimpleCard card={card} label={undone ? "Forgotten" : "Saved to K-MEMORY"}>{card.data?.text}{!undone && <UndoLink card={card} onAction={onAction} />}</SimpleCard>;
  if (t === "decision") return <SimpleCard card={card} label={undone ? "Decision undone" : "Decision applied"}>{card.data?.summary}{!undone && <UndoLink card={card} onAction={onAction} />}</SimpleCard>;
  if (t === "message") {
    const del = (card.data?.deliveries || []).map((x) => `In app: ${x.app ? "delivered" : "waits until they join"} · WhatsApp: ${x.whatsapp || "not sent"}`).join(" | ");
    return <SimpleCard card={card} label={`Sent to ${card.data?.to_name}`}>“{card.data?.text}”{del && <div className="mt-1 font-mono text-[10px] text-muted-foreground" data-testid="message-delivery-status">{del}</div>}</SimpleCard>;
  }
  if (t === "business") return <SimpleCard card={card} label="Business profile updated">{Object.entries(card.data || {}).filter(([k]) => k !== "owner_user_id").map(([k, v]) => <div key={k}><span className="text-muted-foreground">{k}:</span> <span className="font-semibold">{String(v)}</span></div>)}</SimpleCard>;
  if (t === "update") return <SimpleCard card={card} label={undone ? "Change undone" : "Work item updated"}>“{card.data?.title}” → <span className="font-semibold">{card.data?.new_status}</span>{!undone && <UndoLink card={card} onAction={onAction} />}</SimpleCard>;
  if (t === "handover") return <HandoverCard card={card} onAction={onAction} />;
  if (t === "persona") return <SimpleCard card={card} label="Conversation style">K-BRAIN now talks like your <span className="font-semibold">{card.data?.label}</span>. Change it any time from the top of the chat.</SimpleCard>;
  if (t === "doc") return <SimpleCard card={card} label="Document saved">{card.data?.filename}{card.data?.summary ? ` — ${card.data.summary}` : ""}</SimpleCard>;
  return null;
}

export default BrainCard;
