import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Plus, Save, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { PageHeader, SectionCard } from "@/components/common";
import { useApi } from "@/lib/api";

const BLANK = { name: "", category: "Standard", billing: "flat", price: null, currency: "USD", interval: "month", seats_included: null, features: [], limits: {}, visible: false };

export default function AdminPlans() {
  const api = useApi();
  const [data, setData] = useState({ plans: [], categories: [] });
  const [loading, setLoading] = useState(true);
  const [edit, setEdit] = useState(null);
  const [featuresText, setFeaturesText] = useState("");

  const load = async () => { setLoading(true); try { setData(await api.get("/admin/plans")); } catch (e) { toast.error(e.message); } finally { setLoading(false); } };
  useEffect(() => { load(); }, [api]);

  const openEdit = (plan) => { setEdit(plan ? { ...plan } : { ...BLANK, category: data.categories[0] || "Standard" }); setFeaturesText((plan?.features || []).join("\n")); };
  const save = async () => {
    const body = { ...edit, features: featuresText.split("\n").map((x) => x.trim()).filter(Boolean) };
    try {
      if (edit.plan_id) await api.put(`/admin/plans/${edit.plan_id}`, body);
      else await api.post("/admin/plans", body);
      toast.success("Saved");
      setEdit(null); load();
    } catch (e) { toast.error(e.message); }
  };
  const archive = async (id) => { if (!window.confirm("Archive this plan?")) return; try { await api.del(`/admin/plans/${id}`); toast.success("Archived"); load(); } catch (e) { toast.error(e.message); } };

  return (
    <div className="p-4 lg:p-8 max-w-[1100px] mx-auto">
      <PageHeader title="Plans" subtitle="Internal — never shown to customers.">
        <Button onClick={() => openEdit(null)} data-testid="plan-new"><Plus className="h-4 w-4 mr-1" /> New plan</Button>
      </PageHeader>
      <SectionCard title="All plans" testid="plans-card">
        {loading ? <Loader2 className="h-4 w-4 animate-spin" />
        : data.plans.length === 0 ? <div className="text-sm text-muted-foreground">No plans yet.</div>
        : <div className="divide-y divide-border">{data.plans.map((p) => (
            <div key={p.plan_id} className="flex items-center gap-3 py-3" data-testid="plan-row">
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{p.name}</div>
                <div className="text-xs text-muted-foreground">{p.category} · {p.billing}{p.price ? ` · ${p.currency} ${p.price}/${p.interval}` : ""}</div>
              </div>
              <Button size="sm" variant="outline" onClick={() => openEdit(p)} data-testid="plan-edit">Edit</Button>
              <Button size="sm" variant="ghost" onClick={() => archive(p.plan_id)} data-testid="plan-archive"><Trash2 className="h-4 w-4 text-destructive" /></Button>
            </div>
          ))}</div>}
      </SectionCard>

      <Dialog open={!!edit} onOpenChange={(v) => !v && setEdit(null)}>
        <DialogContent data-testid="plan-dialog">
          <DialogHeader><DialogTitle>{edit?.plan_id ? "Edit plan" : "New plan"}</DialogTitle></DialogHeader>
          {edit && (
            <div className="space-y-3">
              <Input placeholder="Name" value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} data-testid="plan-name" />
              <Select value={edit.category} onValueChange={(v) => setEdit({ ...edit, category: v })}>
                <SelectTrigger data-testid="plan-category"><SelectValue /></SelectTrigger>
                <SelectContent>{data.categories.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
              <Select value={edit.billing} onValueChange={(v) => setEdit({ ...edit, billing: v })}>
                <SelectTrigger data-testid="plan-billing"><SelectValue /></SelectTrigger>
                <SelectContent><SelectItem value="flat">Flat</SelectItem><SelectItem value="per_seat">Per seat</SelectItem><SelectItem value="custom">Custom</SelectItem></SelectContent>
              </Select>
              <div className="grid grid-cols-2 gap-2">
                <Input type="number" placeholder="Price" value={edit.price ?? ""} onChange={(e) => setEdit({ ...edit, price: e.target.value === "" ? null : Number(e.target.value) })} data-testid="plan-price" />
                <Input placeholder="Currency" value={edit.currency} onChange={(e) => setEdit({ ...edit, currency: e.target.value })} data-testid="plan-currency" />
              </div>
              <Textarea rows={4} placeholder="Features — one per line" value={featuresText} onChange={(e) => setFeaturesText(e.target.value)} data-testid="plan-features" />
              <label className="flex items-center gap-2 text-sm"><Checkbox checked={edit.visible} onCheckedChange={(v) => setEdit({ ...edit, visible: Boolean(v) })} data-testid="plan-visible" /> Visible to customers (we recommend keeping this off)</label>
            </div>
          )}
          <DialogFooter><Button variant="outline" onClick={() => setEdit(null)}>Cancel</Button><Button onClick={save} data-testid="plan-save"><Save className="h-4 w-4 mr-1" /> Save</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
