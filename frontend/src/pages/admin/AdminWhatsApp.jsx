import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Copy, Phone, Check, X, RefreshCw, Send, FileCheck2, ExternalLink, Circle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { SectionCard, TonePill } from "@/components/common";
import { useApi } from "@/lib/api";

const STATUS_TONE = { APPROVED: "done", PENDING: "pending", IN_APPEAL: "pending", REJECTED: "overdue", PAUSED: "stuck", DISABLED: "overdue", NOT_SUBMITTED: "open", FAILED: "overdue" };
const STATUS_LABEL = { APPROVED: "Approved", PENDING: "Waiting for Meta", IN_APPEAL: "In appeal", REJECTED: "Rejected", PAUSED: "Paused", DISABLED: "Disabled", NOT_SUBMITTED: "Not sent yet", FAILED: "Failed" };

const STEPS = [
  { t: "Create a Meta app", b: <>Open <a className="text-primary underline" href="https://developers.facebook.com/apps/" target="_blank" rel="noreferrer">developers.facebook.com/apps</a> → <b>Create app</b> → pick <b>“Connect with customers through WhatsApp”</b>. Create a business portfolio when asked. You land on <b>WhatsApp → API Setup</b>.</> },
  { t: "Choose the number", b: <>For the demo, Meta's free <b>test number</b> is fine: under <b>To</b>, add up to 5 phones that should receive messages (each one confirms a code). For real customers, choose <b>Add phone number</b> and verify your business number by SMS — it must not be in use on the normal WhatsApp app.</> },
  { t: "Copy two IDs", b: <>On the same API Setup page copy the <b>Phone number ID</b> and the <b>WhatsApp Business Account ID</b>. Note the phone number itself too (the “display number”).</> },
  { t: "Create a permanent token", b: <>Go to <a className="text-primary underline" href="https://business.facebook.com/settings/system-users" target="_blank" rel="noreferrer">Business settings → System users</a> → <b>Add</b> (Admin). Click <b>Assign assets</b>: your app (full control) and your WhatsApp account (full control). Then <b>Generate token</b> → pick the app → expiry <b>Never</b> → tick <b>whatsapp_business_messaging</b> and <b>whatsapp_business_management</b>. Copy it straight away.</> },
  { t: "Copy the App Secret", b: <>In the app: <b>App settings → Basic → App secret → Show</b>.</> },
  { t: "Give the keys to KONNTO", b: <>Tell the builder chat you're ready — a secure card will ask for the token, Phone number ID, WhatsApp Business Account ID, App Secret and display number. Never paste them into chat.</> },
  { t: "Connect the webhook", b: <>In the app: <b>WhatsApp → Configuration → Webhook → Edit</b>. Paste the <b>Webhook URL</b> and <b>Verify token</b> shown below → <b>Verify and save</b>. Then under <b>Webhook fields</b> click <b>Subscribe</b> next to <b>messages</b>.</> },
  { t: "Check, send templates, test", b: <>Come back here: <b>Check connection</b>, then <b>Send templates to Meta</b> (approval usually takes minutes to a few hours), then send a <b>test message</b> to your phone.</> },
  { t: "Switch on each person", b: <>Add each person's real number on the <b>Team</b> page (your own in <b>Settings</b>). Each person sends <b>hi</b> to the KONNTO number once — that switches WhatsApp on for them, and tasks, chases and approvals start arriving.</> },
];

export function AdminWhatsApp({ wa }) {
  const api = useApi();
  const [check, setCheck] = useState(null);
  const [checking, setChecking] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [testPhone, setTestPhone] = useState("");
  const [testing, setTesting] = useState(false);
  const copy = (v) => { navigator.clipboard.writeText(v || ""); toast.success("Copied"); };

  const runCheck = useCallback(async (quiet = false) => {
    setChecking(true);
    try {
      const r = await api.get("/admin/whatsapp/check");
      setCheck(r);
      if (!quiet) r.errors?.length ? toast.error(r.errors[0]) : r.configured ? toast.success("Meta connection looks good") : toast.warning("Not connected yet — follow the setup guide below");
    } catch (e) { toast.error(e.message); } finally { setChecking(false); }
  }, [api]);

  useEffect(() => { if (wa.configured) runCheck(true); }, [wa.configured, runCheck]);

  const submit = async () => {
    setSubmitting(true);
    try {
      const r = await api.post("/admin/whatsapp/templates/submit", {});
      if (r.error) toast.error(r.error);
      else {
        const failed = r.results.filter((x) => x.status === "FAILED");
        failed.length ? toast.error(`${failed[0].name}: ${failed[0].note}`) : toast.success("Templates sent to Meta for approval");
      }
      runCheck(true);
    } catch (e) { toast.error(e.message); } finally { setSubmitting(false); }
  };

  const sendTest = async () => {
    setTesting(true);
    try {
      const r = await api.post("/admin/whatsapp/test", { phone: testPhone });
      r.ok ? toast.success("Test sent — check that phone's WhatsApp") : toast.error(r.error);
    } catch (e) { toast.error(e.message); } finally { setTesting(false); }
  };

  const connected = check ? check.configured : wa.configured;
  const missing = check?.missing || [];

  return (
    <SectionCard title="WhatsApp Business API" testid="admin-wa-card">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        {connected ? <TonePill tone="done" icon={Check} testid="admin-wa-status">Connected</TonePill> : <TonePill tone="due" icon={X} testid="admin-wa-status">Not connected</TonePill>}
        <span className="text-muted-foreground"><Phone className="h-3.5 w-3.5 inline mr-1" />{check?.number?.display_phone_number || wa.display_number || "No number set"}</span>
        {check?.number?.verified_name && <span className="text-muted-foreground">· {check.number.verified_name}</span>}
        {check?.number?.quality_rating && <TonePill tone="open">Quality {check.number.quality_rating}</TonePill>}
        <Button size="sm" variant="outline" className="ml-auto" onClick={() => runCheck(false)} disabled={checking} data-testid="admin-wa-check">
          {checking ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} Check connection
        </Button>
      </div>
      {missing.length > 0 && <p className="mt-2 text-xs text-muted-foreground" data-testid="admin-wa-missing">Still needed: {missing.join(", ")}.</p>}
      {check?.errors?.map((e) => <p key={e} className="mt-2 text-xs text-status-overdue" data-testid="admin-wa-error">{e}</p>)}

      <div className="mt-4 grid gap-3 sm:grid-cols-2 text-sm">
        <div className="min-w-0">
          <label className="block text-xs text-muted-foreground mb-1">Webhook URL</label>
          <div className="flex gap-2"><Input value={wa.webhook_url || ""} readOnly data-testid="admin-wa-webhook" /><Button size="icon" variant="outline" aria-label="Copy webhook URL" onClick={() => copy(wa.webhook_url)} data-testid="admin-wa-copy-webhook"><Copy className="h-4 w-4" /></Button></div>
        </div>
        <div className="min-w-0">
          <label className="block text-xs text-muted-foreground mb-1">Verify token</label>
          <div className="flex gap-2"><Input value={wa.verify_token || ""} readOnly data-testid="admin-wa-verify" /><Button size="icon" variant="outline" aria-label="Copy verify token" onClick={() => copy(wa.verify_token)} data-testid="admin-wa-copy-verify"><Copy className="h-4 w-4" /></Button></div>
        </div>
      </div>

      <div className="mt-5">
        <div className="flex flex-wrap items-center gap-2">
          <div className="font-medium text-sm">Standard messages (templates)</div>
          <span className="text-xs text-muted-foreground">Needed to reach someone who hasn't messaged KONNTO in the last 24 hours.</span>
          <Button size="sm" className="ml-auto" onClick={submit} disabled={submitting || !connected} data-testid="admin-wa-submit-templates">
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileCheck2 className="h-4 w-4" />} Send templates to Meta
          </Button>
        </div>
        <div className="mt-2 divide-y divide-border rounded-xl border border-border" data-testid="admin-wa-templates">
          {(check?.templates?.length ? check.templates : (wa.templates || []).map((t) => ({ ...t, status: connected ? "NOT_SUBMITTED" : null }))).map((t) => (
            <div key={t.name} className="flex items-start gap-3 px-3 py-2.5 text-sm" data-testid={`admin-wa-template-${t.name}`}>
              <div className="min-w-0 flex-1">
                <div className="font-mono text-xs">{t.name}</div>
                <div className="text-xs text-muted-foreground break-words">{t.body}</div>
              </div>
              {t.status && <TonePill tone={STATUS_TONE[t.status] || "open"}>{STATUS_LABEL[t.status] || t.status}</TonePill>}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5">
        <div className="font-medium text-sm">Send a test message</div>
        <p className="text-xs text-muted-foreground">Sends Meta's built-in “Hello World” — works before KONNTO's templates are approved. With the test number, the phone must be on Meta's allowed list.</p>
        <div className="mt-2 flex gap-2">
          <Input placeholder="+91 98765 43210" value={testPhone} onChange={(e) => setTestPhone(e.target.value)} data-testid="admin-wa-test-phone" />
          <Button onClick={sendTest} disabled={testing || !connected || !testPhone.trim()} data-testid="admin-wa-test-send">
            {testing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />} Send test
          </Button>
        </div>
      </div>

      <Accordion type="single" collapsible defaultValue={connected ? undefined : "guide"} className="mt-5">
        <AccordionItem value="guide" className="border-border">
          <AccordionTrigger className="text-sm" data-testid="admin-wa-guide-toggle">Step-by-step setup guide (about 20 minutes)</AccordionTrigger>
          <AccordionContent>
            <ol className="space-y-3" data-testid="admin-wa-guide">
              {STEPS.map((s, i) => (
                <li key={s.t} className="flex gap-3 text-sm">
                  <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-primary/15 text-xs font-semibold text-primary">{i + 1}</span>
                  <div className="min-w-0"><div className="font-medium">{s.t}</div><div className="text-muted-foreground leading-6">{s.b}</div></div>
                </li>
              ))}
            </ol>
            <a href="https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started" target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-1 text-xs text-primary hover:underline">
              Meta's own guide <ExternalLink className="h-3 w-3" />
            </a>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </SectionCard>
  );
}

export default AdminWhatsApp;
