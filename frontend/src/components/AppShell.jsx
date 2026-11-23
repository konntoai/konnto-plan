import { useMemo } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Home, MessageSquareText, CheckSquare, Users, ShieldCheck, ClipboardList, Menu, LogOut, Settings, BookOpen, FileText, LifeBuoy, Lock, LayoutDashboard, Sparkles } from "lucide-react";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Logo, PersonAvatar, FullPageLoader, KonntoOrb } from "@/components/common";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useSession } from "@/components/auth/session";
import { useMe } from "@/context/MeContext";
import { BrainChatProvider } from "@/context/BrainChatContext";
import { KBrainPanel } from "@/components/brain/KBrainPanel";
import { cn } from "@/lib/utils";

const PRIMARY = [
  { to: "/app/chat", label: "Chat", icon: MessageSquareText, testid: "nav-chat" },
  { to: "/app/dashboard", label: "Today", icon: Home, testid: "nav-dashboard" },
  { to: "/app/work", label: "Work", icon: CheckSquare, testid: "nav-work" },
  { to: "/app/team", label: "Team", icon: Users, testid: "nav-team" },
  { to: "/app/approvals", label: "Approvals", icon: ShieldCheck, testid: "nav-approvals" },
];

const SECONDARY = [
  { to: "/app/pcm", label: "PCM", icon: ClipboardList, testid: "nav-pcm" },
  { to: "/app/documents", label: "Documents", icon: FileText, testid: "nav-documents" },
  { to: "/app/knowledge", label: "Business brain", icon: BookOpen, testid: "nav-knowledge" },
  { to: "/app/settings", label: "Settings", icon: Settings, testid: "nav-settings" },
  { to: "/app/privacy", label: "Privacy", icon: Lock, testid: "nav-privacy" },
  { to: "/app/help", label: "Help", icon: LifeBuoy, testid: "nav-help" },
];

const TITLES = {
  "/app/chat": "Chat with K-BRAIN",
  "/app/dashboard": "Today",
  "/app/work": "Work",
  "/app/pcm": "KONNTO PCM",
  "/app/team": "Team",
  "/app/approvals": "Approvals",
  "/app/documents": "Documents",
  "/app/knowledge": "Business brain",
  "/app/settings": "Settings",
  "/app/privacy": "Privacy",
  "/app/help": "Help",
};

const Badge = ({ n, className = "" }) => (n ? (
  <span className={cn("min-w-[20px] h-5 px-1.5 rounded-full bg-brand-red text-white text-[11px] grid place-items-center font-bold shadow-[0_0_12px_hsl(var(--glow-red))]", className)}>{n}</span>
) : null);

const RailLink = ({ item, badge, onNavigate }) => (
  <NavLink
    to={item.to}
    data-testid={item.testid}
    onClick={onNavigate}
    end={item.to === "/app/chat"}
    className={({ isActive }) => cn(
      "group relative flex items-center gap-3 rounded-xl px-3 h-11 text-sm font-semibold transition-[background-color,color] duration-200",
      isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
    )}
  >
    {({ isActive }) => (
      <>
        {isActive && <span className="nav-active-bar" />}
        <item.icon className={cn("h-[18px] w-[18px] transition-colors", isActive ? "text-primary" : "group-hover:text-primary")} />
        <span className="flex-1 truncate">{item.label}</span>
        <Badge n={badge} />
      </>
    )}
  </NavLink>
);

