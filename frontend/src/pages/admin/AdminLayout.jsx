import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { Brain, Globe, Package, Users, MessageCircle, Settings, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo, FullPageLoader } from "@/components/common";
import { ThemeToggle } from "@/components/ThemeToggle";
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
    <div className="min-h-screen bg-background flex app-ambient" data-testid="admin-page">
      <aside className="hidden lg:flex w-[260px] shrink-0 sticky top-0 h-screen overflow-y-auto scrollbar-thin glass border-y-0 border-l-0">
        <div className="w-full p-4 flex flex-col gap-1">
          <div className="px-1 pt-1 pb-4"><Logo tile /></div>
          <div className="eyebrow text-brand-red px-3 mb-1">Admin console</div>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} data-testid={n.testid}
              className={({ isActive }) => cn("relative flex items-center gap-3 rounded-xl px-3 h-11 text-sm font-semibold transition-[background-color,color] duration-200", isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent/50 hover:text-foreground")}>
              {({ isActive }) => (<>{isActive && <span className="nav-active-bar" />}<n.icon className={cn("h-4 w-4", isActive && "text-primary")} /> {n.label}</>)}
            </NavLink>
          ))}
          <div className="mt-auto" />
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="flex-1" onClick={() => navigate("/app/chat")} data-testid="admin-back-to-app"><ArrowLeft className="h-4 w-4" /> Back to app</Button>
            <ThemeToggle testid="admin-theme-toggle" />
          </div>
        </div>
      </aside>
      <div className="flex-1 min-w-0">
        <header className="lg:hidden sticky top-0 z-40 h-14 glass border-x-0 border-t-0 flex items-center px-3 gap-2">
          <Logo tile compact size="sm" />
          <div className="flex-1 min-w-0 flex gap-1 overflow-x-auto no-scrollbar">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end} data-testid={`${n.testid}-mobile`}
                className={({ isActive }) => cn("px-3 h-9 rounded-full text-xs font-semibold whitespace-nowrap grid place-items-center", isActive ? "bg-brand-gradient text-white" : "text-muted-foreground")}>
                {n.label}
              </NavLink>
            ))}
          </div>
          <ThemeToggle testid="admin-theme-toggle-mobile" className="h-9 w-9" />
        </header>
        <Outlet />
      </div>
    </div>
  );
}
