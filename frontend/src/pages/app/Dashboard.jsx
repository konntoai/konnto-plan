import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Clock, PauseCircle, CheckCircle2, Users, ShieldCheck, ArrowRight, CalendarClock, GitBranch } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, StatusPill, PersonAvatar, SectionCard, EmptyState, KonntoOrb, stateDot } from "@/components/common";
import { useApi } from "@/lib/api";
import { fmtWhen } from "@/lib/format";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const COUNTER_META = [
  { key: "overdue", label: "Overdue", icon: AlertTriangle, tone: "overdue" },
  { key: "due_today", label: "Due today", icon: Clock, tone: "due" },
  { key: "stuck", label: "Stuck", icon: PauseCircle, tone: "stuck" },
  { key: "done_week", label: "Done this week", icon: CheckCircle2, tone: "done" },
];

const TONE_TEXT = { overdue: "text-status-overdue", due: "text-status-due", stuck: "text-status-stuck", done: "text-status-done" };
const TONE_BG = { overdue: "bg-status-overdue/10", due: "bg-status-due/10", stuck: "bg-status-stuck/10", done: "bg-status-done/10" };
const TONE_GLOW = { overdue: "bg-status-overdue/20", due: "bg-status-due/20", stuck: "bg-status-stuck/15", done: "bg-status-done/20" };

function ItemRow({ item }) {
  return (
    <li className="flex items-start gap-3 px-3 py-2.5 rounded-xl hover:bg-accent/50 transition-[background-color] duration-150" data-testid="dashboard-item-row">
      <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", stateDot(item.state))} />
      <div className="min-w-0 flex-1">
        <div className="text-sm font-semibold truncate">{item.title}</div>
        <div className="text-xs text-muted-foreground flex gap-3 flex-wrap mt-0.5">
          {item.assignee_name && <span>For {item.assignee_name}</span>}
          {item.due_at && <span className="font-mono">{fmtWhen(item.due_at)}</span>}
        </div>
      </div>
      <StatusPill state={item.state} />
    </li>
  );
}

