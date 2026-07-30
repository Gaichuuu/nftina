import type { ReactNode } from "react";

type Tone = "loss" | "gain" | "hype";
const toneClass = (t?: Tone) =>
  t === "loss" ? "text-loss" : t === "gain" ? "text-gain" : t === "hype" ? "text-hypeB" : "text-ink";

export function StatCell(
  { big, sub, label, tone, numClass = "text-[26px]" }:
  { big: ReactNode; sub?: ReactNode; label: ReactNode; tone?: Tone; numClass?: string }) {
  return (
    <div className="bg-panel px-7 py-6">
      <div className={`${numClass} font-extrabold tracking-tight ${toneClass(tone)}`}>{big}</div>
      {sub && <div className="mt-0.5 text-[12px] font-bold text-dim">{sub}</div>}
      <div className="mt-1.5 font-mono text-[10px] uppercase tracking-[1px] text-muted">{label}</div>
    </div>
  );
}

export function StatStrip(
  { cols, children, className = "" }:
  { cols: number; children: ReactNode; className?: string }) {
  return (
    <div
      className={`grid gap-px overflow-hidden rounded-md border border-line bg-line ${className}`}
      style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
      {children}
    </div>
  );
}
