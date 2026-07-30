import type { VolumeSeries } from "@/data/schemas";
import { eth, usd } from "@/lib/format";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
// "2021-07" -> "Jul 2021"
function fmtMonth(m?: string): string {
  if (!m) return "";
  const [y, mm] = m.split("-");
  return `${MONTHS[Number(mm) - 1] ?? mm} ${y}`;
}

export default function VolumeChart(
  { points, variant = "panel", centerLabel = "Secondary sales across all MetaZoo collections" }:
  { points: VolumeSeries["ecosystem"]; variant?: "panel" | "header"; centerLabel?: string }) {
  const max = Math.max(1, ...points.map((p) => p.eth));
  const peak = points.reduce((a, b) => (b.eth > a.eth ? b : a), points[0]);
  if (variant === "header") {
    return (
      <div aria-hidden className="pointer-events-none absolute inset-0 flex items-end gap-0.5 opacity-25">
        {points.map((p) => (
          <span key={p.month} className="block flex-1"
                style={{ height: `${Math.max(2, (p.eth / max) * 100)}%`,
                         background: "linear-gradient(var(--color-hypeA),var(--color-hypeB))" }} />
        ))}
      </div>
    );
  }
  return (
    <div>
      <div role="img" aria-label={`Monthly secondary volume, peak ${eth(peak.eth)} (${usd(peak.usd)}) in ${fmtMonth(peak.month)}`}
           className="flex h-50 items-end gap-0.75 rounded-md border border-line bg-panel3 p-4">
        {points.map((p) => (
          <div key={p.month} title={`${fmtMonth(p.month)}: ${eth(p.eth)} · ${usd(p.usd)}`}
               className="flex h-full flex-1 flex-col justify-end">
            <span className="block w-full rounded-t-[2px]"
                  style={{ height: `${Math.max(2, (p.eth / max) * 100)}%`,
                           background: "linear-gradient(var(--color-hypeA),var(--color-hypeB))" }} />
          </div>
        ))}
      </div>
      <div className="mt-2.5 flex justify-between font-mono text-[11px] text-muted">
        <span>{fmtMonth(points[0]?.month)}</span>
        <span className="hidden sm:inline">{centerLabel}</span>
        <span>{fmtMonth(points[points.length - 1]?.month)}</span>
      </div>
    </div>
  );
}
