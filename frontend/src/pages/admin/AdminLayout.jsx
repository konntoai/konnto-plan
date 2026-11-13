import { useEffect } from "react";
import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { Brain, Globe, Package, Users, MessageCircle, Settings, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo, FullPageLoader } from "@/components/common";
import { useMe } from "@/context/MeContext";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/admin", label: "Teach KONNTO", icon: Brain, end: true, testid: "admin-nav-brain" },
  { to: "/admin/site", label: "Website", icon: Globe, testid: "admin-nav-site" },
  { to: "/admin/plans", label: "Plans", icon: Package, testid: "admin-nav-plans" },
  { to: "/admin/customers", label: "Customers", icon: Users, testid: "admin-nav-customers" },
  { to: "/admin/feedback", label: "Feedback", icon: MessageCircle, testid: "admin-nav-feedback" },
  { to: "/admin/settings", label: "Settings", icon: Settings, testid: "admin-nav-settings" },
];

export default function AdminLayout() {
  const { me, loading } = useMe();
  const navigate = useNavigate();

  if (loading) return <FullPageLoader />;
  if (!me?.is_admin) return <Navigate to="/app/chat" replace />;

  return (
    <div className="min-h-screen bg-background flex" data-testid="admin-page">
      <aside className="hidden lg:flex w-[260px] border-r border-border shrink-0 sticky top-0 h-screen overflow-y-auto scrollbar-thin bg-card">
        <div className="w-full p-3 flex flex-col gap-1">
          <div className="px-1 py-3"><Logo /></div>
          <div className="text-[11px] uppercase tracking-wide text-muted-foreground px-3 mt-2">KONNTO admin</div>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} data-testid={n.testid}
              className={({ isActive }) => cn("flex items-center gap-3 rounded-xl px-3 h-11 text-sm font-medium text-muted-foreground hover:bg-accent/60 hover:text-foreground transition-colors", isActive && "bg-accent text-accent-foreground")}>
              <n.icon className="h-4 w-4" /> {n.label}
            </NavLink>
          ))}
          <div className="mt-auto" />
          <Button variant="outline" size="sm" onClick={() => navigate("/app/chat")} data-testid="admin-back-to-app"><ArrowLeft className="h-4 w-4 mr-1" /> Back to app</Button>
        </div>
      </aside>
      <div className="flex-1 min-w-0">
        <header className="lg:hidden sticky top-0 z-30 h-14 border-b border-border bg-background/95 backdrop-blur flex items-center px-3 gap-3">
          <Logo compact />
          <div className="ml-auto flex gap-1 overflow-x-auto no-scrollbar">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end} data-testid={`${n.testid}-mobile`}
                className={({ isActive }) => cn("px-3 h-9 rounded-lg text-xs font-medium whitespace-nowrap grid place-items-center", isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground")}>
                {n.label}
              </NavLink>
            ))}
          </div>
        </header>
        <Outlet />
      </div>
    </div>
  );
}
