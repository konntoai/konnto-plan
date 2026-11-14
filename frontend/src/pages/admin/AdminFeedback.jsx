import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader, SectionCard } from "@/components/common";
import { useApi } from "@/lib/api";
import { fmtAgo } from "@/lib/format";

export default function AdminFeedback() {
  const api = useApi();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  const load = async () => { setLoading(true); try { setRows((await api.get("/admin/feedback")).feedback); } catch (e) { toast.error(e.message); } finally { setLoading(false); } };
  useEffect(() => { load(); }, [api]);

  const setStatus = async (id, status) => { try { await api.patch(`/admin/feedback/${id}`, { status }); load(); } catch (e) { toast.error(e.message); } };

  const visible = rows.filter((r) => filter === "all" || r.status === filter);

  return (
    <div className="p-4 lg:p-8 max-w-[1000px] mx-auto space-y-4">
      <PageHeader title="Feedback" subtitle="Every note customers send us.">
        <Tabs value={filter} onValueChange={setFilter}><TabsList data-testid="feedback-filter-tabs"><TabsTrigger value="all">All</TabsTrigger><TabsTrigger value="new">New</TabsTrigger><TabsTrigger value="seen">Seen</TabsTrigger><TabsTrigger value="done">Done</TabsTrigger></TabsList></Tabs>
      </PageHeader>
      <SectionCard title="Messages" testid="feedback-card">
        {loading ? <Loader2 className="h-4 w-4 animate-spin" />
        : visible.length === 0 ? <div className="text-sm text-muted-foreground">Nothing yet.</div>
        : <div className="space-y-2">{visible.map((f) => (
            <div key={f.feedback_id} className="rounded-xl border border-border bg-[hsl(var(--surface-2))] p-3" data-testid="feedback-row">
              <div className="flex items-center gap-2 text-xs text-muted-foreground"><span className="font-medium text-foreground">{f.user_name}</span> · {f.user_email} · {fmtAgo(f.created_at)} · <span className="rounded-full border border-border px-2 py-0.5">{f.status}</span></div>
              <div className="mt-1 text-sm whitespace-pre-wrap">{f.text}</div>
              <div className="mt-2 flex gap-2">
                <Button size="sm" variant="outline" onClick={() => setStatus(f.feedback_id, "seen")} data-testid="feedback-mark-seen">Mark seen</Button>
                <Button size="sm" variant="outline" onClick={() => setStatus(f.feedback_id, "done")} data-testid="feedback-mark-done">Mark done</Button>
              </div>
            </div>
          ))}</div>}
      </SectionCard>
    </div>
  );
}
