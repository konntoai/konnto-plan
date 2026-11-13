import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Clock, PauseCircle, CheckCircle2, Users, ShieldCheck, Sunrise, UserCheck, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, StatusPill, PersonAvatar, SectionCard, EmptyState } from "@/components/common";
import { useApi } from "@/lib/api";
import { fmtWhen } from "@/lib/format";
import { toast } from "sonner";

const COUNTER_META = [
  { key: "overdue", label: "Overdue", icon: AlertTriangle, tone: "text-red-700 bg-red-50 border-red-200" },
  { key: "due_today", label: "Due today", icon: Clock, tone: "text-amber-800 bg-amber-50 border-amber-200" },
  { key: "stuck", label: "Stuck", icon: PauseCircle, tone: "text-slate-700 bg-slate-100 border-slate-200" },
  { key: "done_week", label: "Done this week", icon: CheckCircle2, tone: "text-emerald-700 bg-emerald-50 border-emerald-200" },
];

function ItemRow({ item }) {
  return (
    <li className="flex items-start gap-3 px-3 py-2 rounded-xl hover:bg-accent/40" data-testid="dashboard-item-row">
      <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary/60" />
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium truncate">{item.title}</div>
        <div className="text-xs text-muted-foreground flex gap-2 flex-wrap mt-0.5">
          {item.assignee_name && <span>For {item.assignee_name}</span>}
          {item.due_at && <span>{fmtWhen(item.due_at)}</span>}
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
    <div className="p-4 lg:p-6 max-w-[1120px] mx-auto space-y-5">
      <Skeleton className="h-8 w-56" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">{[0,1,2,3].map((i) => <Skeleton key={i} className="h-24 rounded-2xl" />)}</div>
      <Skeleton className="h-56 rounded-2xl" />
    </div>
  );

  const { counts, overdue, due_today, due_soon, stuck, waiting, upcoming, brief } = data;

  return (
    <div className="p-4 lg:p-6 max-w-[1120px] mx-auto" data-testid="dashboard-page">
      <PageHeader title="Today" subtitle={`${data.org?.name || "Your business"} — what needs your attention right now.`}>
        <Button asChild variant="outline" data-testid="dashboard-go-chat"><Link to="/app/chat">Open chat <ArrowRight className="h-4 w-4 ml-1" /></Link></Button>
      </PageHeader>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {COUNTER_META.map((c) => {
          const Icon = c.icon;
          return (
            <div key={c.key} className="rounded-2xl border border-border bg-card p-4" data-testid={`dashboard-counter-${c.key.replace("_", "-")}`}>
              <div className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] ${c.tone}`}><Icon className="h-3.5 w-3.5" /> {c.label}</div>
              <div className="mt-3 text-2xl font-semibold font-display" data-testid={`dashboard-counter-${c.key.replace("_", "-")}-value`}>{counts[c.key] || 0}</div>
            </div>
          );
        })}
      </div>

      <div className="mt-5 grid lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3 space-y-4">
          {brief?.text && (
            <SectionCard title="This morning" testid="dashboard-brief-card" className="relative overflow-hidden">
              <div className="absolute left-0 top-4 bottom-4 w-1 bg-primary/30 rounded-r-full" />
              <div className="pl-3 text-sm whitespace-pre-wrap leading-6">{brief.text}</div>
            </SectionCard>
          )}
          <SectionCard title="Overdue" testid="dashboard-overdue-section" action={<Link to="/app/work?state=overdue" className="text-sm text-primary hover:underline" data-testid="dashboard-overdue-link">See all</Link>}>
            {overdue.length ? <ul className="-mx-1">{overdue.map((i) => <ItemRow key={i.item_id} item={i} />)}</ul>
              : <EmptyState icon={CheckCircle2} title="Nothing overdue" body="Your day is clear so far." testid="dashboard-overdue-empty" />}
          </SectionCard>
          <SectionCard title="Due today" testid="dashboard-due-today-section" action={<Link to="/app/work?state=due" className="text-sm text-primary hover:underline">See all</Link>}>
            {due_today.length ? <ul className="-mx-1">{due_today.map((i) => <ItemRow key={i.item_id} item={i} />)}</ul>
              : <div className="text-sm text-muted-foreground px-2 py-3">Nothing due today.</div>}
          </SectionCard>
          {stuck.length > 0 && (
            <SectionCard title="Stuck" testid="dashboard-stuck-section">
              <ul className="-mx-1">{stuck.map((i) => <ItemRow key={i.item_id} item={i} />)}</ul>
            </SectionCard>
          )}
        </div>
        <div className="lg:col-span-2 space-y-4">
          <SectionCard title="Approvals waiting" testid="dashboard-approvals-card" action={<Link to="/app/approvals" className="text-sm text-primary hover:underline" data-testid="dashboard-approvals-link">Open</Link>}>
            <div className="flex items-center gap-3">
              <div className="h-11 w-11 rounded-xl bg-accent text-accent-foreground grid place-items-center"><ShieldCheck className="h-5 w-5" /></div>
              <div className="flex-1"><div className="text-2xl font-semibold font-display">{counts.approvals || 0}</div><div className="text-xs text-muted-foreground">pending</div></div>
            </div>
          </SectionCard>
          <SectionCard title="Who's waiting on whom" testid="dashboard-waiting-section">
            {waiting.length ? (
              <ul className="space-y-2">
                {waiting.slice(0, 6).map((w, i) => (
                  <li key={i} className="flex items-center gap-3 rounded-xl border border-border bg-background px-3 py-2">
                    <PersonAvatar name={w.waiting || "You"} size={30} />
                    <div className="text-sm flex-1 min-w-0">
                      <div className="truncate"><span className="font-medium">{w.waiting || "You"}</span> waiting on <span className="font-medium">{w.on || "—"}</span></div>
                      <div className="text-xs text-muted-foreground truncate">{w.title}{w.blocked_by ? ` — blocked by “${w.blocked_by}”` : ""}</div>
                    </div>
                    <StatusPill state={w.state} />
                  </li>
                ))}
              </ul>
            ) : <div className="text-sm text-muted-foreground px-1">No one is waiting on anyone.</div>}
          </SectionCard>
          <SectionCard title="Upcoming" testid="dashboard-upcoming-section">
            {upcoming.length ? <ul className="-mx-1">{upcoming.slice(0, 6).map((i) => <ItemRow key={i.item_id} item={i} />)}</ul>
              : <div className="text-sm text-muted-foreground px-1">Nothing scheduled.</div>}
          </SectionCard>
          <SectionCard title="Team" testid="dashboard-team-card" action={<Link to="/app/team" className="text-sm text-primary hover:underline">Open</Link>}>
            <div className="flex items-center gap-3">
              <div className="h-11 w-11 rounded-xl bg-accent text-accent-foreground grid place-items-center"><Users className="h-5 w-5" /></div>
              <div className="flex-1"><div className="text-2xl font-semibold font-display">{counts.team}</div><div className="text-xs text-muted-foreground">people</div></div>
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
