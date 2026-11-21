import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader, SectionCard } from "@/components/common";
import { AdminWhatsApp } from "@/pages/admin/AdminWhatsApp";
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

  if (!data) return <div className="p-6"><Loader2 className="h-5 w-5 animate-spin" /></div>;

  return (
    <div className="p-4 lg:p-8 max-w-[900px] mx-auto space-y-4">
      <PageHeader title="Settings" subtitle="Platform-wide defaults and WhatsApp status.">
        <Button onClick={save} disabled={busy} data-testid="admin-settings-save"><Save className="h-4 w-4 mr-1" /> {busy ? "Saving…" : "Save"}</Button>
      </PageHeader>
      <SectionCard title="Default monthly limits" testid="admin-defaults-card">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <label>AI messages / month<Input className="mt-1" type="number" value={form.default_monthly_ai_messages} onChange={(e) => setForm({ ...form, default_monthly_ai_messages: e.target.value })} data-testid="admin-default-ai" /></label>
          <label>WhatsApp messages / month<Input className="mt-1" type="number" value={form.default_monthly_whatsapp} onChange={(e) => setForm({ ...form, default_monthly_whatsapp: e.target.value })} data-testid="admin-default-wa" /></label>
        </div>
      </SectionCard>
      <AdminWhatsApp wa={data.whatsapp} />
    </div>
  );
}
