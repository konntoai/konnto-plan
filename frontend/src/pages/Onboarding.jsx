import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { MessageCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Logo, Spinner, FullPageLoader } from "@/components/common";
import { useApi, PENDING_INVITE_KEY } from "@/lib/api";
import { useMe } from "@/context/MeContext";

export default function Onboarding() {
  const api = useApi();
  const navigate = useNavigate();
  const { me, loading, refresh } = useMe();
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [consent, setConsent] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (me?.user?.whatsapp) setPhone(me.user.whatsapp);
    if (me?.user?.name) setName(me.user.name);
  }, [me]);

  if (loading || !me) return <FullPageLoader />;
  const pending = localStorage.getItem(PENDING_INVITE_KEY);
  if (pending) return <Navigate to={`/join/${pending}`} replace />;
  if (!me.needs_onboarding) return <Navigate to="/app/chat" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      await api.post("/onboarding", { whatsapp: phone, consent, timezone: tz, name: me.user.name ? undefined : name });
      await refresh();
      navigate("/app/chat", { replace: true });
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4 py-10 hero-glow">
      <Logo className="mb-8" />
      <form onSubmit={submit} className="w-full max-w-[420px] rounded-2xl border border-border bg-card p-6 sm:p-7 shadow-sm" data-testid="onboarding-form">
        <div className="h-11 w-11 rounded-xl bg-emerald-50 text-emerald-700 grid place-items-center mb-4"><MessageCircle className="h-5 w-5" /></div>
        <h1 className="text-2xl font-semibold tracking-tight">What's your WhatsApp number?</h1>
        <p className="text-sm text-muted-foreground mt-1">That's the only question. KONNTO works out the rest as you talk.</p>
        {!me.user.name && (
          <Input data-testid="onboarding-name-input" placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} className="mt-5 h-12 text-base rounded-xl" />
        )}
        <Input data-testid="onboarding-whatsapp-input" inputMode="tel" autoFocus placeholder="+91 98765 43210" value={phone} onChange={(e) => setPhone(e.target.value)} className="mt-5 h-12 text-base rounded-xl" />
        <p className="text-xs text-muted-foreground mt-2">Include your country code, like +91, +1 or +44.</p>
        <label className="mt-5 flex items-start gap-3 text-sm cursor-pointer" htmlFor="consent">
          <Checkbox id="consent" checked={consent} onCheckedChange={(v) => setConsent(Boolean(v))} data-testid="onboarding-consent-checkbox" className="mt-0.5" />
          <span>KONNTO AI may message me on WhatsApp about my business. I can reply STOP any time.</span>
        </label>
        <Button data-testid="onboarding-continue-button" type="submit" className="w-full h-12 mt-6 btn-lift" disabled={busy || phone.replace(/\D/g, "").length < 8 || (!me.user.name && !name.trim())}>
          {busy ? <Spinner /> : null} Continue
        </Button>
      </form>
    </div>
  );
}
