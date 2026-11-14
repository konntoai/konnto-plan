import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { PageHeader, SectionCard } from "@/components/common";
import { useApi } from "@/lib/api";
import { fmtAgo } from "@/lib/format";

export default function AdminCustomers() {
  const api = useApi();
  const [rows, setRows] = useState([]);
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [limit, setLimit] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [c, u] = await Promise.all([api.get("/admin/customers"), api.get("/admin/usage?days=30")]);
      setRows(c.customers || []); setUsage(u);
    } catch (e) { toast.error(e.message); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [api]);

  const saveLimit = async () => {
    try { await api.put(`/admin/customers/${editing.org_id}/limits`, { monthly_ai_messages: limit ? Number(limit) : null }); toast.success("Updated"); setEditing(null); load(); }
    catch (e) { toast.error(e.message); }
  };

  return (
    <div className="p-4 lg:p-8 max-w-[1200px] mx-auto space-y-5">
      <PageHeader title="Customers" subtitle="Who’s using KONNTO, how much, and their monthly limits." />
      {usage && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[["Businesses", usage.totals.orgs], ["People", usage.totals.members], ["AI messages (30d)", usage.totals.ai_messages], ["AI cost (30d)", `$${usage.totals.ai_cost}`]].map(([l, v]) => (
            <div key={l} className="rounded-3xl surface p-4 sm:p-5" data-testid={`admin-stat-${l.replace(/\s/g, "-").toLowerCase()}`}>
              <div className="text-xs text-muted-foreground">{l}</div><div className="text-2xl font-semibold font-display mt-1">{v}</div>
            </div>
          ))}
        </div>
      )}
      <SectionCard title="Businesses" testid="admin-customers-card">
        {loading ? <Loader2 className="h-4 w-4 animate-spin" />
        : rows.length === 0 ? <div className="text-sm text-muted-foreground">No customers yet.</div>
        : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-muted-foreground border-b border-border"><th className="py-2 pr-3">Business</th><th className="py-2 pr-3">Owner</th><th className="py-2 pr-3">Country</th><th className="py-2 pr-3">Members</th><th className="py-2 pr-3">AI msgs</th><th className="py-2 pr-3">WA</th><th className="py-2 pr-3">Limit</th><th className="py-2 pr-3"></th></tr></thead>
              <tbody>{rows.map((r) => (
                <tr key={r.org_id} className="border-b border-border/60" data-testid="admin-customer-row">
                  <td className="py-2 pr-3"><div className="font-medium truncate max-w-[200px]">{r.name}</div><div className="text-xs text-muted-foreground">{fmtAgo(r.created_at)}</div></td>
                  <td className="py-2 pr-3">{r.owner || "—"}</td>
                  <td className="py-2 pr-3">{r.country || "—"}</td>
                  <td className="py-2 pr-3">{r.members}</td>
                  <td className="py-2 pr-3">{r.ai_messages_month}</td>
                  <td className="py-2 pr-3">{r.whatsapp_month}</td>
                  <td className="py-2 pr-3">{r.limit_ai_messages}{r.custom_limit ? <span className="text-xs text-muted-foreground ml-1">(custom)</span> : ""}</td>
                  <td className="py-2 pr-3"><Button size="sm" variant="outline" onClick={() => { setEditing(r); setLimit(String(r.limit_ai_messages || "")); }} data-testid="customer-set-limit"><Settings2 className="h-4 w-4" /></Button></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <Dialog open={!!editing} onOpenChange={(v) => !v && setEditing(null)}>
        <DialogContent data-testid="admin-limit-dialog">
          <DialogHeader><DialogTitle>Monthly AI message limit</DialogTitle></DialogHeader>
          {editing && <div className="text-sm">{editing.name}</div>}
          <Input type="number" value={limit} onChange={(e) => setLimit(e.target.value)} placeholder="e.g. 5000" data-testid="admin-limit-input" />
          <DialogFooter><Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button><Button onClick={saveLimit} data-testid="admin-limit-save">Save</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
