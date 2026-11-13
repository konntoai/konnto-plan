import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { BookOpen, Loader2, Plus, Trash2, Building2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader, EmptyState, SectionCard } from "@/components/common";
import { useApi } from "@/lib/api";

export default function KnowledgePage() {
  const api = useApi();
  const [data, setData] = useState(null);
  const [fact, setFact] = useState("");
  const [rule, setRule] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setData(await api.get("/knowledge")); } catch (e) { toast.error(e.message); }
  }, [api]);
  useEffect(() => { load(); }, [load]);

  const addFact = async (e) => {
    e.preventDefault();
    if (!fact.trim()) return;
    setBusy(true);
    try { await api.post("/knowledge", { text: fact }); setFact(""); toast.success("Remembered"); load(); } catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };
  const addRule = async (e) => {
    e.preventDefault();
    if (!rule.trim()) return;
    setBusy(true);
    try { await api.post("/rules", { text: rule }); setRule(""); toast.success("Rule saved"); load(); } catch (err) { toast.error(err.message); } finally { setBusy(false); }
  };
  const removeFact = async (id) => { try { await api.del(`/knowledge/${id}`); toast.success("Removed"); load(); } catch (e) { toast.error(e.message); } };
  const removeRule = async (id) => { try { await api.del(`/rules/${id}`); toast.success("Removed"); load(); } catch (e) { toast.error(e.message); } };

  if (!data) return <div className="p-6"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>;

  return (
    <div className="p-4 lg:p-6 max-w-[1000px] mx-auto space-y-5" data-testid="knowledge-page">
      <PageHeader title="Business brain" subtitle="What KONNTO knows about your business — rules it follows and facts it remembers." />

      <SectionCard title="Business" testid="knowledge-business">
        <div className="flex items-start gap-3">
          <div className="h-11 w-11 rounded-xl bg-accent text-accent-foreground grid place-items-center"><Building2 className="h-5 w-5" /></div>
          <div className="text-sm">
            <div className="font-medium">{data.business.name}</div>
            <div className="text-muted-foreground">{[data.business.industry, data.business.country, data.business.currency, data.business.timezone].filter(Boolean).join(" · ")}</div>
            {data.business.description && <div className="mt-1 text-muted-foreground">{data.business.description}</div>}
          </div>
        </div>
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-2 text-sm">
          <div className="rounded-xl bg-background border border-border px-3 py-2"><div className="text-muted-foreground text-xs">Facts</div><div className="font-semibold text-lg">{data.facts.length}</div></div>
          <div className="rounded-xl bg-background border border-border px-3 py-2"><div className="text-muted-foreground text-xs">Rules</div><div className="font-semibold text-lg">{data.rules.length}</div></div>
          <div className="rounded-xl bg-background border border-border px-3 py-2"><div className="text-muted-foreground text-xs">Documents</div><div className="font-semibold text-lg">{data.documents}</div></div>
        </div>
      </SectionCard>

      <SectionCard title="Rules KONNTO follows" testid="knowledge-rules">
        <form onSubmit={addRule} className="flex gap-2 mb-3">
          <Input placeholder="e.g. Tell Priya whenever a payment is overdue" value={rule} onChange={(e) => setRule(e.target.value)} data-testid="rule-input" />
          <Button type="submit" disabled={busy || !rule.trim()} data-testid="rule-add"><Plus className="h-4 w-4 mr-1" /> Add</Button>
        </form>
        {data.rules.length === 0 ? <EmptyState icon={BookOpen} title="No rules yet" body="KONNTO learns from how you work. Add a rule and it will follow it." testid="rules-empty" />
        : <ul className="space-y-2">{data.rules.map((r) => (
            <li key={r.rule_id} className="flex items-center gap-3 rounded-xl border border-border bg-background px-3 py-2" data-testid="rule-row">
              <div className="flex-1 text-sm">{r.text}</div>
              <Button size="icon" variant="ghost" onClick={() => removeRule(r.rule_id)} aria-label="Remove" data-testid="rule-remove"><Trash2 className="h-4 w-4 text-destructive" /></Button>
            </li>
          ))}</ul>}
      </SectionCard>

      <SectionCard title="Facts KONNTO remembers" testid="knowledge-facts">
        <form onSubmit={addFact} className="flex gap-2 mb-3">
          <Input placeholder="e.g. Our warehouse is closed every Sunday" value={fact} onChange={(e) => setFact(e.target.value)} data-testid="fact-input" />
          <Button type="submit" disabled={busy || !fact.trim()} data-testid="fact-add"><Plus className="h-4 w-4 mr-1" /> Remember</Button>
        </form>
        {data.facts.length === 0 ? <EmptyState icon={BookOpen} title="No facts yet" body="Facts help KONNTO answer naturally and keep team conversations grounded." testid="facts-empty" />
        : <ul className="space-y-2">{data.facts.map((f) => (
            <li key={f.fact_id} className="flex items-center gap-3 rounded-xl border border-border bg-background px-3 py-2" data-testid="fact-row">
              <div className="flex-1 text-sm">{f.text}<div className="text-xs text-muted-foreground mt-0.5">{f.created_by_name}</div></div>
              <Button size="icon" variant="ghost" onClick={() => removeFact(f.fact_id)} aria-label="Remove" data-testid="fact-remove"><Trash2 className="h-4 w-4 text-destructive" /></Button>
            </li>
          ))}</ul>}
      </SectionCard>
    </div>
  );
}