export default function DashboardPage() {
  const api = useApi();
  const [data, setData] = useState(null);

  useEffect(() => { api.get("/dashboard").then(setData).catch((e) => toast.error(e.message)); }, [api]);

  if (!data) return (
    <div className="p-4 lg:p-8 max-w-[1180px] mx-auto space-y-5">
      <Skeleton className="h-10 w-56" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-28 rounded-3xl" />)}</div>
      <Skeleton className="h-56 rounded-3xl" />
    </div>
  );

  const { counts, overdue, due_today, stuck, waiting, upcoming, brief } = data;
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <div className="p-4 lg:p-8 max-w-[1180px] mx-auto" data-testid="dashboard-page">
      <PageHeader eyebrow={greet} title="Today" subtitle={`${data.org?.name || "Your business"} — what needs your attention right now.`}>
        <Button asChild variant="outline" data-testid="dashboard-go-chat"><Link to="/app/chat">Ask KONNTO <ArrowRight className="h-4 w-4" /></Link></Button>
      </PageHeader>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {COUNTER_META.map((c, i) => {
          const Icon = c.icon;
          const id = c.key.replace("_", "-");
          return (
            <div key={c.key} className="relative overflow-hidden rounded-3xl surface surface-hover p-4 sm:p-5 animate-fade-up" style={{ animationDelay: `${i * 60}ms` }} data-testid={`dashboard-counter-${id}`}>
              <div className={cn("absolute -top-10 -right-10 h-28 w-28 rounded-full blur-2xl pointer-events-none", TONE_GLOW[c.tone])} aria-hidden />
              <div className="flex items-center justify-between">
                <span className="eyebrow text-muted-foreground">{c.label}</span>
                <span className={cn("h-8 w-8 rounded-xl grid place-items-center", TONE_BG[c.tone], TONE_TEXT[c.tone])}><Icon className="h-4 w-4" /></span>
              </div>
              <div className={cn("mt-4 font-mono tabular text-4xl font-semibold", (counts[c.key] || 0) > 0 ? TONE_TEXT[c.tone] : "text-foreground")} data-testid={`dashboard-counter-${id}-value`}>{counts[c.key] || 0}</div>
            </div>
          );
        })}
      </div>

      <div className="mt-5 grid lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3 space-y-4">
          {brief?.text && (
            <div className="k-shimmer k-shimmer--calm" data-testid="dashboard-brief-card">
              <div className="relative rounded-[inherit] bg-card/95 p-5 overflow-hidden">
                <div className="absolute -top-20 -left-16 h-48 w-48 rounded-full bg-primary/15 blur-3xl pointer-events-none" aria-hidden />
                <div className="relative flex items-center gap-3">
                  <KonntoOrb size={40} state="idle" />
                  <div>
                    <div className="eyebrow text-primary">KONNTO brief</div>
                    <div className="font-display font-bold text-lg leading-tight">This morning</div>
                  </div>
                </div>
                <div className="relative mt-4 text-[15px] whitespace-pre-wrap leading-7">{brief.text}</div>
              </div>
            </div>
          )}
          <SectionCard title="Overdue" icon={AlertTriangle} testid="dashboard-overdue-section" action={<Link to="/app/work?state=overdue" className="text-sm font-semibold text-primary hover:underline" data-testid="dashboard-overdue-link">See all</Link>}>
            {overdue.length ? <ul className="-mx-2">{overdue.map((i) => <ItemRow key={i.item_id} item={i} />)}</ul>
              : <EmptyState icon={CheckCircle2} title="Nothing overdue" body="Your day is clear so far." testid="dashboard-overdue-empty" />}
          </SectionCard>
          <SectionCard title="Due today" icon={Clock} testid="dashboard-due-today-section" action={<Link to="/app/work?state=due" className="text-sm font-semibold text-primary hover:underline">See all</Link>}>
            {due_today.length ? <ul className="-mx-2">{due_today.map((i) => <ItemRow key={i.item_id} item={i} />)}</ul>
              : <div className="text-sm text-muted-foreground px-1 py-2">Nothing due today.</div>}
          </SectionCard>
          {stuck.length > 0 && (
            <SectionCard title="Stuck" icon={PauseCircle} testid="dashboard-stuck-section">
              <ul className="-mx-2">{stuck.map((i) => <ItemRow key={i.item_id} item={i} />)}</ul>
            </SectionCard>
          )}
        </div>
        <div className="lg:col-span-2 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Link to="/app/approvals" className="relative overflow-hidden rounded-3xl surface surface-hover p-4" data-testid="dashboard-approvals-card">
              <div className="absolute -bottom-10 -right-8 h-24 w-24 rounded-full bg-brand-red/15 blur-2xl pointer-events-none" aria-hidden />
              <span className="h-9 w-9 rounded-xl bg-accent text-primary grid place-items-center"><ShieldCheck className="h-4 w-4" /></span>
              <div className="mt-3 font-mono tabular text-3xl font-semibold" data-testid="dashboard-approvals-link">{counts.approvals || 0}</div>
              <div className="eyebrow text-muted-foreground mt-1">Approvals waiting</div>
            </Link>
            <Link to="/app/team" className="relative overflow-hidden rounded-3xl surface surface-hover p-4" data-testid="dashboard-team-card">
              <div className="absolute -bottom-10 -right-8 h-24 w-24 rounded-full bg-brand-cyan/15 blur-2xl pointer-events-none" aria-hidden />
              <span className="h-9 w-9 rounded-xl bg-accent text-primary grid place-items-center"><Users className="h-4 w-4" /></span>
              <div className="mt-3 font-mono tabular text-3xl font-semibold">{counts.team}</div>
              <div className="eyebrow text-muted-foreground mt-1">People</div>
            </Link>
          </div>
          <SectionCard title="Who's waiting on whom" icon={GitBranch} testid="dashboard-waiting-section">
            {waiting.length ? (
              <ul className="space-y-2">
                {waiting.slice(0, 6).map((w, i) => (
                  <li key={i} className="flex items-center gap-3 rounded-2xl border border-border bg-[hsl(var(--surface-2))] px-3 py-2.5">
                    <PersonAvatar name={w.waiting || "You"} size={32} />
                    <div className="text-sm flex-1 min-w-0">
                      <div className="truncate"><span className="font-semibold">{w.waiting || "You"}</span> <span className="text-muted-foreground">waiting on</span> <span className="font-semibold">{w.on || "—"}</span></div>
                      <div className="text-xs text-muted-foreground truncate">{w.title}{w.blocked_by ? ` — blocked by “${w.blocked_by}”` : ""}</div>
                    </div>
                    <StatusPill state={w.state} />
                  </li>
                ))}
              </ul>
            ) : <div className="text-sm text-muted-foreground px-1">No one is waiting on anyone.</div>}
          </SectionCard>
          <SectionCard title="Upcoming" icon={CalendarClock} testid="dashboard-upcoming-section">
            {upcoming.length ? <ul className="-mx-2">{upcoming.slice(0, 6).map((i) => <ItemRow key={i.item_id} item={i} />)}</ul>
              : <div className="text-sm text-muted-foreground px-1">Nothing scheduled.</div>}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
