import { useEffect, useRef, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import { MessageCircle, Brain, Zap, ShieldCheck, Undo2, Lock, Download, Menu, Check, Clock, ArrowRight, Send, X, Mic, Store, HardHat, Stethoscope, Palette, Truck, Factory, UtensilsCrossed, Briefcase } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Logo, KonntoMark, FullPageLoader } from "@/components/common";
import { useSession } from "@/components/auth/session";
import { publicFetch, readSSE, API, PENDING_INVITE_KEY } from "@/lib/api";

const INDUSTRY_ICONS = [Store, HardHat, Stethoscope, Palette, Truck, Factory, UtensilsCrossed, Briefcase];
const STEP_ICONS = [MessageCircle, Brain, Zap];
const TRUST_ICONS = [ShieldCheck, Undo2, Lock, Download];

const fade = { initial: { opacity: 0, y: 10 }, whileInView: { opacity: 1, y: 0 }, viewport: { once: true, margin: "-60px" }, transition: { duration: 0.35, ease: [0.2, 0.8, 0.2, 1] } };

function ProductMock() {
  return (
    <div className="relative rounded-[28px] border border-border bg-card p-4 sm:p-5 shadow-[0_20px_60px_-30px_rgba(15,118,110,0.35)]" data-testid="landing-product-mock">
      <div className="flex items-center gap-2 pb-3 border-b border-border">
        <KonntoMark size={30} />
        <div>
          <div className="text-sm font-semibold">KONNTO</div>
          <div className="text-xs text-muted-foreground">Sharma Hardware</div>
        </div>
      </div>
      <div className="space-y-3 pt-4 text-sm">
        <div className="ml-auto max-w-[85%] rounded-2xl rounded-tr-md bg-primary/10 border border-primary/15 px-3 py-2">
          Supplier promised 200 cement bags by Thursday. Remind me Wednesday.
        </div>
        <div className="max-w-[90%] rounded-2xl rounded-tl-md bg-white border border-border px-3 py-2">
          Got it. I've prepared a promise and a reminder. Tap Save to keep them.
        </div>
        <div className="max-w-[92%] rounded-2xl border border-border bg-white p-3">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-primary">Promise</div>
          <div className="font-medium mt-0.5">Gupta Cement — 200 bags</div>
          <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground"><Clock className="h-3.5 w-3.5" /> Due Thu, 18:00 · Remind Wed, 09:00</div>
          <div className="mt-3 grid grid-cols-3 gap-2">
            <span className="h-9 rounded-lg bg-primary text-primary-foreground grid place-items-center text-xs font-medium">Save</span>
            <span className="h-9 rounded-lg border border-border grid place-items-center text-xs font-medium">Edit</span>
            <span className="h-9 rounded-lg border border-border grid place-items-center text-xs font-medium">Skip</span>
          </div>
        </div>
        <div className="max-w-[92%] rounded-2xl border border-border bg-white p-3">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-amber-700">Approval</div>
          <div className="font-medium mt-0.5">Ramesh: order steel rods — ₹12,400</div>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span className="h-8 px-3 rounded-lg border border-border grid place-items-center">Allow once</span>
            <span className="h-8 px-3 rounded-lg bg-primary text-primary-foreground grid place-items-center">Always under ₹15,000</span>
            <span className="h-8 px-3 rounded-lg border border-border grid place-items-center">Don't allow</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function HelpWidget() {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState([{ role: "assistant", text: "Hi! Ask me anything about KONNTO AI." }]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);
  useEffect(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), [msgs, open]);

  const send = async (q) => {
    const question = (q ?? text).trim();
    if (!question || busy) return;
    setText("");
    setBusy(true);
    const history = msgs.slice(1).map((m) => ({ role: m.role, text: m.text }));
    setMsgs((m) => [...m, { role: "user", text: question }, { role: "assistant", text: "" }]);
    try {
      const res = await fetch(`${API}/public/help`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: question, history }) });
      if (!res.ok) throw new Error("busy");
      await readSSE(res, (ev) => {
        if (ev.type === "delta") setMsgs((m) => { const c = [...m]; c[c.length - 1] = { ...c[c.length - 1], text: c[c.length - 1].text + ev.text }; return c; });
      });
    } catch {
      setMsgs((m) => { const c = [...m]; c[c.length - 1] = { role: "assistant", text: "Sorry, I can't answer right now. Please try again soon." }; return c; });
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {!open && (
        <button data-testid="landing-help-open-button" onClick={() => setOpen(true)} className="btn-lift fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-primary text-primary-foreground px-4 h-12 shadow-lg">
          <MessageCircle className="h-5 w-5" /> Ask KONNTO
        </button>
      )}
      {open && (
        <div data-testid="landing-help-panel" className="fixed bottom-4 right-4 left-4 sm:left-auto z-50 sm:w-[380px] rounded-2xl border border-border bg-card shadow-2xl flex flex-col max-h-[70vh]">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <div className="flex items-center gap-2"><KonntoMark size={26} /><span className="font-semibold text-sm">Ask KONNTO</span></div>
            <button aria-label="Close help" data-testid="landing-help-close-button" onClick={() => setOpen(false)} className="h-9 w-9 grid place-items-center rounded-lg hover:bg-secondary"><X className="h-4 w-4" /></button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3 text-sm scrollbar-thin">
            {msgs.map((m, i) => (
              <div key={i} className={m.role === "user" ? "ml-auto max-w-[85%] rounded-2xl rounded-tr-md bg-primary/10 border border-primary/15 px-3 py-2" : "max-w-[90%] rounded-2xl rounded-tl-md bg-white border border-border px-3 py-2 whitespace-pre-wrap"}>
                {m.text || <span className="flex gap-1 py-1"><span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" /></span>}
              </div>
            ))}
            {msgs.length === 1 && (
              <div className="flex flex-wrap gap-2">
                {["Is KONNTO free?", "Do my suppliers need the app?", "Who can see my data?"].map((s) => (
                  <button key={s} onClick={() => send(s)} className="rounded-full border border-border bg-secondary px-3 py-1.5 text-xs hover:bg-accent" data-testid="landing-help-suggestion">{s}</button>
                ))}
              </div>
            )}
            <div ref={endRef} />
          </div>
          <form onSubmit={(e) => { e.preventDefault(); send(); }} className="flex gap-2 p-3 border-t border-border">
            <Input data-testid="landing-help-input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Type a question" className="h-11 rounded-xl" />
            <Button data-testid="landing-help-send-button" type="submit" size="icon" disabled={busy} aria-label="Send"><Send className="h-4 w-4" /></Button>
          </form>
        </div>
      )}
    </>
  );
}

