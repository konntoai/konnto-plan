import { useMemo } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Home, MessageSquareText, CheckSquare, Users, ShieldCheck, Menu, LogOut, Settings, BookOpen, FileText, LifeBuoy, Lock, LayoutDashboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Logo, PersonAvatar, FullPageLoader } from "@/components/common";
import { useSession } from "@/components/auth/session";
import { useMe } from "@/context/MeContext";
import { cn } from "@/lib/utils";

const PRIMARY = [
  { to: "/app/chat", label: "Chat", icon: MessageSquareText, testid: "nav-chat" },
  { to: "/app/dashboard", label: "Today", icon: Home, testid: "nav-dashboard" },
  { to: "/app/work", label: "Work", icon: CheckSquare, testid: "nav-work" },
  { to: "/app/team", label: "Team", icon: Users, testid: "nav-team" },
  { to: "/app/approvals", label: "Approvals", icon: ShieldCheck, testid: "nav-approvals" },
];

const SECONDARY = [
  { to: "/app/documents", label: "Documents", icon: FileText, testid: "nav-documents" },
  { to: "/app/knowledge", label: "Business brain", icon: BookOpen, testid: "nav-knowledge" },
  { to: "/app/settings", label: "Settings", icon: Settings, testid: "nav-settings" },
  { to: "/app/privacy", label: "Privacy", icon: Lock, testid: "nav-privacy" },
  { to: "/app/help", label: "Help", icon: LifeBuoy, testid: "nav-help" },
];

const LINK_BASE = "flex items-center gap-3 rounded-xl px-3 h-11 text-sm font-medium text-muted-foreground hover:bg-accent/60 hover:text-foreground transition-colors";
const LINK_ACTIVE = "bg-accent text-accent-foreground";

const RailLink = ({ item, badge, onNavigate }) => (
  <NavLink to={item.to} data-testid={item.testid} onClick={onNavigate} className={({ isActive }) => cn(LINK_BASE, isActive && LINK_ACTIVE)} end={item.to === "/app/chat"}>
    <item.icon className="h-4 w-4" />
    <span className="flex-1 truncate">{item.label}</span>
    {badge ? <span className="min-w-[20px] h-5 px-1.5 rounded-full bg-primary text-primary-foreground text-[11px] grid place-items-center font-semibold">{badge}</span> : null}
  </NavLink>
);

const TabLink = ({ item, badge }) => (
  <NavLink to={item.to} data-testid={`tab-${item.label.toLowerCase()}`} end={item.to === "/app/chat"} className={({ isActive }) => cn(
    "relative flex-1 flex flex-col items-center justify-center gap-0.5 text-[11px] font-medium text-muted-foreground h-full",
    isActive && "text-primary"
  )}>
    {({ isActive }) => (
      <>
        <item.icon className={cn("h-5 w-5", isActive && "text-primary")} />
        <span>{item.label}</span>
        {badge ? <span className="absolute top-1 right-1/4 min-w-[16px] h-4 px-1 rounded-full bg-primary text-primary-foreground text-[10px] grid place-items-center font-semibold">{badge}</span> : null}
      </>
    )}
  </NavLink>
);

