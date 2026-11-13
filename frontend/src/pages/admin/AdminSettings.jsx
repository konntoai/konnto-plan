import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Save, Copy, Phone, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader, SectionCard } from "@/components/common";
import { useApi } from "@/lib/api";

export default function AdminSettings() {
  const api = useApi();
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ default_monthly_ai_messages: "", default_monthly_whatsapp: "" });
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get("/admin/settings").then((d) => { setData(d); setForm({ default_monthly_ai_messages: d.settings.default_monthly_ai_messages || "", default_monthly_whatsapp: d.settings.default_monthly_whatsapp || "" }); }).catch((e) => toast.error(e.message)); }, [api]);

  const save = async () => {
    setBusy(true);
    try {
      await api.put("/admin/settings", {
        default_monthly_ai_messages: form.default_monthly_ai_messages ? Number(form.default_monthly_ai_messages) : null,
        default_monthly_whatsapp: form.default_monthly_whatsapp ? Number(form.default_monthly_whatsapp) : null,
      });
      toast.success("Saved");
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  const copy = (v) => { navigator.clipboard.writeText(v); toast.success("Copied"); };

  if (!data) return <div className="p-6"><Loader2 className="h-5 w-5 animate-spin" /></div>;

  return (
    <div className="p-4 lg:p-6 max-w-[900px] mx-auto space-y-4">
      <PageHeader title="Settings" subtitle="Platform-wide defaults and WhatsApp status.">
        <Button onClick={save} disabled={busy} data-testid="admin-settings-save"><Save className="h-4 w-4 mr-1" /> {busy ? "Saving…" : "Save"}</Button>
      </PageHeader>
      <SectionCard title="Default monthly limits" testid="admin-defaults-card">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <label>AI messages / month<Input className="mt-1" type="number" value={form.default_monthly_ai_messages} onChange={(e) => setForm({ ...form, default_monthly_ai_messages: e.target.value })} data-testid="admin-default-ai" /></label>
          <label>WhatsApp messages / month<Input className="mt-1" type="number" value={form.default_monthly_whatsapp} onChange={(e) => setForm({ ...form, default_monthly_whatsapp: e.target.value })} data-testid="admin-default-wa" /></label>
        </div>
      </SectionCard>
      <SectionCard title="WhatsApp Business API" testid="admin-wa-card">
        <div className="flex items-center gap-2 text-sm">
          {data.whatsapp.configured
            ? <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 px-2.5 py-1 text-xs"><Check className="h-3.5 w-3.5" /> Connected</span>
            : <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200 px-2.5 py-1 text-xs"><X className="h-3.5 w-3.5" /> Not connected</span>}
          <span className="text-muted-foreground"><Phone className="h-3.5 w-3.5 inline mr-1" /> {data.whatsapp.display_number || "No number set"}</span>
        </div>
        <div className="mt-3 space-y-2 text-sm">
          <label className="block text-xs text-muted-foreground">Webhook URL</label>
          <div className="flex gap-2"><Input value={data.whatsapp.webhook_url || ""} readOnly data-testid="admin-wa-webhook" /><Button size="icon" variant="outline" aria-label="Copy" onClick={() => copy(data.whatsapp.webhook_url)}><Copy className="h-4 w-4" /></Button></div>
          <label className="block text-xs text-muted-foreground">Verify token</label>
          <div className="flex gap-2"><Input value={data.whatsapp.verify_token || ""} readOnly data-testid="admin-wa-verify" /><Button size="icon" variant="outline" aria-label="Copy" onClick={() => copy(data.whatsapp.verify_token)}><Copy className="h-4 w-4" /></Button></div>
        </div>
      </SectionCard>
    </div>
  );
}
