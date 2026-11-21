import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Users, UserPlus, Loader2, Copy, Link as LinkIcon, MessageSquare, Trash2, Shield, Settings2, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, PersonAvatar, EmptyState } from "@/components/common";
import { useApi } from "@/lib/api";

function InviteDialog({ onInvited }) {
  const api = useApi();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", job: "", member_type: "team", phone: "", email: "" });
  const [links, setLinks] = useState(null);
  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return toast.error("Name is needed");
    setBusy(true);
    try {
      const r = await api.post("/members", form);
      setLinks(r.links);
      toast.success("Invite created");
      onInvited?.();
    } catch (err) { toast.error(err.message); }
    finally { setBusy(false); }
  };
  const copy = (v) => { navigator.clipboard.writeText(v); toast.success("Copied"); };
  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) { setLinks(null); setForm({ name: "", job: "", member_type: "team", phone: "", email: "" }); } }}>
      <DialogTrigger asChild><Button data-testid="team-invite-button"><UserPlus className="h-4 w-4 mr-1" /> Invite</Button></DialogTrigger>
      <DialogContent data-testid="team-invite-dialog">
        <DialogHeader><DialogTitle>Invite someone</DialogTitle><DialogDescription>KONNTO picks a safe starting access based on their role. You can change it anytime.</DialogDescription></DialogHeader>
        {links ? (
          <div className="space-y-3 text-sm">
            <p className="text-muted-foreground">Share this link so they can join:</p>
            <div className="flex gap-2"><Input value={links.invite_url} readOnly data-testid="invite-url-input" /><Button size="icon" variant="outline" onClick={() => copy(links.invite_url)} aria-label="Copy"><Copy className="h-4 w-4" /></Button></div>
            {links.share_url && <Button asChild variant="outline" data-testid="invite-share-wa"><a href={links.share_url} target="_blank" rel="noreferrer"><LinkIcon className="h-4 w-4 mr-1" /> Share on WhatsApp</a></Button>}
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-3">
            <Input placeholder="Name" autoFocus value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="invite-name" />
            <Input placeholder="Role or job (e.g. Operations)" value={form.job} onChange={(e) => setForm({ ...form, job: e.target.value })} data-testid="invite-job" />
            <Select value={form.member_type} onValueChange={(v) => setForm({ ...form, member_type: v })}>
              <SelectTrigger data-testid="invite-type"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="team">Team member</SelectItem><SelectItem value="partner">Partner / supplier</SelectItem></SelectContent>
            </Select>
            <Input placeholder="WhatsApp number (optional)" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} data-testid="invite-phone" />
            <Input placeholder="Email (optional, used to send the invite)" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="invite-email" />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={busy} data-testid="invite-submit">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send invite"}</Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

function MemberEditor({ member, onClose, onChange, scopes, canManage }) {
  const api = useApi();
  const [form, setForm] = useState({ name: member.name, job: member.job, member_type: member.member_type, phone: member.phone || "", access: new Set(member.access || []) });
  const [busy, setBusy] = useState(false);
  const toggleAccess = (s) => { const n = new Set(form.access); n.has(s) ? n.delete(s) : n.add(s); setForm({ ...form, access: n }); };
  const save = async () => {
    setBusy(true);
    try {
      await api.patch(`/members/${member.member_id}`, { name: form.name, job: form.job, member_type: form.member_type, phone: form.phone, access: Array.from(form.access) });
      toast.success("Saved");
      onChange?.(); onClose();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const remove = async () => {
    if (!window.confirm(`Remove ${member.name}?`)) return;
    try { await api.del(`/members/${member.member_id}`); toast.success("Removed"); onChange?.(); onClose(); } catch (e) { toast.error(e.message); }
  };
  return (
    <div className="space-y-4 py-2">
      <div className="flex items-center gap-3">
        <PersonAvatar name={member.name} size={48} tone={member.member_type === "owner" ? "owner" : member.member_type === "partner" ? "partner" : "default"} />
        <div className="min-w-0">
          <div className="font-semibold truncate">{member.name}</div>
          <div className="text-sm text-muted-foreground">{member.job || member.member_type}</div>
          {member.access_reason && <div className="text-xs text-muted-foreground mt-1">{member.access_reason}</div>}
        </div>
      </div>
      {canManage && (
        <div className="space-y-3">
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="member-edit-name" />
          <Input value={form.job || ""} onChange={(e) => setForm({ ...form, job: e.target.value })} placeholder="Role or job" data-testid="member-edit-job" />
          <div>
            <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="WhatsApp number, e.g. +91 98765 43210" inputMode="tel" data-testid="member-edit-phone" />
            <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground" data-testid="member-wa-state">
              <Phone className="h-3.5 w-3.5" />
              {!member.phone ? "No WhatsApp number yet."
                : member.wa_opt_in ? "WhatsApp is on — KONNTO messages reach this phone."
                : `Waiting for ${member.name.split(" ")[0]} to send "hi" to the KONNTO number — that switches WhatsApp on.`}
            </div>
          </div>
          <Select value={form.member_type} onValueChange={(v) => setForm({ ...form, member_type: v })} disabled={member.member_type === "owner"}>
            <SelectTrigger data-testid="member-edit-type"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="team">Team member</SelectItem><SelectItem value="partner">Partner</SelectItem></SelectContent>
          </Select>
          <div>
            <div className="text-sm font-medium mb-1">Access</div>
            <div className="space-y-1 rounded-xl border border-border bg-[hsl(var(--surface-2))] p-3">
              {Object.entries(scopes || {}).map(([s, label]) => (
                <label key={s} className="flex items-start gap-2 text-sm">
                  <Checkbox checked={form.access.has(s)} onCheckedChange={() => toggleAccess(s)} data-testid={`member-access-${s}`} />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="flex gap-2 pt-2 border-t border-border">
            <Button onClick={save} disabled={busy} data-testid="member-save"><Shield className="h-4 w-4 mr-1" /> {busy ? "Saving…" : "Save"}</Button>
            {member.member_type !== "owner" && <Button variant="outline" className="text-destructive ml-auto" onClick={remove} data-testid="member-remove"><Trash2 className="h-4 w-4 mr-1" /> Remove</Button>}
          </div>
        </div>
      )}
      {member.links?.invite_url && (
        <div className="rounded-xl border border-border bg-[hsl(var(--surface-2))] p-3 space-y-2 text-sm">
          <div className="font-medium">Invite link</div>
          <div className="flex gap-2"><Input value={member.links.invite_url} readOnly data-testid="member-invite-url" /><Button size="icon" variant="outline" aria-label="Copy" onClick={() => { navigator.clipboard.writeText(member.links.invite_url); toast.success("Copied"); }}><Copy className="h-4 w-4" /></Button></div>
        </div>
      )}
    </div>
  );
}

export default function TeamPage() {
  const api = useApi();
  const navigate = useNavigate();
  const [data, setData] = useState({ members: [], can_manage: false });
  const [scopes, setScopes] = useState({});
  const [threads, setThreads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editId, setEditId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [m, s, t] = await Promise.all([api.get("/members"), api.get("/scopes"), api.get("/threads")]);
      setData(m); setScopes(s.scopes); setThreads(t.threads || []);
    } catch (e) { toast.error(e.message); } finally { setLoading(false); }
  }, [api]);

  useEffect(() => { load(); }, [load]);

  const openDirect = async (memberId) => {
    try {
      const t = await api.post("/threads", { member_ids: [memberId] });
      navigate(`/app/team/thread/${t.thread_id}`);
    } catch (e) { toast.error(e.message); }
  };

  const editing = data.members.find((m) => m.member_id === editId);

  return (
    <div className="p-4 lg:p-8 max-w-[1100px] mx-auto" data-testid="team-page">
      <PageHeader title="Team" subtitle="People, roles, access — and the chats that reach them wherever they are.">
        {data.can_manage && <InviteDialog onInvited={load} />}
      </PageHeader>

      {loading ? (<div className="space-y-2">{[0,1,2].map((i) => <Skeleton key={i} className="h-16 rounded-2xl" />)}</div>)
      : data.members.length === 0 ? <EmptyState icon={Users} title="Just you so far" body="Invite the people who help run the business — team or partners." testid="team-empty" />
      : (
        <div className="grid lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-2">
            <div className="eyebrow text-muted-foreground px-1">People</div>
            {data.members.map((m) => (
              <div key={m.member_id} className="flex items-center gap-3 rounded-2xl surface px-3.5 py-3.5" data-testid="team-member-row">
                <PersonAvatar name={m.name} size={40} tone={m.member_type === "owner" ? "owner" : m.member_type === "partner" ? "partner" : "default"} />
                <div className="min-w-0 flex-1">
                  <div className="font-medium truncate">{m.name}{m.member_id === data.me && <span className="ml-1 text-xs text-muted-foreground">(you)</span>}</div>
                  <div className="text-xs text-muted-foreground truncate">{m.job || m.member_type}{m.status === "invited" ? " · invited" : ""}</div>
                </div>
                <div className="hidden sm:flex items-center gap-1 text-[11px] text-muted-foreground">
                  {m.has_app && <span className="rounded-full border border-primary/20 bg-accent/60 text-accent-foreground px-2 py-0.5">App</span>}
                  {m.has_whatsapp && (m.wa_opt_in
                    ? <span className="rounded-full border border-primary/20 bg-accent/60 text-accent-foreground px-2 py-0.5" data-testid="team-member-wa-on">WhatsApp</span>
                    : <span className="rounded-full border border-dashed border-border px-2 py-0.5" title="Number added — waiting for them to message KONNTO" data-testid="team-member-wa-waiting">WhatsApp · waiting</span>)}
                </div>
                {m.member_id !== data.me && <Button size="sm" variant="outline" onClick={() => openDirect(m.member_id)} data-testid="team-direct-chat"><MessageSquare className="h-4 w-4" /></Button>}
                <Button size="sm" variant="ghost" onClick={() => setEditId(m.member_id)} data-testid="team-edit-member"><Settings2 className="h-4 w-4" /></Button>
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <div className="eyebrow text-muted-foreground px-1">Threads</div>
            {threads.length === 0 ? <div className="rounded-2xl border border-dashed border-primary/25 bg-card/60 p-4 text-sm text-muted-foreground">No threads yet. Start one from the people list.</div>
            : threads.map((t) => (
              <button key={t.thread_id} onClick={() => navigate(`/app/team/thread/${t.thread_id}`)} className="w-full text-left rounded-2xl surface surface-hover px-3.5 py-3.5" data-testid="team-thread-row">
                <div className="flex items-center gap-2"><span className="font-medium truncate flex-1">{t.title}</span>{t.unread > 0 && <span className="min-w-5 h-5 px-1.5 rounded-full bg-brand-red text-white text-[11px] grid place-items-center font-bold">{t.unread}</span>}</div>
                <div className="mt-0.5 text-xs text-muted-foreground truncate">{t.last_message_preview || "No messages yet"}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      <Sheet open={!!editId} onOpenChange={(v) => !v && setEditId(null)}>
        <SheetContent className="w-full sm:w-[480px] overflow-y-auto scrollbar-thin" data-testid="team-member-sheet">
          <SheetHeader><SheetTitle>Member details</SheetTitle></SheetHeader>
          {editing && <MemberEditor member={editing} canManage={data.can_manage && editing.member_type !== "owner"} scopes={scopes} onClose={() => setEditId(null)} onChange={load} />}
        </SheetContent>
      </Sheet>
    </div>
  );
}