export default function Landing() {
  const { isLoaded, isSignedIn } = useSession();
  const [site, setSite] = useState(null);
  useEffect(() => {
    publicFetch("/public/site").then((d) => setSite(d.site)).catch(() => setSite({}));
  }, []);

  if (isLoaded && isSignedIn) {
    const pending = localStorage.getItem(PENDING_INVITE_KEY);
    return <Navigate to={pending ? `/join/${pending}` : "/app/chat"} replace />;
  }
  if (!site) return <FullPageLoader />;
  const s = site;
  const nav = [{ href: "#how", label: "How it works" }, { href: "#whatsapp", label: "WhatsApp" }, { href: "#trust", label: "Security" }];

  return (
    <div className="min-h-screen bg-background" data-testid="landing-page">
      <header className="sticky top-0 z-30 border-b border-border/70 bg-background/90 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link to="/" data-testid="landing-logo-link"><Logo /></Link>
          <nav className="hidden md:flex items-center gap-7 text-sm text-muted-foreground">
            {nav.map((n) => <a key={n.href} href={n.href} className="hover:text-foreground transition-colors">{n.label}</a>)}
          </nav>
          <div className="hidden md:flex items-center gap-2">
            <Button asChild variant="ghost" data-testid="landing-signin-button"><Link to="/sign-in">Sign in</Link></Button>
            <Button asChild className="btn-lift" data-testid="landing-start-button"><Link to="/sign-up">{s.hero_cta || "Start free"}</Link></Button>
          </div>
          <Sheet>
            <SheetTrigger asChild>
              <button className="md:hidden h-11 w-11 grid place-items-center rounded-xl hover:bg-secondary" aria-label="Open menu" data-testid="landing-menu-button"><Menu className="h-5 w-5" /></button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[300px] bg-card">
              <div className="mt-8 flex flex-col gap-4">
                {nav.map((n) => <a key={n.href} href={n.href} className="text-base">{n.label}</a>)}
                <Button asChild variant="outline" data-testid="landing-mobile-signin"><Link to="/sign-in">Sign in</Link></Button>
                <Button asChild data-testid="landing-mobile-start"><Link to="/sign-up">{s.hero_cta || "Start free"}</Link></Button>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </header>

      <section className="hero-glow noise">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-14 md:py-20 grid lg:grid-cols-12 gap-10 items-center">
          <motion.div {...fade} className="lg:col-span-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-white px-3 py-1 text-xs font-medium text-primary mb-5">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" /> For any business, anywhere
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight leading-[1.05]" data-testid="landing-hero-title">{s.hero_title}</h1>
            <p className="mt-5 text-base md:text-lg text-muted-foreground max-w-xl leading-7" data-testid="landing-hero-subtitle">{s.hero_subtitle}</p>
            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              <Button asChild size="lg" className="btn-lift" data-testid="landing-hero-start-button"><Link to="/sign-up">{s.hero_cta || "Start free"} <ArrowRight className="h-4 w-4" /></Link></Button>
              <Button asChild size="lg" variant="outline" data-testid="landing-hero-how-button"><a href="#how">See how it works</a></Button>
            </div>
            <div className="mt-7 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground">
              {(s.proof_points || []).map((p) => <span key={p} className="inline-flex items-center gap-1.5"><Check className="h-4 w-4 text-primary" />{p}</span>)}
            </div>
          </motion.div>
          <motion.div {...fade} transition={{ duration: 0.45, delay: 0.1 }} className="lg:col-span-6">
            <ProductMock />
          </motion.div>
        </div>
      </section>

      <section id="how" className="py-14 md:py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <motion.h2 {...fade} className="text-2xl md:text-4xl font-semibold tracking-tight">{s.how_title}</motion.h2>
          <div className="mt-8 grid md:grid-cols-3 gap-4">
            {(s.steps || []).map((st, i) => {
              const Icon = STEP_ICONS[i % 3];
              return (
                <motion.div {...fade} transition={{ duration: 0.35, delay: i * 0.08 }} key={i} className="rounded-2xl border border-border bg-card p-6" data-testid={`landing-step-${i}`}>
                  <div className="flex items-center justify-between">
                    <div className="h-11 w-11 rounded-xl bg-accent text-accent-foreground grid place-items-center"><Icon className="h-5 w-5" /></div>
                    <span className="font-display text-sm text-muted-foreground">0{i + 1}</span>
                  </div>
                  <h3 className="mt-5 text-lg font-semibold">{st.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground leading-6">{st.body}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      <section id="whatsapp" className="py-14 md:py-20 bg-card border-y border-border">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 grid lg:grid-cols-2 gap-10 items-center">
          <motion.div {...fade}>
            <h2 className="text-2xl md:text-4xl font-semibold tracking-tight">{s.whatsapp_title}</h2>
            <p className="mt-4 text-muted-foreground leading-7 max-w-lg">{s.whatsapp_body}</p>
            <div className="mt-6 flex items-center gap-3 text-sm text-muted-foreground"><Mic className="h-4 w-4 text-primary" /> Voice notes in any language understood.</div>
          </motion.div>
          <motion.div {...fade} className="rounded-[24px] bg-[#EFEAE2] p-5 border border-border">
            <div className="max-w-[85%] rounded-xl rounded-tl-sm bg-white px-3 py-2 text-sm shadow-sm">
              <div className="text-[11px] font-semibold text-primary mb-1">KONNTO AI</div>
              Reminder: send the quote to Mehta Builders. Due today, 17:00.
            </div>
            <div className="mt-1.5 grid grid-cols-3 gap-1.5 max-w-[85%]">
              {["Done", "Delayed", "Need help"].map((b) => <div key={b} className="rounded-lg bg-white text-[#0F766E] text-sm font-medium text-center py-2 shadow-sm">{b}</div>)}
            </div>
            <div className="mt-4 ml-auto max-w-[70%] rounded-xl rounded-tr-sm bg-[#D9FDD3] px-3 py-2 text-sm shadow-sm">Done</div>
            <div className="mt-3 max-w-[85%] rounded-xl rounded-tl-sm bg-white px-3 py-2 text-sm shadow-sm">Great — marked done. I told Priya.</div>
          </motion.div>
        </div>
      </section>

      <section className="py-14 md:py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <motion.h2 {...fade} className="text-2xl md:text-4xl font-semibold tracking-tight">{s.industries_title}</motion.h2>
          <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3">
            {(s.industries || []).map((ind, i) => {
              const Icon = INDUSTRY_ICONS[i % INDUSTRY_ICONS.length];
              return (
                <motion.div {...fade} key={ind} className={`rounded-2xl border border-border bg-card p-5 ${i === 0 ? "md:col-span-2 md:row-span-1" : ""}`}>
                  <Icon className="h-5 w-5 text-primary" />
                  <div className="mt-4 font-medium text-sm">{ind}</div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      <section id="trust" className="py-14 md:py-20 bg-card border-y border-border">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <motion.h2 {...fade} className="text-2xl md:text-4xl font-semibold tracking-tight">{s.trust_title}</motion.h2>
          <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {(s.trust || []).map((t, i) => {
              const Icon = TRUST_ICONS[i % 4];
              return (
                <motion.div {...fade} key={i} className="rounded-2xl border border-border bg-background p-6">
                  <Icon className="h-5 w-5 text-primary" />
                  <h3 className="mt-4 font-semibold">{t.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground leading-6">{t.body}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="py-16 md:py-24">
        <motion.div {...fade} className="mx-auto max-w-3xl px-4 sm:px-6 text-left sm:text-center">
          <h2 className="text-3xl md:text-5xl font-semibold tracking-tight">{s.final_title}</h2>
          <p className="mt-4 text-muted-foreground text-lg">{s.final_body}</p>
          <Button asChild size="lg" className="mt-8 btn-lift" data-testid="landing-final-start-button"><Link to="/sign-up">{s.hero_cta || "Start free"} <ArrowRight className="h-4 w-4" /></Link></Button>
        </motion.div>
      </section>

      <footer className="border-t border-border bg-card">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-8 flex flex-col sm:flex-row gap-4 sm:items-center sm:justify-between text-sm text-muted-foreground">
          <div className="flex items-center gap-3"><Logo compact /><span>{s.footer_note}</span></div>
          <div className="flex gap-5">
            <Link to="/terms" data-testid="landing-terms-link" className="hover:text-foreground">Terms</Link>
            <Link to="/privacy-policy" data-testid="landing-privacy-link" className="hover:text-foreground">Privacy</Link>
            <Link to="/sign-in" className="hover:text-foreground">Sign in</Link>
          </div>
        </div>
      </footer>
      <HelpWidget />
    </div>
  );
}
