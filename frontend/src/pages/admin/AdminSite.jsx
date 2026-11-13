import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader, SectionCard } from "@/components/common";
import { useApi } from "@/lib/api";

const FIELDS = [
  ["hero_title", "Hero headline", 2],
  ["hero_subtitle", "Hero subtitle", 3],
  ["hero_cta", "Primary CTA label", 1],
  ["how_title", "How it works title", 1],
  ["whatsapp_title", "WhatsApp section title", 1],
  ["whatsapp_body", "WhatsApp section body", 3],
  ["industries_title", "Industries title", 1],
  ["trust_title", "Trust section title", 1],
  ["final_title", "Final CTA title", 1],
  ["final_body", "Final CTA body", 2],
  ["footer_note", "Footer note", 1],
];

export default function AdminSite() {
  const api = useApi();
  const [site, setSite] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get("/admin/site").then((r) => setSite(r.site)).catch((e) => toast.error(e.message)); }, [api]);
  const save = async () => {
    setBusy(true);
    try { const r = await api.put("/admin/site", { content: site }); setSite(r.site); toast.success("Saved"); } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  if (!site) return <div className="p-6"><Loader2 className="h-5 w-5 animate-spin" /></div>;
  return (
    <div className="p-4 lg:p-6 max-w-[900px] mx-auto space-y-4">
      <PageHeader title="Website" subtitle="The public landing page text.">
        <Button onClick={save} disabled={busy} data-testid="site-save"><Save className="h-4 w-4 mr-1" /> {busy ? "Saving…" : "Save"}</Button>
      </PageHeader>
      <SectionCard title="Copy" testid="site-copy-card">
        <div className="space-y-3">
          {FIELDS.map(([k, label, rows]) => (
            <label key={k} className="text-sm block">{label}{rows > 1
              ? <Textarea className="mt-1" rows={rows} value={site[k] || ""} onChange={(e) => setSite({ ...site, [k]: e.target.value })} data-testid={`site-${k}`} />
              : <Input className="mt-1" value={site[k] || ""} onChange={(e) => setSite({ ...site, [k]: e.target.value })} data-testid={`site-${k}`} />}</label>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
