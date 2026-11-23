import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Activity, AlertTriangle, CheckCircle2, Clock3, Plus, RefreshCw, Send, ShieldCheck, Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageHeader, EmptyState, PersonAvatar } from "@/components/common";
import { useApi } from "@/lib/api";
import { useMe } from "@/context/MeContext";
import { fmtWhen } from "@/lib/format";

const STATUS = {
  issued: { label: "Issued", tone: "text-blue-500 bg-blue-500/10" },
  acknowledged: { label: "Acknowledged", tone: "text-violet-500 bg-violet-500/10" },
  in_progress: { label: "In progress", tone: "text-amber-500 bg-amber-500/10" },
  blocked: { label: "Blocked", tone: "text-red-500 bg-red-500/10" },
  completed: { label: "Completed", tone: "text-emerald-500 bg-emerald-500/10" },
  cancelled: { label: "Cancelled", tone: "text-muted-foreground bg-muted" },
};

function Stat({ label, value, icon: Icon }) {
  return <div className="rounded-2xl surface p-4"><div className="flex items-center justify-between text-muted-foreground"><span className="text-xs font-semibold">{label}</span><Icon className="h-4 w-4" /></div><div className="mt-2 text-2xl font-display font-bold tabular-nums">{value || 0}</div></div>;
}

function InstructionCard({ row, onProgress, onCancel, memberId }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const assigned = row.assignee_id === memberId;
  const issuer = row.issued_by === memberId;
  const closed = ["completed", "cancelled"].includes(row.status);
  const act = async (status) => {
    setBusy(true);
    try { await onProgress(row.instruction_id, { status, note: note.trim() || undefined, evidence: status === "completed" ? note.trim() : undefined }); setNote(""); }
    finally { setBusy(false); }
  };
  const meta = STATUS[row.status] || STATUS.issued;
  return (
    <article className="rounded-2xl surface p-4 sm:p-5 space-y-3" data-testid="pcm-instruction-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${meta.tone}`}>{meta.label}</span>
            <span className="text-[11px] uppercase tracking-wide text-muted-foreground">{row.department} · {row.priority}</span>
          </div>
          <h3 className="mt-2 font-semibold leading-snug">{row.title}</h3>
          {row.details && <p className="mt-1 text-sm text-muted-foreground whitespace-pre-wrap">{row.details}</p>}
          {row.objective && <p className="mt-2 text-xs text-muted-foreground flex gap-2"><Target className="h-3.5 w-3.5 shrink-0" />{row.objective}</p>}
        </div>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1.5"><PersonAvatar name={row.assignee_name} size={20} /> {row.assignee_name}</span>
        <span>Issued by {row.issued_by_name}</span>
        {row.due_at && <span className="inline-flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" />Due {fmtWhen(row.due_at)}</span>}
      </div>
      {row.blocker && <div className="rounded-xl bg-red-500/10 text-red-600 dark:text-red-300 p-3 text-sm"><strong>Blocker:</strong> {row.blocker}</div>}
      {(row.evidence || []).length > 0 && <div className="rounded-xl bg-muted/50 p-3 text-xs space-y-1"><strong>Evidence / updates</strong>{row.evidence.slice(-3).map((e, i) => <p key={i} className="text-muted-foreground">{e.by}: {e.text}</p>)}</div>}
      {!closed && (assigned || issuer) && (
        <div className="border-t border-border/60 pt-3 space-y-2">
          <Textarea value={note} onChange={e => setNote(e.target.value)} placeholder={assigned ? "Add an update, blocker reason or completion evidence…" : "Add a coordination note…"} rows={2} />
          <div className="flex flex-wrap gap-2">
            {assigned && row.status === "issued" && <Button size="sm" variant="outline" disabled={busy} onClick={() => act("acknowledged")}>Acknowledge</Button>}
            {assigned && ["issued", "acknowledged"].includes(row.status) && <Button size="sm" variant="outline" disabled={busy} onClick={() => act("in_progress")}>Start work</Button>}
            {assigned && <Button size="sm" variant="outline" disabled={busy || !note.trim()} onClick={() => act("blocked")}><AlertTriangle className="h-3.5 w-3.5 mr-1" />Report blocker</Button>}
            {assigned && <Button size="sm" disabled={busy || !note.trim()} onClick={() => act("completed")}><CheckCircle2 className="h-3.5 w-3.5 mr-1" />Complete with evidence</Button>}
            {issuer && <Button size="sm" variant="ghost" className="text-destructive" disabled={busy} onClick={() => onCancel(row.instruction_id)}>Cancel</Button>}
          </div>
        </div>
      )}
      <div className="text-[10px] text-muted-foreground">Updated {fmtWhen(row.updated_at)} · Follow-up stage {row.followup_level || 0}/2 · Linked to Work item {row.item_id}</div>
    </article>
  );
}

