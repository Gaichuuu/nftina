const USD0 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

const MINUS = "−";
const sign = (s: string) => s.replace("-", MINUS);

export function eth(n: number, dp = 2): string { return sign(`${n.toFixed(dp)} Ξ`); }
export function usd(n: number): string { return sign(USD0.format(n)); }
export function compactUsd(n: number): string {
  const a = Math.abs(n);
  if (a >= 1_000_000) return `${n < 0 ? MINUS : ""}$${(a / 1_000_000).toFixed(1)}M`;
  if (a >= 1_000) return `${n < 0 ? MINUS : ""}$${Math.floor(a / 1_000)}K`;
  return sign(USD0.format(n));
}
export function compactUsdDown(n: number): string {
  const a = Math.abs(n);
  if (a >= 1_000_000) return `${n < 0 ? MINUS : ""}$${(Math.floor(a / 100_000) / 10).toFixed(1)}M`;
  if (a >= 1_000) return `${n < 0 ? MINUS : ""}$${Math.floor(a / 1_000)}K`;
  return sign(USD0.format(n));
}
export function ethUsd(e: number, u: number | null | undefined): string {
  return u == null ? eth(e) : `${eth(e)} · ${usd(u)}`;
}
export function shortAddr(a: string): string {
  return a.length <= 12 ? a : `${a.slice(0, 6)}…${a.slice(-4)}`;
}
export function pct(n: number): string { return sign(`${Math.round(n)}%`); }
export const osAssetUrl = (contract: string, tokenId: string) =>
  `https://opensea.io/assets/ethereum/${contract}/${tokenId}`;
export const etherscanAddr = (a: string) => `https://etherscan.io/address/${a}`;
export const etherscanTx = (h: string) => `https://etherscan.io/tx/${h}`;
export const tileGradient = "radial-gradient(circle at 40% 30%,#3a2358,#160a24)";
export function cdnResized(url: string, width: number): string {
  if (!url.includes(".b-cdn.net/") || url.endsWith(".svg")) return url;
  return `${url}?width=${width}`;
}
export function placeholderGradient(seed: string): string {
  let h = 0;
  for (const ch of seed) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return `radial-gradient(circle at 40% 30%, hsl(${h} 60% 38%), hsl(${(h + 45) % 360} 70% 12%))`;
}

export function longDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const at = (opt: Intl.DateTimeFormatOptions) =>
    d.toLocaleDateString("en-US", { ...opt, timeZone: "UTC" });
  const day = Number(at({ day: "numeric" }));
  const rem = day % 100;
  const suffix = rem >= 11 && rem <= 13 ? "th" : ["th", "st", "nd", "rd"][day % 10] ?? "th";
  return `${at({ month: "long" })} ${day}${suffix}, ${at({ year: "numeric" })}`;
}
