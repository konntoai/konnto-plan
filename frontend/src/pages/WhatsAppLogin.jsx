import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { MessageCircle, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { Logo, Spinner } from "@/components/common";
import { publicFetch, APP_TOKEN_KEY, PENDING_INVITE_KEY } from "@/lib/api";

export default function WhatsAppLogin() {
  const navigate = useNavigate();
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState("phone");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  const request = async (e) => {
    e?.preventDefault();
    setBusy(true);
    setNotice("");
    try {
      await publicFetch("/auth/whatsapp/request", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ phone }) });
      setStep("code");
      toast.success("Code sent on WhatsApp");
    } catch (err) {
      setNotice(err.message);
    } finally {
      setBusy(false);
    }
  };

  const verify = async (e) => {
    e?.preventDefault();
    setBusy(true);
    try {
      const res = await publicFetch("/auth/whatsapp/verify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ phone, code }) });
      localStorage.setItem(APP_TOKEN_KEY, res.token);
      const pending = localStorage.getItem(PENDING_INVITE_KEY);
      window.location.href = pending ? `/join/${pending}` : "/app/chat";
    } catch (err) {
      toast.error(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4 py-10">
      <Link to="/" className="mb-8"><Logo /></Link>
      <div className="w-full max-w-[400px] rounded-2xl border border-border bg-card p-6 shadow-sm" data-testid="whatsapp-auth-card">
        <div className="h-11 w-11 rounded-xl bg-emerald-50 text-emerald-700 grid place-items-center mb-4"><MessageCircle className="h-5 w-5" /></div>
        <h1 className="text-xl font-semibold">Continue with WhatsApp</h1>
        {step === "phone" ? (
          <form onSubmit={request} className="mt-5 space-y-4">
            <p className="text-sm text-muted-foreground">We'll send a 6-digit code to your WhatsApp.</p>
            <Input data-testid="whatsapp-auth-phone-input" inputMode="tel" placeholder="+91 98765 43210" value={phone} onChange={(e) => setPhone(e.target.value)} className="h-12 text-base rounded-xl" />
            {notice && <div data-testid="whatsapp-auth-notice" className="rounded-xl border border-amber-200 bg-amber-50 text-amber-900 text-sm px-3 py-2">{notice}</div>}
            <Button data-testid="whatsapp-auth-send-code-button" type="submit" className="w-full h-12" disabled={busy || phone.replace(/\D/g, "").length < 8}>{busy ? <Spinner /> : null} Send code</Button>
          </form>
        ) : (
          <form onSubmit={verify} className="mt-5 space-y-4">
            <p className="text-sm text-muted-foreground">Enter the code we sent to {phone}.</p>
            <InputOTP maxLength={6} value={code} onChange={setCode} data-testid="whatsapp-auth-otp-input">
              <InputOTPGroup>{[0, 1, 2, 3, 4, 5].map((i) => <InputOTPSlot key={i} index={i} className="h-12 w-12 text-lg" />)}</InputOTPGroup>
            </InputOTP>
            <Button data-testid="whatsapp-auth-verify-button" type="submit" className="w-full h-12" disabled={busy || code.length < 6}>{busy ? <Spinner /> : null} Verify and continue</Button>
            <button type="button" onClick={() => setStep("phone")} className="text-sm text-muted-foreground hover:text-foreground">Use a different number</button>
          </form>
        )}
      </div>
      <button onClick={() => navigate("/sign-in")} className="mt-6 text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1" data-testid="whatsapp-auth-back"><ArrowLeft className="h-4 w-4" /> Use email or Google instead</button>
    </div>
  );
}
