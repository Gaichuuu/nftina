const USD0 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export function eth(n: number, dp = 2): string { return `${n.toFixed(dp)} Ξ`; }
export function usd(n: number): string { return USD0.format(n); }
export function compactUsd(n: number): string {
  const a = Math.abs(n);
  if (a >= 1_000_000) return `${n < 0 ? "-" : ""}$${(a / 1_000_000).toFixed(1)}M`;
  if (a >= 1_000) return `${n < 0 ? "-" : ""}$${Math.floor(a / 1_000)}K`;
  return USD0.format(n);
}
export function compactUsdDown(n: number): string {
  const a = Math.abs(n);
  if (a >= 1_000_000) return `${n < 0 ? "-" : ""}$${(Math.floor(a / 100_000) / 10).toFixed(1)}M`;
  if (a >= 1_000) return `${n < 0 ? "-" : ""}$${Math.floor(a / 1_000)}K`;
  return USD0.format(n);
}
export function ethUsd(e: number, u: number | null | undefined): string {
  return u == null ? eth(e) : `${eth(e)} · ${usd(u)}`;
}
export function shortAddr(a: string): string {
  return a.length <= 12 ? a : `${a.slice(0, 6)}…${a.slice(-4)}`;
}
export function pct(n: number): string { return `${Math.round(n)}%`; }
export const osAssetUrl = (contract: string, tokenId: string) =>
  `https://opensea.io/assets/ethereum/${contract}/${tokenId}`;
export const etherscanAddr = (a: string) => `https://etherscan.io/address/${a}`;
export function placeholderGradient(seed: string): string {
  let h = 0;
  for (const ch of seed) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return `radial-gradient(circle at 40% 30%, hsl(${h} 60% 38%), hsl(${(h + 45) % 360} 70% 12%))`;
}
