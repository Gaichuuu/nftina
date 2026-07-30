import type { ReactNode } from "react";

type Tone = "loss" | "gain" | "hype";
const toneClass = (t?: Tone) =>
  t === "loss" ? "text-loss" : t === "gain" ? "text-gain" : t === "hype" ? "text-hypeB" : "text-ink";

export function StatCell(
  { big, sub, label, tone, bg = "bg-panel", numClass = "text-[20px] sm:text-[24px]" }:
  { big: ReactNode; sub?: ReactNode; label: ReactNode; tone?: Tone; bg?: string; numClass?: string }) {
  return (
    <div className={`${bg} px-4 py-4 sm:px-6 sm:py-5`}>
      <div className={`${numClass} font-extrabold tracking-[-0.02em] tabular-nums ${toneClass(tone)}`}>{big}</div>
      {sub && <div className="mt-0.5 text-[12px] font-bold tabular-nums text-dim">{sub}</div>}
      <div className="mt-2 font-mono text-[10px] font-semibold uppercase tracking-widest text-muted">{label}</div>
    </div>
  );
}

export function StatStrip(
  { children, className = "" }:
  { children: ReactNode; className?: string }) {
  return (
    <div className={`grid gap-px overflow-hidden rounded-md border border-line bg-line ${className}`}>
      {children}
    </div>
  );
}
