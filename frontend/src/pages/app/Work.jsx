import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { Plus, Search, Filter, ArrowRight, Loader2, Check, Clock, Pencil, Trash2, Mail, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription, DialogTrigger } from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, StatusPill, PersonAvatar, EmptyState, stateDot } from "@/components/common";
import { useApi } from "@/lib/api";
import { fmtWhen, money, KIND_LABEL, toLocalInput, fromLocalInput, fmtAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

const STATE_TABS = [
  { value: "active", label: "Active" },
  { value: "overdue", label: "Overdue" },
  { value: "due", label: "Due" },
  { value: "stuck", label: "Stuck" },
  { value: "done", label: "Done" },
  { value: "all", label: "All" },
];
const KIND_TABS = [
  { value: "all", label: "All kinds" },
  { value: "task", label: "Tasks" },
  { value: "promise", label: "Promises" },
  { value: "reminder", label: "Reminders" },
  { value: "note", label: "Notes" },
];

function NewItemDialog({ onCreated, members }) {
  const api = useApi();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ kind: "task", title: "", details: "", assignee_id: "", due_at: "", remind_at: "", private: false });
  const submit = async (e) => {
    e.preventDefault();
    if (!form.title.trim()) { toast.error("Give it a title"); return; }
    setBusy(true);
    try {
      await api.post("/items", { ...form, assignee_id: form.assignee_id || undefined, due_at: form.due_at || undefined, remind_at: form.remind_at || undefined });
      toast.success("Added");
      setOpen(false);
      setForm({ kind: "task", title: "", details: "", assignee_id: "", due_at: "", remind_at: "", private: false });
      onCreated?.();
    } catch (err) {
      toast.error(err.message);
    } finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button data-testid="work-add-button"><Plus className="h-4 w-4 mr-1" /> Add</Button></DialogTrigger>
      <DialogContent data-testid="work-add-dialog">
        <DialogHeader><DialogTitle>Add work</DialogTitle><DialogDescription>A task, promise, reminder or personal note.</DialogDescription></DialogHeader>
        <form onSubmit={submit} className="space-y-3">
          <Select value={form.kind} onValueChange={(v) => setForm({ ...form, kind: v })}>
            <SelectTrigger data-testid="work-add-kind"><SelectValue /></SelectTrigger>
            <SelectContent>{["task", "promise", "reminder", "note"].map((k) => <SelectItem key={k} value={k}>{KIND_LABEL[k]}</SelectItem>)}</SelectContent>
          </Select>
          <Input placeholder="Title" autoFocus value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} data-testid="work-add-title" />
          <Textarea placeholder="Details (optional)" rows={3} value={form.details} onChange={(e) => setForm({ ...form, details: e.target.value })} data-testid="work-add-details" />
          {form.kind !== "note" && (
            <Select value={form.assignee_id} onValueChange={(v) => setForm({ ...form, assignee_id: v })}>
              <SelectTrigger data-testid="work-add-assignee"><SelectValue placeholder="Who's it for?" /></SelectTrigger>
              <SelectContent>{members.map((m) => <SelectItem key={m.member_id} value={m.member_id}>{m.name}</SelectItem>)}</SelectContent>
            </Select>
          )}
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm">Due<Input type="datetime-local" className="mt-1" value={form.due_at} onChange={(e) => setForm({ ...form, due_at: e.target.value })} data-testid="work-add-due" /></label>
            <label className="text-sm">Remind<Input type="datetime-local" className="mt-1" value={form.remind_at} onChange={(e) => setForm({ ...form, remind_at: e.target.value })} data-testid="work-add-remind" /></label>
          </div>
          {form.kind === "note" && (
            <label className="flex items-center gap-2 text-sm"><Checkbox checked={form.private} onCheckedChange={(v) => setForm({ ...form, private: Boolean(v) })} data-testid="work-add-private" /> Private — only you</label>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={busy} data-testid="work-add-submit">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ItemDetail({ itemId, onClose, onChange, members }) {
  const api = useApi();
  const [detail, setDetail] = useState(null);
  const [statusForm, setStatusForm] = useState({ status: "", reason: "", new_due_at: "" });
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState(null);

  const load = useCallback(async () => {
    if (!itemId) return;
    try {
      const d = await api.get(`/items/${itemId}`);
      setDetail(d);
      setEditForm({ title: d.title, details: d.details, due_at: d.due_at, remind_at: d.remind_at, assignee_id: d.assignee_id, kind: d.kind });
    } catch (e) { toast.error(e.message); onClose(); }
  }, [api, itemId, onClose]);

  useEffect(() => { load(); }, [load]);

  const setStatus = async (status) => {
    const needsReason = status === "delayed" || status === "stuck";
    if (needsReason && !statusForm.reason.trim()) { toast.error("Give a short reason"); return; }
    try {
      await api.post(`/items/${itemId}/status`, { status, reason: statusForm.reason || undefined, new_due_at: statusForm.new_due_at || undefined });
      toast.success("Updated");
      await load();
      onChange?.();
      setStatusForm({ status: "", reason: "", new_due_at: "" });
    } catch (e) { toast.error(e.message); }
  };

  const saveEdit = async () => {
    try {
      await api.patch(`/items/${itemId}`, editForm);
      toast.success("Saved");
      setEditing(false);
      await load();
      onChange?.();
    } catch (e) { toast.error(e.message); }
  };

  const remove = async () => {
    if (!window.confirm("Delete this?")) return;
    try {
      await api.del(`/items/${itemId}`);
      toast.success("Deleted");
      onClose();
      onChange?.();
    } catch (e) { toast.error(e.message); }
  };

  if (!detail) return <div className="p-6"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>;

  return (
    <div className="space-y-5 py-2">
      <div>
        <div className="text-[11px] uppercase tracking-wide text-primary font-semibold">{KIND_LABEL[detail.kind]}</div>
        {editing ? (
          <Input value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} className="mt-2 text-lg font-semibold" data-testid="work-detail-edit-title" />
        ) : (
          <h2 className="mt-1 text-xl font-semibold" data-testid="work-detail-title">{detail.title}</h2>
        )}
        <div className="mt-2 flex items-center gap-2 flex-wrap">
          <StatusPill state={detail.state} />
          {detail.assignee_name && <span className="inline-flex items-center gap-1.5 text-sm"><PersonAvatar name={detail.assignee_name} size={22} /> {detail.assignee_name}</span>}
          {detail.amount != null && <span className="text-sm text-muted-foreground">{money(detail.amount, detail.currency)}</span>}
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-background p-3 space-y-3">
        {editing ? (
          <>
            <Textarea rows={3} value={editForm.details || ""} onChange={(e) => setEditForm({ ...editForm, details: e.target.value })} data-testid="work-detail-edit-details" />
            <div className="grid grid-cols-2 gap-3">
              <label className="text-sm">Due<Input type="datetime-local" className="mt-1" value={toLocalInput(editForm.due_at)} onChange={(e) => setEditForm({ ...editForm, due_at: fromLocalInput(e.target.value) })} /></label>
              <label className="text-sm">Remind<Input type="datetime-local" className="mt-1" value={toLocalInput(editForm.remind_at)} onChange={(e) => setEditForm({ ...editForm, remind_at: fromLocalInput(e.target.value) })} /></label>
            </div>
            <Select value={editForm.assignee_id || ""} onValueChange={(v) => setEditForm({ ...editForm, assignee_id: v })}>
              <SelectTrigger><SelectValue placeholder="Assignee" /></SelectTrigger>
              <SelectContent>{members.map((m) => <SelectItem key={m.member_id} value={m.member_id}>{m.name}</SelectItem>)}</SelectContent>
            </Select>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
              <Button onClick={saveEdit} data-testid="work-detail-save-edits">Save</Button>
            </div>
          </>
        ) : (
          <>
            {detail.details && <p className="text-sm whitespace-pre-wrap">{detail.details}</p>}
            <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
              {detail.due_at && <div><span className="text-muted-foreground">Due</span><div className="font-medium">{fmtWhen(detail.due_at)}</div></div>}
              {detail.remind_at && <div><span className="text-muted-foreground">Remind</span><div className="font-medium">{fmtWhen(detail.remind_at)}</div></div>}
              {detail.counterparty && <div><span className="text-muted-foreground">With</span><div className="font-medium">{detail.counterparty}</div></div>}
              {detail.project && <div><span className="text-muted-foreground">Project</span><div className="font-medium">{detail.project.name}</div></div>}
            </div>
          </>
        )}
      </div>

      {!editing && detail.can_edit && detail.state !== "done" && detail.state !== "cancelled" && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold">Update status</h3>
          <div className="grid grid-cols-3 gap-2">
            <Button variant="outline" onClick={() => setStatus("done")} data-testid="work-detail-mark-done"><Check className="h-4 w-4 mr-1" /> Done</Button>
            <Button variant="outline" onClick={() => setStatusForm({ ...statusForm, status: "delayed" })} data-testid="work-detail-mark-delayed"><Clock className="h-4 w-4 mr-1" /> Delayed</Button>
            <Button variant="outline" onClick={() => setStatusForm({ ...statusForm, status: "stuck" })} data-testid="work-detail-mark-stuck">Stuck</Button>
          </div>
          {(statusForm.status === "delayed" || statusForm.status === "stuck") && (
            <div className="space-y-2 rounded-xl border border-border bg-background p-3">
              <Textarea rows={2} placeholder="Short reason" value={statusForm.reason} onChange={(e) => setStatusForm({ ...statusForm, reason: e.target.value })} data-testid="work-detail-reason" />
              {statusForm.status === "delayed" && <Input type="datetime-local" value={statusForm.new_due_at} onChange={(e) => setStatusForm({ ...statusForm, new_due_at: e.target.value })} data-testid="work-detail-new-due" />}
              <div className="flex gap-2 justify-end">
                <Button variant="outline" onClick={() => setStatusForm({ status: "", reason: "", new_due_at: "" })}>Cancel</Button>
                <Button onClick={() => setStatus(statusForm.status)} data-testid="work-detail-reason-submit">Save</Button>
              </div>
            </div>
          )}
        </div>
      )}

      {detail.history?.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-2">Timeline</h3>
          <ul className="space-y-2 text-xs">
            {detail.history.slice().reverse().map((h, i) => (
              <li key={i} className="flex gap-3">
                <span className="text-muted-foreground tabular">{fmtAgo(h.at)}</span>
                <span>{h.actor}: {h.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {detail.can_edit && !editing && (
        <div className="flex gap-2 pt-2 border-t border-border">
          <Button variant="outline" onClick={() => setEditing(true)} data-testid="work-detail-edit"><Pencil className="h-4 w-4 mr-1" /> Edit</Button>
          <Button variant="outline" className="text-destructive" onClick={remove} data-testid="work-detail-delete"><Trash2 className="h-4 w-4 mr-1" /> Delete</Button>
        </div>
      )}
    </div>
  );
}

export default function WorkPage() {
  const api = useApi();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState({ items: [], projects: [] });
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [state, setState] = useState(params.get("state") || "active");
  const [kind, setKind] = useState("all");
  const [mine, setMine] = useState(false);
  const [selected, setSelected] = useState(params.get("item") || null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const q = new URLSearchParams();
      if (kind !== "all") q.set("kind", kind);
      if (state) q.set("state", state);
      if (mine) q.set("mine", "true");
      if (search) q.set("q", search);
      const d = await api.get(`/items?${q}`);
      setData(d);
    } catch (e) { toast.error(e.message); } finally { setLoading(false); }
  }, [api, kind, state, mine, search]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { api.get("/members").then((m) => setMembers(m.members || [])); }, [api]);

  const onSelect = (id) => {
    setSelected(id);
    const p = new URLSearchParams(params);
    if (id) p.set("item", id); else p.delete("item");
    setParams(p, { replace: true });
  };

  const rows = useMemo(() => data.items || [], [data]);

  return (
    <div className="p-4 lg:p-6 max-w-[1120px] mx-auto" data-testid="work-page">
      <PageHeader title="Work" subtitle="Tasks, promises, reminders — everything that needs doing.">
        <NewItemDialog onCreated={load} members={members} />
      </PageHeader>

      <div className="sticky top-14 lg:top-16 z-10 -mx-4 lg:-mx-6 px-4 lg:px-6 py-3 bg-background/95 backdrop-blur border-b border-border">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <Tabs value={state} onValueChange={setState}>
            <TabsList data-testid="work-state-tabs" className="overflow-x-auto no-scrollbar max-w-full">
              {STATE_TABS.map((t) => <TabsTrigger key={t.value} value={t.value} data-testid={`work-tab-${t.value}`}>{t.label}</TabsTrigger>)}
            </TabsList>
          </Tabs>
          <div className="flex gap-2">
            <Select value={kind} onValueChange={setKind}>
              <SelectTrigger className="w-[140px]" data-testid="work-kind-filter"><SelectValue /></SelectTrigger>
              <SelectContent>{KIND_TABS.map((k) => <SelectItem key={k.value} value={k.value}>{k.label}</SelectItem>)}</SelectContent>
            </Select>
            <Button variant={mine ? "default" : "outline"} onClick={() => setMine((m) => !m)} data-testid="work-mine-toggle"><Filter className="h-4 w-4 mr-1" /> {mine ? "Only mine" : "Everyone"}</Button>
          </div>
        </div>
        <div className="mt-3 relative">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input placeholder="Search work" value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" data-testid="work-search" />
        </div>
      </div>

      <div className="mt-4 space-y-2">
        {loading ? (
          <>{[0,1,2].map((i) => <Skeleton key={i} className="h-16 rounded-2xl" />)}</>
        ) : rows.length === 0 ? (
          <EmptyState icon={Check} title="Nothing to show" body="Try changing the filter above — or add some work." testid="work-empty-state" />
        ) : (
          rows.map((item) => (
            <button key={item.item_id} onClick={() => onSelect(item.item_id)} className="w-full text-left flex items-start gap-3 rounded-2xl border border-border bg-card px-3 py-3 hover:bg-accent/40 transition-colors" data-testid="work-item-row">
              <div className={cn("mt-1.5 h-2 w-2 rounded-full", stateDot(item.state))} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] uppercase tracking-wide text-muted-foreground">{KIND_LABEL[item.kind]}</span>
                  {item.project_name && <span className="text-[11px] text-muted-foreground">· {item.project_name}</span>}
                </div>
                <div className="text-sm font-medium truncate">{item.title}</div>
                <div className="mt-0.5 text-xs text-muted-foreground flex flex-wrap gap-x-3 gap-y-1">
                  {item.assignee_name && <span>For {item.assignee_name}</span>}
                  {item.counterparty && <span>With {item.counterparty}</span>}
                  {item.due_at && <span>Due {fmtWhen(item.due_at)}</span>}
                  {item.amount != null && <span>{money(item.amount, item.currency)}</span>}
                </div>
              </div>
              <StatusPill state={item.state} />
              <ArrowRight className="h-4 w-4 text-muted-foreground mt-2" />
            </button>
          ))
        )}
      </div>

      <Sheet open={!!selected} onOpenChange={(v) => !v && onSelect(null)}>
        <SheetContent className="w-full sm:w-[520px] overflow-y-auto scrollbar-thin bg-card" data-testid="work-detail-sheet">
          <SheetHeader><SheetTitle>Work details</SheetTitle></SheetHeader>
          {selected && <ItemDetail itemId={selected} members={members} onClose={() => onSelect(null)} onChange={load} />}
        </SheetContent>
      </Sheet>
    </div>
  );
}
