import { cn } from "@/lib/utils";

/**
 * KONNTO "K" mark — recreated from the brand logo:
 * a slanted bar (white on dark / navy on light) + a red chevron.
 * `bar` lets callers force the bar colour (e.g. always white on a blue tile).
 */
export const KonntoMarkSvg = ({ className = "", bar, title = "KONNTO", style }) => (
  <svg viewBox="-2 -2 61 76" className={className} style={style} role="img" aria-label={title} xmlns="http://www.w3.org/2000/svg">
    <polygon
      points="37.5,1.5 54.5,1.5 10,46 1.5,37.5"
      fill={bar || "hsl(var(--mark-bar))"}
      stroke={bar || "hsl(var(--mark-bar))"}
      strokeWidth="3"
      strokeLinejoin="round"
    />
    <polygon
      points="30,36 54.5,36 38,52.5 54.5,69 30,69 14,53 14,52"
      fill="hsl(var(--brand-red))"
      stroke="hsl(var(--brand-red))"
      strokeWidth="3"
      strokeLinejoin="round"
    />
  </svg>
);

/** Mark inside the royal-blue gradient tile, like the brand artwork. */
export const KonntoTile = ({ size = 36, className = "" }) => (
  <div
    style={{ width: size, height: size, borderRadius: Math.round(size * 0.3) }}
    className={cn("bg-brand-tile grid place-items-center shrink-0 shadow-[0_8px_24px_-8px_hsl(var(--glow-blue))] ring-1 ring-white/10", className)}
  >
    <KonntoMarkSvg bar="#ffffff" className="w-[52%] h-auto" />
  </div>
);

/** Full lockup: mark | KONNTO (+ optional AI tag). */
export const Logo = ({ className = "", compact = false, tile = false, size = "md", showAi = true }) => {
  const dims = { sm: { mark: 22, text: "text-[15px]", div: "h-5" }, md: { mark: 26, text: "text-[18px]", div: "h-6" }, lg: { mark: 40, text: "text-[28px]", div: "h-9" } }[size] || { mark: 26, text: "text-[18px]", div: "h-6" };
  return (
    <div className={cn("flex items-center gap-2.5 select-none", className)} data-testid="konnto-logo">
      {tile ? <KonntoTile size={dims.mark + 10} /> : <KonntoMarkSvg className="h-auto shrink-0" style={{ width: dims.mark }} />}
      {!compact && (
        <>
          {!tile && <span className={cn("w-px bg-foreground/50", dims.div)} aria-hidden />}
          <span className={cn("font-display font-extrabold tracking-[0.06em] text-foreground leading-none", dims.text)}>
            KONNTO{showAi && <span className="ml-1.5 align-top text-[0.5em] font-mono font-medium tracking-[0.18em] text-primary">AI</span>}
          </span>
        </>
      )}
    </div>
  );
};

export default Logo;