export default function PCMPage() {
  const api = useApi();
  const { me } = useMe();
  const [data, setData] = useState(null);
  const [people, setPeople] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [filter, setFilter] = useState("open");
  const [form, setForm] = useState({ title: "", details: "", assignee_id: "", due_at: "", priority: "normal", department: "operations", objective: "", authority_class: "delegated" });
  const memberId = me?.member?.member_id;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [overview, team] = await Promise.all([api.get("/pcm/overview"), api.get("/members")]);
      setData(overview);
      setPeople((team.members || []).filter(p => p.status === "active" && p.member_type === "team"));
    } catch (e) { toast.error(e.message || "Couldn't load PCM"); }
    finally { setLoading(false); }
  }, [api]);

  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.assignee_id) return toast.error("Add an instruction and choose a team member.");
    setSaving(true);
    try {
      await api.post("/pcm/instructions", { ...form, due_at: form.due_at ? new Date(form.due_at).toISOString() : null });
      toast.success("Instruction issued and added to Work.");
      setForm({ title: "", details: "", assignee_id: "", due_at: "", priority: "normal", department: "operations", objective: "", authority_class: "delegated" });
      setShowForm(false);
      await load();
    } catch (e) { toast.error(e.message || "Couldn't issue instruction"); }
    finally { setSaving(false); }
  };

  const progress = async (id, payload) => {
    try { await api.post(`/pcm/instructions/${id}/progress`, payload); toast.success("Progress recorded"); await load(); }
    catch (e) { toast.error(e.message || "Couldn't update progress"); }
  };
  const cancel = async (id) => {
    try { await api.post(`/pcm/instructions/${id}/cancel`, {}); toast.success("Instruction cancelled"); await load(); }
    catch (e) { toast.error(e.message || "Couldn't cancel instruction"); }
  };

  const rows = useMemo(() => (data?.instructions || []).filter(x => filter === "all" || (filter === "open" ? !["completed", "cancelled"].includes(x.status) : x.status === filter)), [data, filter]);
  const counts = data?.counts || {};

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 space-y-6" data-testid="pcm-page">
      <PageHeader title="KONNTO PCM" subtitle="Business coordination, instruction ownership and evidence-backed follow-through." />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground"><ShieldCheck className="h-4 w-4 text-primary" /> Owner authority stays protected. PCM records progress; it does not move money or sign commitments.</div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}><RefreshCw className="h-4 w-4 mr-1" />Refresh</Button>
          {data?.can_issue && <Button size="sm" onClick={() => setShowForm(v => !v)}><Plus className="h-4 w-4 mr-1" />New instruction</Button>}
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Issued" value={counts.issued} icon={Send} />
        <Stat label="In progress" value={counts.in_progress} icon={Activity} />
        <Stat label="Blocked" value={counts.blocked} icon={AlertTriangle} />
        <Stat label="Completed" value={counts.completed} icon={CheckCircle2} />
      </div>
      {showForm && (
        <form onSubmit={submit} className="rounded-2xl surface p-4 sm:p-5 space-y-4">
          <div><h2 className="font-semibold">Issue an instruction</h2><p className="text-xs text-muted-foreground mt-1">Instructions become shared Work items, with PCM status and evidence tracked here.</p></div>
          <div className="grid md:grid-cols-2 gap-3">
            <div className="md:col-span-2"><label className="text-xs font-semibold">Instruction</label><Input value={form.title} onChange={e => setForm(p => ({...p,title:e.target.value}))} maxLength={160} required placeholder="What needs to happen?" /></div>
            <div className="md:col-span-2"><label className="text-xs font-semibold">Context and expected outcome</label><Textarea value={form.details} onChange={e => setForm(p => ({...p,details:e.target.value}))} rows={3} placeholder="Why it matters, expected result and constraints…" /></div>
            <div><label className="text-xs font-semibold">Responsible person</label><Select value={form.assignee_id} onValueChange={v => setForm(p => ({...p,assignee_id:v}))}><SelectTrigger><SelectValue placeholder="Choose team member" /></SelectTrigger><SelectContent>{people.map(p => <SelectItem key={p.member_id} value={p.member_id}>{p.name} · {p.job || "Team"}</SelectItem>)}</SelectContent></Select></div>
            <div><label className="text-xs font-semibold">Department</label><Select value={form.department} onValueChange={v => setForm(p => ({...p,department:v}))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{["sales","marketing","finance","operations","people","technology","leadership","growth","other"].map(v => <SelectItem key={v} value={v}>{v[0].toUpperCase()+v.slice(1)}</SelectItem>)}</SelectContent></Select></div>
            <div><label className="text-xs font-semibold">Priority</label><Select value={form.priority} onValueChange={v => setForm(p => ({...p,priority:v}))}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{["low","normal","high","urgent"].map(v => <SelectItem key={v} value={v}>{v[0].toUpperCase()+v.slice(1)}</SelectItem>)}</SelectContent></Select></div>
            <div><label className="text-xs font-semibold">Due date</label><Input type="datetime-local" value={form.due_at} onChange={e => setForm(p => ({...p,due_at:e.target.value}))} /></div>
            <div className="md:col-span-2"><label className="text-xs font-semibold">Business objective (optional)</label><Input value={form.objective} onChange={e => setForm(p => ({...p,objective:e.target.value}))} maxLength={500} placeholder="Which business outcome does this support?" /></div>
          </div>
          <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={() => setShowForm(false)}>Cancel</Button><Button type="submit" disabled={saving}>{saving ? "Issuing…" : "Issue instruction"}</Button></div>
        </form>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h2 className="font-display text-xl font-bold">Instruction register</h2><p className="text-xs text-muted-foreground">Every status change is recorded against its owner and source instruction.</p></div>
        <Select value={filter} onValueChange={setFilter}><SelectTrigger className="w-44"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="open">Open instructions</SelectItem><SelectItem value="all">All instructions</SelectItem>{Object.keys(STATUS).map(k => <SelectItem key={k} value={k}>{STATUS[k].label}</SelectItem>)}</SelectContent></Select>
      </div>
      {loading ? <div className="rounded-2xl surface p-8 text-center text-sm text-muted-foreground">Loading PCM register…</div> :
        rows.length ? <div className="grid gap-3">{rows.map(row => <InstructionCard key={row.instruction_id} row={row} onProgress={progress} onCancel={cancel} memberId={memberId} />)}</div> :
        <EmptyState title="No instructions here yet" body="Issue a clear instruction to a responsible person, or check another filter." />}
    </div>
  );
}
