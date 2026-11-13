import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Send, History, Rocket, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { PageHeader, SectionCard } from "@/components/common";
import { useApi } from "@/lib/api";
import { fmtAgo } from "@/lib/format";

const FIELDS = [
  { key: "personality", label: "Personality", rows: 5, hint: "How should KONNTO sound and act with customers?" },
  { key: "rules", label: "Rules it must follow", rows: 5, hint: "Hard rules (e.g. never discuss pricing publicly)." },
  { key: "knowledge", label: "Knowledge", rows: 6, hint: "General business knowledge, product info, boundaries." },
  { key: "pricing_answers", label: "How to answer pricing", rows: 3, hint: "Keep this short. Pricing is never shown to customers." },
  { key: "welcome_message", label: "Welcome message", rows: 3, hint: "Use {name} for the first name." },
];

export default function AdminBrain() {
  const api = useApi();
  const [data, setData] = useState(null);
  const [faqs, setFaqs] = useState([]);
  const [testQ, setTestQ] = useState("");
  const [testA, setTestA] = useState("");
  const [testBusy, setTestBusy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [versions, setVersions] = useState([]);

  const load = async () => { try { const d = await api.get("/admin/brain"); setData(d); setFaqs(d.draft.faqs || []); } catch (e) { toast.error(e.message); } };
  useEffect(() => { load(); }, [api]);
  const loadVersions = async () => { try { setVersions((await api.get("/admin/brain/versions")).versions); } catch (e) { toast.error(e.message); } };

  const setField = (k, v) => setData((d) => ({ ...d, draft: { ...d.draft, [k]: v } }));

  const saveDraft = async () => {
    setBusy(true);
    try { const r = await api.put("/admin/brain", { ...data.draft, faqs }); setData((d) => ({ ...d, draft: r.draft })); toast.success("Draft saved"); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const publish = async (note) => {
    setBusy(true);
    try { await api.put("/admin/brain", { ...data.draft, faqs }); await api.post("/admin/brain/publish", { note }); toast.success("Published"); load(); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const runTest = async (mode) => {
    if (!testQ.trim()) return;
    setTestBusy(true); setTestA("");
    try { const r = await api.post("/admin/brain/test", { question: testQ, mode }); setTestA(r.answer); }
    catch (e) { toast.error(e.message); } finally { setTestBusy(false); }
  };
  const restore = async (vid) => {
    try { await api.post(`/admin/brain/restore/${vid}`); toast.success("Loaded as draft"); load(); } catch (e) { toast.error(e.message); }
  };

  if (!data) return <div className="p-6"><Loader2 className="h-5 w-5 animate-spin" /></div>;

  return (
    <div className="p-4 lg:p-6 max-w-[1100px] mx-auto" data-testid="admin-brain-page">
      <PageHeader title="Teach KONNTO" subtitle={`Draft v${data.version + (data.has_unpublished ? " (unsaved changes)" : "")}`}>
        <Dialog>
          <DialogTrigger asChild><Button variant="outline" onClick={loadVersions} data-testid="brain-versions-button"><History className="h-4 w-4 mr-1" /> Versions</Button></DialogTrigger>
          <DialogContent data-testid="brain-versions-dialog">
            <DialogHeader><DialogTitle>Version history</DialogTitle><DialogDescription>Any version can be loaded back as a draft.</DialogDescription></DialogHeader>
            <div className="max-h-[300px] overflow-y-auto scrollbar-thin space-y-2">{versions.length === 0 ? <div className="text-sm text-muted-foreground">No versions yet.</div>
              : versions.map((v) => (
                <div key={v.version_id} className="flex items-center gap-3 rounded-xl border border-border bg-background px-3 py-2">
                  <div className="flex-1"><div className="text-sm font-medium">v{v.version}</div><div className="text-xs text-muted-foreground">{fmtAgo(v.published_at)} · {v.published_by}</div>{v.note && <div className="text-xs mt-1">{v.note}</div>}</div>
                  <Button size="sm" variant="outline" onClick={() => restore(v.version_id)} data-testid="brain-restore">Restore</Button>
                </div>
              ))}</div>
          </DialogContent>
        </Dialog>
        <Button variant="outline" onClick={saveDraft} disabled={busy} data-testid="brain-save-draft">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save draft"}</Button>
        <Button onClick={() => publish("")} disabled={busy} data-testid="brain-publish"><Rocket className="h-4 w-4 mr-1" /> Publish</Button>
      </PageHeader>

      <Tabs defaultValue="edit">
        <TabsList><TabsTrigger value="edit" data-testid="brain-tab-edit">Edit</TabsTrigger><TabsTrigger value="test" data-testid="brain-tab-test">Test</TabsTrigger><TabsTrigger value="faqs" data-testid="brain-tab-faqs">FAQs</TabsTrigger></TabsList>
        <TabsContent value="edit" className="space-y-4 mt-3">
          {FIELDS.map((f) => (
            <SectionCard key={f.key} title={f.label} testid={`brain-field-${f.key}`}>
              <Textarea rows={f.rows} value={data.draft[f.key] || ""} onChange={(e) => setField(f.key, e.target.value)} data-testid={`brain-input-${f.key}`} />
              <div className="text-xs text-muted-foreground mt-2">{f.hint}</div>
            </SectionCard>
          ))}
        </TabsContent>
        <TabsContent value="test" className="mt-3">
          <SectionCard title="Try the current draft" testid="brain-test-card">
            <Textarea rows={3} value={testQ} onChange={(e) => setTestQ(e.target.value)} placeholder="Ask something a customer or an owner might ask…" data-testid="brain-test-question" />
            <div className="mt-2 flex gap-2">
              <Button variant="outline" onClick={() => runTest("help")} disabled={testBusy} data-testid="brain-test-help">As help assistant</Button>
              <Button variant="outline" onClick={() => runTest("business")} disabled={testBusy} data-testid="brain-test-business">As business assistant</Button>
            </div>
            {testBusy && <div className="mt-3 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin inline" /> Thinking…</div>}
            {testA && <div className="mt-3 rounded-xl border border-border bg-background p-3 text-sm whitespace-pre-wrap" data-testid="brain-test-answer">{testA}</div>}
          </SectionCard>
        </TabsContent>
        <TabsContent value="faqs" className="mt-3">
          <SectionCard title="Common questions" testid="brain-faqs-card">
            <div className="space-y-2">
              {faqs.map((f, i) => (
                <div key={i} className="rounded-xl border border-border bg-background p-3 space-y-2" data-testid="brain-faq-row">
                  <Input value={f.q} placeholder="Question" onChange={(e) => { const c = [...faqs]; c[i] = { ...c[i], q: e.target.value }; setFaqs(c); }} />
                  <Textarea rows={2} value={f.a} placeholder="Answer" onChange={(e) => { const c = [...faqs]; c[i] = { ...c[i], a: e.target.value }; setFaqs(c); }} />
                  <Button size="sm" variant="ghost" className="text-destructive" onClick={() => setFaqs(faqs.filter((_, j) => j !== i))} data-testid="brain-faq-remove"><Trash2 className="h-4 w-4" /> Remove</Button>
                </div>
              ))}
              <Button variant="outline" onClick={() => setFaqs([...faqs, { q: "", a: "" }])} data-testid="brain-faq-add"><Plus className="h-4 w-4 mr-1" /> Add a FAQ</Button>
            </div>
          </SectionCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
