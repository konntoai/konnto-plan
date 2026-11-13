import { useState } from "react";
import { Save, Pencil, X, Undo2, Check, UserPlus, FileText, Scale, BookMarked, MessageCircle, ShieldCheck, Link as LinkIcon, Copy } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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
};

const copy = (text) => {
  navigator.clipboard.writeText(text);
  toast.success("Copied");
};

function ProposalCard({ card, people, onSave, onSkip, onUndo }) {
  const d = card.data || {};
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ title: d.title, details: d.details, assignee_id: d.assignee_id, due_at: d.due_at, remind_at: d.remind_at, kind: d.kind });
  const saved = card.status === "saved";
  const skipped = card.status === "skipped";
  return (
    <div className="rounded-2xl border border-border bg-card p-3" data-testid={`chat-card-proposal-${card.card_id}`}>
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-primary">
        <FileText className="h-3.5 w-3.5" /> {KIND_LABEL[d.kind] || "Task"}
      </div>
      <div className="mt-1 font-medium text-[15px] leading-5" data-testid="proposal-title">{d.title}</div>
      {d.details && <div className="mt-1 text-sm text-muted-foreground">{d.details}</div>}
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {d.assignee_name && <span>For: <span className="text-foreground font-medium">{d.assignee_name}</span></span>}
        {d.counterparty && <span>With: <span className="text-foreground font-medium">{d.counterparty}</span></span>}
        {d.due_at && <span>Due: <span className="text-foreground font-medium">{fmtWhen(d.due_at)}</span></span>}
        {d.remind_at && <span>Remind: <span className="text-foreground font-medium">{fmtWhen(d.remind_at)}</span></span>}
        {d.amount != null && <span>Amount: <span className="text-foreground font-medium">{money(d.amount, d.currency)}</span></span>}
        {d.private && <span className="text-foreground font-medium">Private</span>}
      </div>
      {!saved && !skipped && (
        <div className="mt-3 grid grid-cols-3 gap-2">
          <Button size="sm" onClick={() => onSave?.(card.card_id, null)} data-testid={`proposal-save-${card.card_id}`} className="btn-lift"><Save className="h-4 w-4 mr-1" /> Save</Button>
          <Button size="sm" variant="outline" onClick={() => setOpen(true)} data-testid={`proposal-edit-${card.card_id}`}><Pencil className="h-4 w-4 mr-1" /> Edit</Button>
          <Button size="sm" variant="outline" onClick={() => onSkip?.(card.card_id)} data-testid={`proposal-skip-${card.card_id}`}><X className="h-4 w-4 mr-1" /> Skip</Button>
        </div>
      )}
      {saved && (
        <div className="mt-3 flex items-center gap-2 text-sm text-emerald-700">
          <Check className="h-4 w-4" /> Saved.
          <button className="inline-flex items-center gap-1 text-primary hover:underline" data-testid={`proposal-undo-${card.card_id}`} onClick={() => onUndo?.(card.card_id)}>
            <Undo2 className="h-3.5 w-3.5" /> Undo
          </button>
        </div>
      )}
      {skipped && <div className="mt-3 text-sm text-muted-foreground">Skipped.</div>}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="proposal-edit-dialog">
          <DialogHeader><DialogTitle>Edit before saving</DialogTitle><DialogDescription>Small fixes KONNTO got slightly wrong.</DialogDescription></DialogHeader>
          <div className="space-y-3">
            <label className="block text-sm">Title<Input className="mt-1" value={form.title || ""} onChange={(e) => setForm({ ...form, title: e.target.value })} data-testid="proposal-edit-title" /></label>
            <label className="block text-sm">Details<Textarea className="mt-1" rows={3} value={form.details || ""} onChange={(e) => setForm({ ...form, details: e.target.value })} data-testid="proposal-edit-details" /></label>
            <label className="block text-sm">Kind
              <Select value={form.kind} onValueChange={(v) => setForm({ ...form, kind: v })}>
                <SelectTrigger className="mt-1" data-testid="proposal-edit-kind"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {["task", "promise", "reminder", "decision", "note"].map((k) => <SelectItem key={k} value={k}>{KIND_LABEL[k]}</SelectItem>)}
                </SelectContent>
              </Select>
            </label>
            <label className="block text-sm">Assignee
              <Select value={form.assignee_id || ""} onValueChange={(v) => setForm({ ...form, assignee_id: v })}>
                <SelectTrigger className="mt-1" data-testid="proposal-edit-assignee"><SelectValue placeholder="Pick someone" /></SelectTrigger>
                <SelectContent>{(people || []).map((p) => <SelectItem key={p.member_id} value={p.member_id}>{p.name}</SelectItem>)}</SelectContent>
              </Select>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block text-sm">Due<Input type="datetime-local" className="mt-1" value={toLocalInput(form.due_at)} onChange={(e) => setForm({ ...form, due_at: fromLocalInput(e.target.value) })} data-testid="proposal-edit-due" /></label>
              <label className="block text-sm">Remind<Input type="datetime-local" className="mt-1" value={toLocalInput(form.remind_at)} onChange={(e) => setForm({ ...form, remind_at: fromLocalInput(e.target.value) })} data-testid="proposal-edit-remind" /></label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={() => { setOpen(false); onSave?.(card.card_id, form); }} data-testid="proposal-edit-save">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function InviteCard({ card }) {
  const d = card.data || {};
  return (
    <div className="rounded-2xl border border-border bg-card p-3" data-testid={`chat-card-invite-${card.card_id}`}>
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-primary"><UserPlus className="h-3.5 w-3.5" /> Invite ready</div>
      <div className="mt-1 font-medium">{d.name}</div>
      {d.job && <div className="text-sm text-muted-foreground">{d.job}</div>}
      {d.access_reason && <div className="mt-1 text-xs text-muted-foreground">{d.access_reason}</div>}
      {d.invite_url && (
        <div className="mt-3 space-y-2">
          <div className="flex gap-2">
            <Input value={d.invite_url} readOnly data-testid="invite-url-input" className="text-xs" />
            <Button size="icon" variant="outline" onClick={() => copy(d.invite_url)} aria-label="Copy" data-testid="invite-copy-url"><Copy className="h-4 w-4" /></Button>
          </div>
          {d.share_url && <Button asChild size="sm" variant="outline" data-testid="invite-share-wa"><a href={d.share_url} target="_blank" rel="noreferrer"><LinkIcon className="h-4 w-4 mr-1" /> Share on WhatsApp</a></Button>}
        </div>
      )}
    </div>
  );
}

function SimpleCard({ card, label, children }) {
  const Icon = ICONS[card.type] || BookMarked;
  return (
    <div className="rounded-2xl border border-border bg-card p-3" data-testid={`chat-card-${card.type}-${card.card_id}`}>
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-primary"><Icon className="h-3.5 w-3.5" /> {label}</div>
      <div className="mt-1 text-sm">{children}</div>
    </div>
  );
}

export function BrainCard({ card, people, onAction }) {
  const t = card.type;
  if (t === "proposal") return <ProposalCard card={card} people={people} onSave={(id, edits) => onAction?.(id, "save", edits)} onSkip={(id) => onAction?.(id, "skip")} onUndo={(id) => onAction?.(id, "undo")} />;
  if (t === "invite") return <InviteCard card={card} />;
  if (t === "approval") {
    const d = card.data || {};
    return <SimpleCard card={card} label={card.status === "allowed_by_rule" ? "Approved by rule" : "Sent for approval"}>{d.title}{d.rule_text ? ` — ${d.rule_text}` : ""}</SimpleCard>;
  }
  if (t === "access_request") return <SimpleCard card={card} label="Access request sent">We asked the owner to grant: <span className="font-medium text-foreground">{card.data?.label}</span>.</SimpleCard>;
  if (t === "rule") return <SimpleCard card={card} label="Rule saved">{card.data?.text}</SimpleCard>;
  if (t === "fact") return <SimpleCard card={card} label="Remembered">{card.data?.text}</SimpleCard>;
  if (t === "decision") return <SimpleCard card={card} label="Decision applied">{card.data?.summary}</SimpleCard>;
  if (t === "message") return <SimpleCard card={card} label={`Sent to ${card.data?.to_name}`}>“{card.data?.text}”</SimpleCard>;
  if (t === "business") return <SimpleCard card={card} label="Business profile updated">{Object.entries(card.data || {}).filter(([k]) => k !== "owner_user_id").map(([k, v]) => <div key={k}><span className="text-muted-foreground">{k}:</span> <span className="font-medium">{String(v)}</span></div>)}</SimpleCard>;
  if (t === "update") return <SimpleCard card={card} label="Work item updated">“{card.data?.title}” → <span className="font-medium">{card.data?.new_status}</span></SimpleCard>;
  if (t === "doc") return <SimpleCard card={card} label="Document saved">{card.data?.filename}{card.data?.summary ? ` — ${card.data.summary}` : ""}</SimpleCard>;
  return null;
}

export default BrainCard;