const TabLink = ({ item, badge }) => (
  <NavLink
    to={item.to}
    data-testid={`tab-${item.label.toLowerCase()}`}
    end={item.to === "/app/chat"}
    className={({ isActive }) => cn("relative flex-1 flex flex-col items-center justify-center gap-1 text-[11px] font-semibold h-full", isActive ? "text-primary" : "text-muted-foreground")}
  >
    {({ isActive }) => (
      <>
        <span className={cn("relative h-8 w-12 grid place-items-center rounded-full transition-[background-color,box-shadow] duration-200", isActive && "bg-accent shadow-[0_6px_18px_-6px_hsl(var(--glow-blue))]")}>
          <item.icon className="h-5 w-5" />
          {badge ? <Badge n={badge} className="absolute -top-1 -right-0.5 min-w-[16px] h-4 text-[10px] px-1" /> : null}
        </span>
        <span>{item.label}</span>
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
  const title = TITLES[location.pathname] || (location.pathname.startsWith("/app/team/thread") ? "Team chat" : "KONNTO");

  const Rail = ({ onNavigate }) => (
    <div className="h-full w-full flex flex-col gap-1 p-4">
      <div className="px-1 pt-1 pb-4"><Logo tile size="md" /></div>

      <button
        onClick={() => { navigate("/app/chat"); onNavigate?.(); }}
        data-testid="rail-ask-konnto"
        className="k-trail group relative mb-4 flex items-center gap-3 rounded-2xl border border-primary/20 bg-[linear-gradient(135deg,hsl(var(--primary)/0.14),hsl(var(--brand-cyan)/0.06))] p-3 text-left transition-[border-color,box-shadow] duration-200 hover:border-primary/40 hover:shadow-[0_12px_30px_-14px_hsl(var(--glow-blue))]"
      >
        <KonntoOrb size={38} state="idle" />
        <div className="min-w-0">
          <div className="text-sm font-bold font-display">Ask K-BRAIN</div>
          <div className="text-xs text-muted-foreground truncate">Type, talk or drop a file</div>
        </div>
        <Sparkles className="h-4 w-4 text-primary ml-auto opacity-70 group-hover:opacity-100" />
      </button>

      <div className="eyebrow text-muted-foreground/80 px-3 mb-1">Your day</div>
      {PRIMARY.map((n) => <RailLink key={n.to} item={n} badge={badges[n.to]} onNavigate={onNavigate} />)}
      <div className="eyebrow text-muted-foreground/80 px-3 mt-5 mb-1">More</div>
      {SECONDARY.map((n) => <RailLink key={n.to} item={n} onNavigate={onNavigate} />)}
      {isAdmin && (
        <>
          <div className="eyebrow text-muted-foreground/80 px-3 mt-5 mb-1">KONNTO admin</div>
          <RailLink item={{ to: "/admin", label: "Admin console", icon: LayoutDashboard, testid: "nav-admin" }} onNavigate={onNavigate} />
        </>
      )}
      <div className="mt-auto pt-4" />
      <div className="rounded-2xl border border-border bg-[hsl(var(--surface-2))] p-3 text-xs leading-5" data-testid="app-rail-status">
        <div className="font-bold font-display text-sm text-foreground truncate">{org?.name || "Your business"}</div>
        <div className="mt-1 flex items-center gap-2 text-muted-foreground">
          <span className={cn("h-2 w-2 rounded-full", me?.whatsapp_connected ? "bg-status-done shadow-[0_0_8px_hsl(var(--status-done))]" : "bg-status-due shadow-[0_0_8px_hsl(var(--status-due))]")} />
          {me?.whatsapp_connected ? "WhatsApp is live" : "WhatsApp is not connected yet"}
        </div>
      </div>
    </div>
  );

  const onChat = location.pathname === "/app/chat";

  return (
    <BrainChatProvider>
    <div className="min-h-screen bg-background flex app-ambient">
      <aside className="hidden lg:flex w-[272px] shrink-0 sticky top-0 h-screen overflow-y-auto scrollbar-thin glass border-y-0 border-l-0">
        <Rail />
      </aside>
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="sticky top-0 z-40 h-14 lg:h-16 glass border-x-0 border-t-0" data-testid="app-topbar">
          <div className="h-full px-3 lg:px-6 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 lg:gap-3 min-w-0">
              <Sheet>
                <SheetTrigger asChild>
                  <button className="lg:hidden h-10 w-10 grid place-items-center rounded-xl hover:bg-accent" aria-label="Open menu" data-testid="app-menu-button">
                    <Menu className="h-5 w-5" />
                  </button>
                </SheetTrigger>
                <SheetContent side="left" className="w-[300px] p-0 overflow-y-auto">
                  <SheetTitle className="sr-only">Menu</SheetTitle>
                  <Rail />
                </SheetContent>
              </Sheet>
              <div className="lg:hidden"><Logo tile compact size="sm" /></div>
              <div className="min-w-0">
                <div className="eyebrow text-primary hidden sm:block">{org?.name || "Your business"}</div>
                <div className="font-display font-bold text-[15px] lg:text-lg truncate" data-testid="app-topbar-title">{title}</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle testid="app-theme-toggle" />
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex items-center gap-2 rounded-full glass pl-1 pr-1 sm:pr-3 py-1 hover:border-primary/40 transition-[border-color] duration-200" data-testid="profile-menu-button">
                    <PersonAvatar name={user.name || "You"} size={32} tone={member?.member_type === "owner" ? "owner" : "default"} />
                    <span className="hidden sm:block text-sm font-semibold max-w-[160px] truncate">{user.name || user.email || "Me"}</span>
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-64" data-testid="profile-menu">
                  <DropdownMenuLabel className="font-normal">
                    <div className="font-semibold truncate">{user.name}</div>
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
          </div>
        </header>
        <main className={cn("flex-1 min-w-0", !onChat && "pb-24 lg:pb-28")}>
          <Outlet />
        </main>
        <nav className="lg:hidden sticky bottom-0 z-[45] h-[68px] glass border-x-0 border-b-0 safe-bottom box-content" data-testid="app-bottom-tabs">
          <div className="h-[68px] flex px-1">
            {PRIMARY.map((n) => <TabLink key={n.to} item={n} badge={badges[n.to]} />)}
          </div>
        </nav>
      </div>
      <KBrainPanel />
    </div>
    </BrainChatProvider>
  );
}
