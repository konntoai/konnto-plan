import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { MessageCircle, Smartphone, Users } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@clerk/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Logo, Spinner, FullPageLoader } from "@/components/common";
import { useSession } from "@/components/auth/session";
import { publicFetch, useApi, PENDING_INVITE_KEY } from "@/lib/api";

export default function Join() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { isLoaded, isSignedIn } = useSession();
  const api = useApi();
  const [invite, setInvite] = useState(null);
  const [error, setError] = useState("");
  const [phone, setPhone] = useState("");
  const [consent, setConsent] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    publicFetch(`/public/invites/${token}`).then(setInvite).catch((e) => { setError(e.message); localStorage.removeItem(PENDING_INVITE_KEY); });
  }, [token]);

  useEffect(() => {
    if (!isSignedIn) return;
    api.get("/me").then((me) => { if (me?.user?.whatsapp) setPhone(me.user.whatsapp); }).catch(() => {});
  }, [isSignedIn, api]);

  if (!isLoaded || (!invite && !error)) return <FullPageLoader />;

  const goAuth = (path) => {
    localStorage.setItem(PENDING_INVITE_KEY, token);
    navigate(path);
  };

  const accept = async () => {
    setBusy(true);
    try {
      await api.post(`/invites/${token}/accept`, { phone: phone || null, consent });
      localStorage.removeItem(PENDING_INVITE_KEY);
      toast.success(`Welcome to ${invite.business}`);
      window.location.href = "/app/chat";
    } catch (e) {
      if (e.status === 409) {
        localStorage.removeItem(PENDING_INVITE_KEY);
        navigate("/app/chat");
      }
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-background hero-glow flex flex-col items-center justify-center px-4 py-10">
      <Link to="/" className="mb-8"><Logo /></Link>
      <div className="w-full max-w-[440px] rounded-2xl border border-border bg-card p-6 sm:p-7 shadow-sm" data-testid="join-card">
        {error ? (
          <>
            <h1 className="text-xl font-semibold">This link isn't active</h1>
            <p className="text-sm text-muted-foreground mt-2" data-testid="join-error">{error}</p>
            <Button asChild className="mt-6 w-full"><Link to="/">Go to KONNTO</Link></Button>
          </>
        ) : (
          <>
            <div className="h-11 w-11 rounded-xl bg-accent text-accent-foreground grid place-items-center mb-4"><Users className="h-5 w-5" /></div>
            <p className="text-sm text-muted-foreground">{invite.invited_by} invited you</p>
            <h1 className="text-2xl font-semibold tracking-tight mt-1" data-testid="join-business-name">Join {invite.business}</h1>
            <p className="text-sm mt-3">Hi {invite.name}{invite.job ? ` — ${invite.job}` : ""}. KONNTO keeps track of your work and reminds you, so nothing is forgotten.</p>
            {invite.access_reason && <p className="text-xs text-muted-foreground mt-2">{invite.access_reason}</p>}

            {invite.wa_join_url && (
              <Button asChild className="w-full h-12 mt-6 bg-[#16A34A] hover:bg-[#15803D]" data-testid="join-whatsapp-button">
                <a href={invite.wa_join_url} target="_blank" rel="noreferrer"><MessageCircle className="h-4 w-4" /> Join on WhatsApp</a>
              </Button>
            )}
            {invite.wa_join_url && <p className="text-xs text-muted-foreground mt-2">Opens WhatsApp with a join message. Just press send.</p>}

            <div className="mt-6 rounded-xl border border-border p-4">
              <div className="flex items-center gap-2 font-medium text-sm"><Smartphone className="h-4 w-4 text-primary" /> Join in the app</div>
              {isSignedIn ? (
                <div className="mt-3 space-y-3">
                  <Input data-testid="join-phone-input" inputMode="tel" placeholder="Your WhatsApp number (+91 …)" value={phone} onChange={(e) => setPhone(e.target.value)} className="h-11 rounded-xl" />
                  <label className="flex items-start gap-3 text-sm cursor-pointer" htmlFor="join-consent">
                    <Checkbox id="join-consent" checked={consent} onCheckedChange={(v) => setConsent(Boolean(v))} data-testid="join-consent-checkbox" className="mt-0.5" />
                    <span>KONNTO AI may message me on WhatsApp for {invite.business}.</span>
                  </label>
                  <Button data-testid="join-accept-button" className="w-full h-11" onClick={accept} disabled={busy}>{busy ? <Spinner /> : null} Join {invite.business}</Button>
                </div>
              ) : (
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <Button data-testid="join-signup-button" onClick={() => goAuth("/sign-up")}>Sign up</Button>
                  <Button data-testid="join-signin-button" variant="outline" onClick={() => goAuth("/sign-in")}>Sign in</Button>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
