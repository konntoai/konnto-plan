import { toast } from "sonner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useApi } from "@/lib/api";
import { useMe } from "@/context/MeContext";
import { cn } from "@/lib/utils";

const HINT = {
  chief_of_staff: "Warm, direct, gives a recommendation",
  assistant: "Organised, polite, offers to handle it",
  advisor: "CEO-level, explains the trade-offs",
  operator: "Short, punchy, numbers first",
};

const FALLBACK = [
  { id: "chief_of_staff", label: "Chief of Staff" },
  { id: "assistant", label: "Executive Assistant" },
  { id: "advisor", label: "Senior Advisor" },
  { id: "operator", label: "Sharp Operator" },
];

/** Lets each person choose how K-BRAIN talks to them. */
export function PersonaSelect({ testid = "kbrain-persona-select", className = "" }) {
  const api = useApi();
  const { me, setMe } = useMe();
  const options = me?.brain_personas?.length ? me.brain_personas : FALLBACK;
  const value = me?.brain_persona || "chief_of_staff";

  const change = async (v) => {
    const prev = me?.brain_persona;
    setMe((m) => ({ ...m, brain_persona: v }));
    try {
      const r = await api.put("/me/brain-persona", { persona: v });
      toast.success(`K-BRAIN will talk like your ${r.label}`);
    } catch (e) {
      setMe((m) => ({ ...m, brain_persona: prev }));
      toast.error(e.message);
    }
  };

  return (
    <Select value={value} onValueChange={change}>
      <SelectTrigger className={cn("h-8 w-auto gap-2 rounded-full px-3 text-xs font-semibold", className)} data-testid={testid} aria-label="How K-BRAIN talks to you">
        <SelectValue>{options.find((o) => o.id === value)?.label || "Chief of Staff"}</SelectValue>
      </SelectTrigger>
      <SelectContent align="end">
        {options.map((o) => (
          <SelectItem key={o.id} value={o.id} data-testid={`${testid}-${o.id}`}>
            <span className="font-semibold">{o.label}</span>
            <span className="block text-[11px] text-muted-foreground">{HINT[o.id]}</span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