export default function AppShell() {
  const { me, loading } = useMe();
  const { signOut } = useSession();
  const navigate = useNavigate();
  const location = useLocation();

  const badges = useMemo(() => ({ "/app/approvals": me?.pending_approvals || 0 }), [me]);

  if (loading) return <FullPageLoader label="Opening KONNTO…" />;
  if (me && me.needs_onboarding && location.pathname !== "/onboarding") {
    navigate("/onboarding", { replace: true });
    return null;
  }

  const user = me?.user || {};
  const org = me?.org;
  const member = me?.member;
  const isAdmin = me?.is_admin;

  const Rail = ({ onNavigate }) => (
    <div className="h-full flex flex-col gap-1 p-3 bg-card">
      <div className="px-1 py-3"><Logo /></div>
      <div className="mt-2 mb-1 text-[11px] uppercase tracking-wide text-muted-foreground px-3">Your day</div>
      {PRIMARY.map((n) => <RailLink key={n.to} item={n} badge={badges[n.to]} onNavigate={onNavigate} />)}
      <div className="mt-4 mb-1 text-[11px] uppercase tracking-wide text-muted-foreground px-3">More</div>
      {SECONDARY.map((n) => <RailLink key={n.to} item={n} onNavigate={onNavigate} />)}
      {isAdmin && (
        <>
          <div className="mt-4 mb-1 text-[11px] uppercase tracking-wide text-muted-foreground px-3">KONNTO admin</div>
          <RailLink item={{ to: "/admin", label: "Admin console", icon: LayoutDashboard, testid: "nav-admin" }} onNavigate={onNavigate} />
        </>
      )}
      <div className="mt-auto" />
      <div className="rounded-xl border border-border bg-background/60 p-3 text-xs text-muted-foreground leading-5" data-testid="app-rail-status">
        <div className="font-medium text-foreground truncate">{org?.name || "Your business"}</div>
        <div className="mt-0.5">{me?.whatsapp_connected ? "WhatsApp is live" : "WhatsApp is not connected yet"}</div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background flex">
      <aside className="hidden lg:flex w-[280px] border-r border-border shrink-0 sticky top-0 h-screen overflow-y-auto scrollbar-thin">
        <Rail />
      </aside>
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="sticky top-0 z-30 h-14 lg:h-16 border-b border-border bg-background/95 backdrop-blur" data-testid="app-topbar">
          <div className="h-full px-3 lg:px-6 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 lg:gap-3 min-w-0">
              <Sheet>
                <SheetTrigger asChild>
                  <button className="lg:hidden h-10 w-10 grid place-items-center rounded-xl hover:bg-secondary" aria-label="Open menu" data-testid="app-menu-button">
                    <Menu className="h-5 w-5" />
                  </button>
                </SheetTrigger>
                <SheetContent side="left" className="w-[300px] p-0 bg-card"><Rail /></SheetContent>
              </Sheet>
              <div className="lg:hidden"><Logo compact /></div>
              <div className="hidden lg:block min-w-0">
                <div className="text-sm text-muted-foreground">Business</div>
                <div className="font-semibold truncate">{org?.name || "Your business"}</div>
              </div>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-2 rounded-full border border-border bg-card px-2.5 py-1.5 hover:bg-accent/40" data-testid="profile-menu-button">
                  <PersonAvatar name={user.name || "You"} size={28} tone={member?.member_type === "owner" ? "owner" : "default"} />
                  <span className="hidden sm:block text-sm font-medium max-w-[160px] truncate">{user.name || user.email || "Me"}</span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-60" data-testid="profile-menu">
                <DropdownMenuLabel className="font-normal">
                  <div className="font-medium truncate">{user.name}</div>
                  <div className="text-xs text-muted-foreground truncate">{user.email || user.whatsapp}</div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => navigate("/app/settings")} data-testid="profile-menu-settings"><Settings className="h-4 w-4 mr-2" /> Settings</DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate("/app/privacy")} data-testid="profile-menu-privacy"><Lock className="h-4 w-4 mr-2" /> Privacy</DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate("/app/help")} data-testid="profile-menu-help"><LifeBuoy className="h-4 w-4 mr-2" /> Help</DropdownMenuItem>
                {isAdmin && <DropdownMenuItem onClick={() => navigate("/admin")} data-testid="profile-menu-admin"><LayoutDashboard className="h-4 w-4 mr-2" /> Admin console</DropdownMenuItem>}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={signOut} data-testid="profile-menu-signout" className="text-destructive focus:text-destructive"><LogOut className="h-4 w-4 mr-2" /> Sign out</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>
        <main className="flex-1 min-w-0">
          <Outlet />
        </main>
        <nav className="lg:hidden sticky bottom-0 z-30 h-[68px] border-t border-border bg-background/95 backdrop-blur safe-bottom" data-testid="app-bottom-tabs">
          <div className="h-full flex">
            {PRIMARY.map((n) => <TabLink key={n.to} item={n} badge={badges[n.to]} />)}
          </div>
        </nav>
      </div>
    </div>
  );
}
