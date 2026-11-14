import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Download, ShieldAlert, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription, DialogTrigger } from "@/components/ui/dialog";
import { PageHeader, SectionCard } from "@/components/common";
import { useApi } from "@/lib/api";
import { downloadBlob } from "@/lib/format";

export default function PrivacyPage() {
  const api = useApi();
  const [s, setS] = useState(null);
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get("/privacy/summary").then(setS).catch((e) => toast.error(e.message)); }, [api]);

  const exportData = async () => {
    try {
      const blob = await api.blob("/privacy/export");
      downloadBlob(blob, "konnto-my-data.json");
      toast.success("Export downloaded");
    } catch (e) { toast.error(e.message); }
  };

  const deleteData = async () => {
    setBusy(true);
    try {
      const r = await api.post("/privacy/delete", { confirm });
      toast.success("Done");
      if (r.account_removed) window.location.href = "/";
      else window.location.reload();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  if (!s) return <div className="p-6"><Loader2 className="h-5 w-5 animate-spin" /></div>;

  const c = s.counts;

  return (
    <div className="p-4 lg:p-8 max-w-[900px] mx-auto space-y-5" data-testid="privacy-page">
      <PageHeader title="Privacy" subtitle="See, export or delete your data. Your call." />

      <SectionCard title="What KONNTO holds about you here" testid="privacy-summary">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-sm">
          {[["KONNTO messages", c.konnto_messages], ["Private notes", c.private_notes], ["Items created", c.items_created], ["Team messages", c.team_messages], ["Documents", c.documents], ["Files", c.files]].map(([label, n]) => (
            <div key={label} className="rounded-2xl bg-[hsl(var(--surface-2))] border border-border px-3 py-2.5" data-testid={`privacy-count-${label.replace(/\s/g, "-").toLowerCase()}`}>
              <div className="text-xs text-muted-foreground">{label}</div><div className="text-lg font-semibold">{n}</div>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Export" testid="privacy-export">
        <p className="text-sm text-muted-foreground mb-3">Download everything KONNTO holds about you in this business as a single JSON file.</p>
        <Button onClick={exportData} data-testid="privacy-export-button"><Download className="h-4 w-4 mr-1" /> Export my data</Button>
      </SectionCard>

      <SectionCard title="Delete" testid="privacy-delete">
        <p className="text-sm text-muted-foreground mb-3">
          {s.is_owner ? "You're the owner. Deleting will remove the whole business and everyone in it." : "Your KONNTO chat, private notes and files for this business will be removed."}
        </p>
        <Dialog onOpenChange={(v) => !v && setConfirm("")}>
          <DialogTrigger asChild><Button variant="outline" className="text-destructive" data-testid="privacy-delete-button"><Trash2 className="h-4 w-4 mr-1" /> Delete my data</Button></DialogTrigger>
          <DialogContent data-testid="privacy-delete-dialog">
            <DialogHeader><DialogTitle className="flex items-center gap-2"><ShieldAlert className="h-5 w-5 text-destructive" /> Are you sure?</DialogTitle><DialogDescription>This cannot be undone. Type DELETE to confirm.</DialogDescription></DialogHeader>
            <Input value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="DELETE" data-testid="privacy-delete-confirm" />
            <DialogFooter>
              <Button onClick={deleteData} disabled={busy || confirm !== "DELETE"} variant="outline" className="text-destructive" data-testid="privacy-delete-submit">{busy ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null} Delete permanently</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </SectionCard>
    </div>
  );
}
