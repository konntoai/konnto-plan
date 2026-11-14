import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { FileText, Upload, Loader2, Download, Trash2, PlusSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, EmptyState } from "@/components/common";
import { useApi } from "@/lib/api";
import { fmtAgo, downloadBlob } from "@/lib/format";

export default function DocumentsPage() {
  const api = useApi();
  const inputRef = useRef(null);
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(null);
  const [detail, setDetail] = useState(null);
  const [uploading, setUploading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await api.get(`/documents${q ? `?q=${encodeURIComponent(q)}` : ""}`); setDocs(r.documents || []); }
    catch (e) { toast.error(e.message); } finally { setLoading(false); }
  }, [api, q]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (!open) { setDetail(null); return; } api.get(`/documents/${open}`).then(setDetail).catch((e) => toast.error(e.message)); }, [api, open]);

  const upload = async (files) => {
    setUploading(true);
    try {
      for (const f of files) {
        const fd = new FormData(); fd.append("file", f); fd.append("visibility", "org");
        await api.upload("/documents", fd);
      }
      toast.success("Uploaded");
      load();
    } catch (e) { toast.error(e.message); } finally { setUploading(false); if (inputRef.current) inputRef.current.value = ""; }
  };

  const download = async (d) => {
    try { const blob = await api.blob(`/documents/${d.doc_id}/file`); downloadBlob(blob, d.filename); } catch (e) { toast.error(e.message); }
  };

  const remove = async (d) => {
    if (!window.confirm(`Delete ${d.filename}?`)) return;
    try { await api.del(`/documents/${d.doc_id}`); toast.success("Deleted"); setOpen(null); load(); } catch (e) { toast.error(e.message); }
  };

  const saveFound = async () => {
    try { const r = await api.post(`/documents/${open}/save-items`); toast.success(`${r.created || 0} saved`); api.get(`/documents/${open}`).then(setDetail); }
    catch (e) { toast.error(e.message); }
  };

  return (
    <div className="p-4 lg:p-8 max-w-[1100px] mx-auto" data-testid="documents-page">
      <PageHeader title="Documents" subtitle="PDFs, Word, Excel — KONNTO reads them so you don’t have to.">
        <input ref={inputRef} type="file" className="hidden" multiple accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt" onChange={(e) => e.target.files && upload(Array.from(e.target.files))} data-testid="documents-file-input" />
        <Button onClick={() => inputRef.current?.click()} disabled={uploading} data-testid="documents-upload-button">{uploading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Upload className="h-4 w-4 mr-1" />} Upload</Button>
      </PageHeader>
      <Input placeholder="Search documents" value={q} onChange={(e) => setQ(e.target.value)} className="mb-4" data-testid="documents-search" />
      {loading ? <div className="space-y-2">{[0,1,2].map((i) => <Skeleton key={i} className="h-20 rounded-2xl" />)}</div>
      : docs.length === 0 ? <EmptyState icon={FileText} title="No documents yet" body="Upload a PDF, Word or Excel — KONNTO will summarise and even spot tasks inside." testid="documents-empty" />
      : (
        <div className="space-y-2">
          {docs.map((d) => (
            <button key={d.doc_id} onClick={() => setOpen(d.doc_id)} className="w-full text-left rounded-2xl surface surface-hover p-3.5 flex items-start gap-3" data-testid="document-row">
              <div className="h-10 w-10 rounded-xl bg-accent text-primary ring-1 ring-primary/15 grid place-items-center shrink-0"><FileText className="h-5 w-5" /></div>
              <div className="min-w-0 flex-1">
                <div className="font-medium truncate">{d.filename}</div>
                <div className="text-xs text-muted-foreground">{d.uploaded_by_name} · {fmtAgo(d.created_at)}</div>
                {d.summary && <div className="text-sm text-muted-foreground mt-1 line-clamp-2">{d.summary}</div>}
              </div>
            </button>
          ))}
        </div>
      )}

      <Sheet open={!!open} onOpenChange={(v) => !v && setOpen(null)}>
        <SheetContent className="w-full sm:w-[520px] overflow-y-auto scrollbar-thin" data-testid="document-detail-sheet">
          <SheetHeader><SheetTitle>Document</SheetTitle></SheetHeader>
          {!detail ? <Loader2 className="h-4 w-4 animate-spin mt-6" />
          : (
            <div className="space-y-4 py-2">
              <div><div className="font-semibold text-lg">{detail.filename}</div><div className="text-xs text-muted-foreground">{detail.doc_type || "document"}</div></div>
              {detail.summary && <div className="rounded-xl border border-border bg-[hsl(var(--surface-2))] p-3 text-sm whitespace-pre-wrap">{detail.summary}</div>}
              {detail.key_details?.length > 0 && (
                <div><div className="text-sm font-semibold mb-1">Key details</div><ul className="text-sm space-y-1 list-disc pl-5">{detail.key_details.map((k, i) => <li key={i}>{typeof k === "string" ? k : `${k.label || "•"}: ${k.value || ""}`}</li>)}</ul></div>
              )}
              {detail.found_items?.length > 0 && (
                <div className="rounded-2xl border border-primary/25 bg-accent/50 p-3.5">
                  <div className="text-sm font-semibold">Found {detail.found_items.length} item{detail.found_items.length > 1 ? "s" : ""} inside</div>
                  <ul className="text-sm mt-1 space-y-0.5">{detail.found_items.map((i, idx) => <li key={idx}>• {i.title}</li>)}</ul>
                  <Button size="sm" className="mt-2" onClick={saveFound} data-testid="document-save-found"><PlusSquare className="h-4 w-4 mr-1" /> Save them to Work</Button>
                </div>
              )}
              <div className="flex gap-2 pt-2 border-t border-border">
                <Button variant="outline" onClick={() => download(detail)} data-testid="document-download"><Download className="h-4 w-4 mr-1" /> Download</Button>
                <Button variant="outline" className="text-destructive ml-auto" onClick={() => remove(detail)} data-testid="document-delete"><Trash2 className="h-4 w-4 mr-1" /> Delete</Button>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
