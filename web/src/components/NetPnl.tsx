import { eth, usd } from "@/lib/format";

export function Signed(
  { v, fmt, className = "" }:
  { v: number; fmt: (n: number) => string; className?: string }) {
  return (
    <div className={`tabular-nums ${v < 0 ? "text-loss" : "text-gain"} ${className}`}>
      {v < 0 ? "" : "+"}{fmt(v)}
    </div>
  );
}

export default function NetPnl({ ethv, usdv }: { ethv: number; usdv: number }) {
  return (
    <div className="text-right tabular-nums">
      <Signed v={ethv} fmt={eth} className="text-[12.5px] font-bold" />
      <Signed v={usdv} fmt={usd} className="font-mono text-[11px] opacity-75" />
    </div>
  );
}
