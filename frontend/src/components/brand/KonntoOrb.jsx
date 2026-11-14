import { KonntoMarkSvg } from "@/components/brand/Logo";
import { cn } from "@/lib/utils";

/**
 * KONNTO Orb — the AI presence.
 * state: "idle" | "thinking" | "streaming" | "static"
 * ripple: adds expanding rings (bold moments — hero / empty states)
 */
export const KonntoOrb = ({ size = 40, state = "idle", ripple = false, mark = true, className = "", testid }) => (
  <div
    data-testid={testid}
    aria-hidden
    style={{ "--orb-size": `${size}px` }}
    className={cn("k-orb", `k-orb--${state}`, className)}
  >
    {ripple && (
      <>
        <span className="k-orb__ripple" />
        <span className="k-orb__ripple" />
      </>
    )}
    <span className="k-orb__halo" />
    <span className="k-orb__ring" />
    <span className="k-orb__core"><span className="k-orb__swirl" /></span>
    {mark && <KonntoMarkSvg bar="#ffffff" className="k-orb__mark" />}
  </div>
);

export default KonntoOrb;
