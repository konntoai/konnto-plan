import { Loader2, Clock, AlertTriangle, PauseCircle, CheckCircle2, Circle, XCircle } from "lucide-react";
import { initials } from "@/lib/format";
import { cn } from "@/lib/utils";

export const Logo = ({ className = "", compact = false }) => (
  <div className={cn("flex items-center gap-2 select-none", className)} data-testid="konnto-logo">
    <div className="h-8 w-8 rounded-[10px] bg-primary text-primary-foreground grid place-items-center font-display font-bold text-[15px] shadow-sm">K</div>
    {!compact && (
      <span className="font-display font-semibold tracking-tight text-[17px] text-foreground">
        KONNTO <span className="text-primary">AI</span>
      </span>
    )}
  </div>
);

export const KonntoMark = ({ size = 28 }) => (
  <div style={{ width: size, height: size }} className="shrink-0 rounded-[9px] bg-primary text-primary-foreground grid place-items-center font-display font-bold text-[13px]">
    K
  </div>
);

export const FullPageLoader = ({ label = "Loading…" }) => (
  <div className="min-h-screen grid place-items-center bg-background" data-testid="full-page-loader">
    <div className="flex flex-col items-center gap-3 text-muted-foreground">
      <Logo compact />
      <div className="flex items-center gap-2 text-sm">
        <Loader2 className="h-4 w-4 animate-spin" /> {label}
      </div>
    </div>
  </div>
);

export const Spinner = ({ className = "" }) => <Loader2 className={cn("h-4 w-4 animate-spin", className)} />;

const STATE = {
  due: { label: "Due", cls: "bg-amber-50 text-amber-800 border-amber-200", Icon: Clock },
  overdue: { label: "Overdue", cls: "bg-red-50 text-red-700 border-red-200", Icon: AlertTriangle },
  stuck: { label: "Stuck", cls: "bg-slate-100 text-slate-700 border-slate-200", Icon: PauseCircle },
  done: { label: "Done", cls: "bg-emerald-50 text-emerald-700 border-emerald-200", Icon: CheckCircle2 },
  open: { label: "Open", cls: "bg-white text-slate-600 border-slate-200", Icon: Circle },
  cancelled: { label: "Cancelled", cls: "bg-white text-slate-500 border-slate-200 line-through", Icon: XCircle },
};

export const StatusPill = ({ state = "open", label, className = "" }) => {
  const s = STATE[state] || STATE.open;
  const Icon = s.Icon;
  return (
    <span data-testid={`status-pill-${state}`} className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium border whitespace-nowrap", s.cls, className)}>
      <Icon className="h-3.5 w-3.5" />
      {label || s.label}
    </span>
  );
};

export const stateDot = (state) =>
  ({ due: "bg-amber-500", overdue: "bg-red-500", stuck: "bg-slate-400", done: "bg-emerald-600", open: "bg-primary/60", cancelled: "bg-slate-300" }[state] || "bg-primary/60");

export const PersonAvatar = ({ name, size = 36, tone = "default" }) => {
  const tones = {
    default: "bg-accent text-accent-foreground",
    partner: "bg-amber-50 text-amber-800 border border-amber-200",
    owner: "bg-primary text-primary-foreground",
  };
  return (
    <div style={{ width: size, height: size, fontSize: Math.max(11, size * 0.36) }} className={cn("shrink-0 rounded-full grid place-items-center font-semibold", tones[tone] || tones.default)}>
      {initials(name)}
    </div>
  );
};

export const EmptyState = ({ icon: Icon, title, body, children, testid = "empty-state" }) => (
  <div data-testid={testid} className="rounded-2xl border border-dashed border-border bg-card px-5 py-8 text-left">
    {Icon && (
      <div className="h-10 w-10 rounded-xl bg-accent text-accent-foreground grid place-items-center mb-3">
        <Icon className="h-5 w-5" />
      </div>
    )}
    <h3 className="text-base font-semibold">{title}</h3>
    {body && <p className="mt-1 text-sm text-muted-foreground max-w-md">{body}</p>}
    {children && <div className="mt-4 flex flex-wrap gap-2">{children}</div>}
  </div>
);

export const PageHeader = ({ title, subtitle, children }) => (
  <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between mb-5">
    <div>
      <h1 className="text-2xl sm:text-[28px] font-semibold tracking-tight" data-testid="page-title">{title}</h1>
      {subtitle && <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>}
    </div>
    {children && <div className="flex flex-wrap gap-2">{children}</div>}
  </div>
);

export const SectionCard = ({ title, action, children, className = "", testid }) => (
  <section data-testid={testid} className={cn("rounded-2xl border border-border bg-card", className)}>
    {(title || action) && (
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
        {action}
      </div>
    )}
    <div className="px-4 pb-4">{children}</div>
  </section>
);
