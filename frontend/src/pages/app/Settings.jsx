import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Save, Phone, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageHeader, SectionCard } from "@/components/common";
import { useApi } from "@/lib/api";
import { useMe } from "@/context/MeContext";

const HOURS = Array.from({ length: 24 }, (_, i) => i);

export default function SettingsPage() {
  const api = useApi();
  const { me, refresh } = useMe();
  const [profile, setProfile] = useState(null);
  const [org, setOrg] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!me) return;
    setProfile({ name: me.user?.name || "", email: me.user?.email || "", phone: me.member?.phone || "", wa_opt_in: !!me.member?.wa_opt_in });
    setOrg({
      name: me.org?.name || "",
      industry: me.org?.industry || "",
      description: me.org?.description || "",
      country: me.org?.country || "",
      currency: me.org?.currency || "",
      timezone: me.org?.timezone || "",
      briefs_enabled: me.org?.briefs?.enabled ?? true,
      morning_hour: me.org?.briefs?.morning_hour ?? 8,
      evening_hour: me.org?.briefs?.evening_hour ?? 19,
    });
  }, [me]);

  const saveProfile = async () => {
    setBusy(true);
    try { await api.put("/me/profile", profile); await refresh(); toast.success("Profile saved"); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };
  const saveOrg = async () => {
    setBusy(true);
    try { await api.put("/org", org); await refresh(); toast.success("Business saved"); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  if (!profile || !org) return <div className="p-6"><Loader2 className="h-5 w-5 animate-spin" /></div>;

  const isOwner = me?.member?.member_type === "owner";

  return (
    <div className="p-4 lg:p-8 max-w-[900px] mx-auto space-y-5" data-testid="settings-page">
      <PageHeader title="Settings" subtitle="Your profile and business settings." />

      <SectionCard title="You" testid="settings-profile">
        <div className="space-y-3">
          <label className="text-sm block">Name<Input className="mt-1" value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} data-testid="settings-name" /></label>
          <label className="text-sm block">WhatsApp number<Input className="mt-1" placeholder="+91 98765 43210" value={profile.phone} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} data-testid="settings-phone" /></label>
          <label className="text-sm block">Email<Input className="mt-1" value={profile.email || ""} onChange={(e) => setProfile({ ...profile, email: e.target.value })} data-testid="settings-email" /></label>
          <label className="flex items-start gap-2 text-sm"><Checkbox checked={profile.wa_opt_in} onCheckedChange={(v) => setProfile({ ...profile, wa_opt_in: Boolean(v) })} data-testid="settings-wa-opt-in" /> KONNTO can message me on WhatsApp.</label>
          <Button onClick={saveProfile} disabled={busy} data-testid="settings-save-profile" className="btn-lift">{busy ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Save className="h-4 w-4 mr-1" />} Save</Button>
        </div>
      </SectionCard>

      {isOwner && (
        <SectionCard title="Business" testid="settings-business">
          <div className="space-y-3">
            <label className="text-sm block">Business name<Input className="mt-1" value={org.name} onChange={(e) => setOrg({ ...org, name: e.target.value })} data-testid="settings-biz-name" /></label>
            <div className="grid grid-cols-2 gap-3">
              <label className="text-sm">Industry<Input className="mt-1" value={org.industry || ""} onChange={(e) => setOrg({ ...org, industry: e.target.value })} data-testid="settings-biz-industry" /></label>
              <label className="text-sm">Currency<Input className="mt-1" value={org.currency || ""} onChange={(e) => setOrg({ ...org, currency: e.target.value })} data-testid="settings-biz-currency" /></label>
            </div>
            <label className="text-sm block">Description<Textarea className="mt-1" rows={3} value={org.description || ""} onChange={(e) => setOrg({ ...org, description: e.target.value })} data-testid="settings-biz-description" /></label>
            <div className="pt-3 border-t border-border">
              <label className="flex items-start gap-2 text-sm mb-3"><Checkbox checked={org.briefs_enabled} onCheckedChange={(v) => setOrg({ ...org, briefs_enabled: Boolean(v) })} data-testid="settings-briefs-enabled" /> Send morning + evening briefs</label>
              <div className="grid grid-cols-2 gap-3">
                <label className="text-sm">Morning time
                  <Select value={String(org.morning_hour)} onValueChange={(v) => setOrg({ ...org, morning_hour: Number(v) })}>
                    <SelectTrigger className="mt-1" data-testid="settings-morning-hour"><SelectValue /></SelectTrigger>
                    <SelectContent>{HOURS.map((h) => <SelectItem key={h} value={String(h)}>{String(h).padStart(2, "0")}:00</SelectItem>)}</SelectContent>
                  </Select>
                </label>
                <label className="text-sm">Evening time
                  <Select value={String(org.evening_hour)} onValueChange={(v) => setOrg({ ...org, evening_hour: Number(v) })}>
                    <SelectTrigger className="mt-1" data-testid="settings-evening-hour"><SelectValue /></SelectTrigger>
                    <SelectContent>{HOURS.map((h) => <SelectItem key={h} value={String(h)}>{String(h).padStart(2, "0")}:00</SelectItem>)}</SelectContent>
                  </Select>
                </label>
              </div>
            </div>
            <Button onClick={saveOrg} disabled={busy} data-testid="settings-save-business" className="btn-lift">{busy ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Save className="h-4 w-4 mr-1" />} Save business</Button>
          </div>
        </SectionCard>
      )}

      <SectionCard title="Channels" testid="settings-channels">
        <div className="text-sm space-y-2">
          <div className="flex items-center gap-2"><Mail className="h-4 w-4 text-primary" /> Email is on by default for important updates.</div>
          <div className="flex items-center gap-2"><Phone className="h-4 w-4 text-primary" /> WhatsApp is {me?.whatsapp_connected ? <span className="font-medium ml-1">connected</span> : <span className="font-medium ml-1">not connected yet</span>}.</div>
          {!me?.whatsapp_connected && <p className="text-muted-foreground text-xs">When WhatsApp is live for your business, briefs, reminders and approvals will send there automatically.</p>}
        </div>
      </SectionCard>
    </div>
  );
}
