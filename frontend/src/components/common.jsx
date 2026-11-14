import { Loader2, Clock, AlertTriangle, PauseCircle, CheckCircle2, Circle, XCircle } from "lucide-react";
import { initials } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Logo as BrandLogo, KonntoTile } from "@/components/brand/Logo";
import { KonntoOrb } from "@/components/brand/KonntoOrb";

export { KonntoOrb, KonntoTile };

export const Logo = (props) => <BrandLogo {...props} />;

/** Small AI presence used as the assistant avatar. */
export const KonntoMark = ({ size = 28, state = "idle" }) => <KonntoOrb size={size} state={state} />;

export const FullPageLoader = ({ label = "Opening KONNTO…" }) => (
  <div className="min-h-screen grid place-items-center bg-background app-ambient" data-testid="full-page-loader">
    <div className="flex flex-col items-center gap-5 text-muted-foreground">
      <KonntoOrb size={72} state="thinking" />
      <div className="eyebrow text-muted-foreground">{label}</div>
    </div>
  </div>
);

export const Spinner = ({ className = "" }) => <Loader2 className={cn("h-4 w-4 animate-spin", className)} />;

const STATE = {
  due: { label: "Due", tone: "due", Icon: Clock },
  overdue: { label: "Overdue", tone: "overdue", Icon: AlertTriangle },
  stuck: { label: "Stuck", tone: "stuck", Icon: PauseCircle },
  done: { label: "Done", tone: "done", Icon: CheckCircle2 },
  open: { label: "Open", tone: "open", Icon: Circle },
  cancelled: { label: "Cancelled", tone: "stuck", Icon: XCircle },
};

export const TONE_CLASS = {
  overdue: "bg-status-overdue/10 text-status-overdue border-status-overdue/25",
  due: "bg-status-due/10 text-status-due border-status-due/25",
  stuck: "bg-status-stuck/10 text-status-stuck border-status-stuck/25",
  done: "bg-status-done/10 text-status-done border-status-done/25",
  open: "bg-status-open/10 text-status-open border-status-open/25",
  pending: "bg-status-pending/10 text-status-pending border-status-pending/25",
  decided: "bg-status-decided/10 text-status-decided border-status-decided/25",
};

export const TonePill = ({ tone = "open", icon: Icon, children, className = "", testid }) => (
  <span data-testid={testid} className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium border whitespace-nowrap", TONE_CLASS[tone] || TONE_CLASS.open, className)}>
    {Icon && <Icon className="h-3.5 w-3.5" />}
    {children}
  </span>
);

export const StatusPill = ({ state = "open", label, className = "" }) => {
  const s = STATE[state] || STATE.open;
  return (
    <TonePill tone={s.tone} icon={s.Icon} testid={`status-pill-${state}`} className={cn(state === "cancelled" && "line-through", className)}>
      {label || s.label}
    </TonePill>
  );
};

export const stateDot = (state) =>
  ({ due: "bg-status-due", overdue: "bg-status-overdue shadow-[0_0_10px_hsl(var(--status-overdue)/0.7)]", stuck: "bg-status-stuck", done: "bg-status-done", open: "bg-status-open shadow-[0_0_10px_hsl(var(--status-open)/0.6)]", cancelled: "bg-muted-foreground/40" }[state] || "bg-status-open");

export const PersonAvatar = ({ name, size = 36, tone = "default" }) => {
  const tones = {
    default: "bg-accent text-accent-foreground ring-1 ring-primary/15",
    partner: "bg-status-due/10 text-status-due ring-1 ring-status-due/25",
    owner: "bg-brand-gradient text-white ring-1 ring-white/15 shadow-[0_6px_18px_-6px_hsl(var(--glow-blue))]",
  };
  return (
    <div style={{ width: size, height: size, fontSize: Math.max(11, size * 0.36) }} className={cn("shrink-0 rounded-full grid place-items-center font-display font-bold", tones[tone] || tones.default)}>
      {initials(name)}
    </div>
  );
};

export const EmptyState = ({ icon: Icon, title, body, children, testid = "empty-state", orb = false }) => (
  <div data-testid={testid} className="relative overflow-hidden rounded-3xl border border-dashed border-primary/25 bg-card/60 px-5 py-8 text-left">
    <div className="absolute -top-16 -right-16 h-40 w-40 rounded-full bg-primary/10 blur-3xl pointer-events-none" aria-hidden />
    {orb ? (
      <div className="mb-5"><KonntoOrb size={64} state="idle" ripple /></div>
    ) : Icon ? (
      <div className="h-11 w-11 rounded-2xl bg-accent text-accent-foreground grid place-items-center mb-4 ring-1 ring-primary/15">
        <Icon className="h-5 w-5" />
      </div>
    ) : null}
    <h3 className="text-base sm:text-lg font-display font-bold">{title}</h3>
    {body && <p className="mt-1.5 text-sm text-muted-foreground max-w-md leading-relaxed">{body}</p>}
    {children && <div className="mt-5 flex flex-wrap gap-2">{children}</div>}
  </div>
);

export const PageHeader = ({ title, subtitle, eyebrow, children }) => (
  <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between mb-6 animate-fade-up">
    <div className="min-w-0">
      {eyebrow && <div className="eyebrow text-primary mb-2">{eyebrow}</div>}
      <h1 className="text-[26px] sm:text-[32px] font-display font-extrabold tracking-tight leading-tight" data-testid="page-title">{title}</h1>
      {subtitle && <p className="text-sm sm:text-[15px] text-muted-foreground mt-1.5 max-w-2xl">{subtitle}</p>}
    </div>
    {children && <div className="flex flex-wrap gap-2">{children}</div>}
  </div>
);

export const SectionCard = ({ title, action, children, className = "", testid, icon: Icon }) => (
  <section data-testid={testid} className={cn("rounded-3xl surface", className)}>
    {(title || action) && (
      <div className="flex items-center justify-between gap-3 px-4 sm:px-5 pt-4 sm:pt-5 pb-2">
        <h2 className="flex items-center gap-2 text-[13px] font-display font-bold tracking-wide uppercase text-muted-foreground">
          {Icon && <Icon className="h-4 w-4 text-primary" />}
          {title}
        </h2>
        {action}
      </div>
    )}
    <div className="px-4 sm:px-5 pb-4 sm:pb-5">{children}</div>
  </section>
);
