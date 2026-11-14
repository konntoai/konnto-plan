import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { ShieldCheck, Check, X, Undo2, MessageCircle, Clock, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader, EmptyState, PersonAvatar, TonePill } from "@/components/common";
import { useApi } from "@/lib/api";
import { fmtAgo, money } from "@/lib/format";

function ApprovalCard({ ap, canDecide, onDecide, onUndo, onReply }) {
  const [maxAmount, setMaxAmount] = useState(ap.amount ? Math.ceil(Number(ap.amount) * 1.2 / 100) * 100 : "");
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);

  const decide = async (decision, amount) => {
    if (busy) return;
    setBusy(true);
    try { await onDecide(decision, amount); }
    finally { setBusy(false); }
  };

  const words = async () => {
    if (!reply.trim() || busy) return;
    setBusy(true);
    try { const understood = await onReply(reply); if (understood) setReply(""); }
    finally { setBusy(false); }
  };

  const pending = ap.status === "pending";

  return (
    <div className="rounded-3xl surface p-4 sm:p-5" data-testid="approval-card">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <PersonAvatar name={ap.requested_by_name} size={36} />
          <div className="min-w-0">
            <div className="text-sm text-muted-foreground">{ap.requested_by_name} · {fmtAgo(ap.created_at)}</div>
            <div className="font-display font-bold text-[15px] sm:text-base truncate">{ap.title}</div>
          </div>
        </div>
        {pending
          ? <TonePill tone="pending" icon={Clock}>Pending</TonePill>
          : <TonePill tone="decided" icon={Check} testid="approval-decided-pill">Decided</TonePill>}
      </div>
      {ap.details && <p className="mt-2 text-sm text-muted-foreground">{ap.details}</p>}
      {ap.amount != null && <div className="mt-3 inline-flex items-baseline gap-2 rounded-xl border border-border bg-[hsl(var(--surface-2))] px-3 py-2"><span className="eyebrow text-muted-foreground">Amount</span><span className="font-mono tabular text-lg font-semibold">{money(ap.amount, ap.currency)}</span></div>}

      {pending && canDecide && (
        <div className="mt-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <Button onClick={() => decide("once")} disabled={busy} data-testid="approval-allow-once"><Check className="h-4 w-4 mr-1" /> Allow once</Button>
            {ap.amount != null ? (
              <div className="flex gap-2 items-center">
                <Input type="number" value={maxAmount} onChange={(e) => setMaxAmount(e.target.value)} placeholder="Under" className="h-10" data-testid="approval-always-amount" />
                <Button variant="outline" onClick={() => decide("always", maxAmount ? Number(maxAmount) : undefined)} disabled={busy} data-testid="approval-allow-always" className="shrink-0">Always under</Button>
              </div>
            ) : (
              <Button variant="outline" onClick={() => decide("always")} disabled={busy} data-testid="approval-allow-always">Always allow</Button>
            )}
            <Button variant="outline" className="text-destructive" onClick={() => decide("deny")} disabled={busy} data-testid="approval-deny"><X className="h-4 w-4 mr-1" /> Don't allow</Button>
          </div>
          <div className="flex gap-2">
            <Textarea placeholder="Or reply in words — e.g. “yes under 15000”" rows={1} value={reply} onChange={(e) => setReply(e.target.value)} data-testid="approval-reply-text" />
            <Button variant="outline" onClick={words} disabled={busy || !reply.trim()} data-testid="approval-reply-button"><MessageCircle className="h-4 w-4" /></Button>
          </div>
        </div>
      )}
      {!pending && (
        <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
          <span>{ap.decision_text || "Decided"}</span>
          {canDecide && (
            <button className="ml-auto inline-flex items-center gap-1 text-primary hover:underline" onClick={onUndo} data-testid="approval-undo"><Undo2 className="h-3.5 w-3.5" /> Undo</button>
          )}
        </div>
      )}
    </div>
  );
}

export default function ApprovalsPage() {
  const api = useApi();
  const [tab, setTab] = useState("pending");
  const [data, setData] = useState({ approvals: [], can_decide: false });
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await api.get(`/approvals?status=${tab}`)); }
    catch (e) { toast.error(e.message); }
    finally { setLoading(false); }
  }, [api, tab]);

  useEffect(() => { load(); }, [load]);

  const decide = async (id, decision, max_amount) => {
    try { await api.post(`/approvals/${id}/decide`, { decision, max_amount }); toast.success("Done"); load(); }
    catch (e) { toast.error(e.message); }
  };
  const undo = async (id) => { try { await api.post(`/approvals/${id}/undo`); toast.success("Undone"); load(); } catch (e) { toast.error(e.message); } };
  const reply = async (id, text) => {
    try {
      const r = await api.post(`/approvals/${id}/reply`, { text });
      if (!r.understood) toast.message(r.summary);
      else { toast.success("Done"); load(); }
      return r.understood;
    } catch (e) { toast.error(e.message); return false; }
  };

  return (
    <div className="p-4 lg:p-8 max-w-[900px] mx-auto" data-testid="approvals-page">
      <PageHeader title="Approvals" subtitle={data.can_decide ? "Decide once, always, or don’t allow. Undo any time." : "Your approval requests and their status."} />
      <Tabs value={tab} onValueChange={setTab} className="mb-4">
        <TabsList data-testid="approvals-tabs">
          <TabsTrigger value="pending" data-testid="approvals-tab-pending">Pending</TabsTrigger>
          <TabsTrigger value="decided" data-testid="approvals-tab-decided">Decided</TabsTrigger>
        </TabsList>
      </Tabs>

      {loading ? <div className="text-muted-foreground text-sm"><Loader2 className="h-4 w-4 animate-spin inline" /> Loading…</div>
      : data.approvals.length === 0 ? <EmptyState icon={ShieldCheck} title={tab === "pending" ? "Nothing to decide" : "No decisions yet"} body="KONNTO only asks when it's not sure. You'll see new requests here." testid="approvals-empty" />
      : <div className="space-y-3">{data.approvals.map((ap) => <ApprovalCard key={ap.approval_id} ap={ap} canDecide={data.can_decide} onDecide={(d, a) => decide(ap.approval_id, d, a)} onUndo={() => undo(ap.approval_id)} onReply={(t) => reply(ap.approval_id, t)} />)}</div>}
    </div>
  );
}
