import { z } from "zod";
import { WalletRow, TokenRow, Holders } from "./schemas";
import type { Holders as HoldersT, HolderEntry, WalletRow as WalletRowT } from "./schemas";

const cache: Record<string, Promise<unknown>> = {};
function cachedFetch<T>(path: string, parse: (data: unknown) => T): Promise<T> {
  const hit = cache[path];
  if (hit) return hit as Promise<T>;
  const p = (async () => {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`${path} ${res.status}`);
    return parse(await res.json());
  })();
  cache[path] = p;
  p.catch(() => { delete cache[path]; });
  return p;
}

export function fetchWalletIndex(): Promise<WalletRow[]> {
  return cachedFetch("/data/wallet_index.json", (d) => z.array(WalletRow).parse(d));
}

export function fetchTokens(slug: string): Promise<TokenRow[]> {
  return cachedFetch(`/data/collections/${slug}/tokens.json`, (d) => z.array(TokenRow).parse(d));
}

export function fetchHolders(slug: string): Promise<HoldersT["holders"]> {
  return cachedFetch(`/data/collections/${slug}/holders.json`, (d) => Holders.parse(d).holders);
}

export const PROFILE_SLUGS = [
  "genesis_2021", "genesis_reissue_1155", "coin_tokens", "beasties_s1", "pfp_2",
  "valentines", "wilderness",
] as const;

export type WalletCollectionRow = {
  slug: string; name: string; rank: number | null; total: number; entry: HolderEntry | null;
};
export type WalletProfile = {
  address: string;
  overall: WalletRowT | null;
  overallRank: number | null;
  overallTotal: number;
  collections: WalletCollectionRow[];
};

function rankIn<T extends { wallet: string; net_pnl_eth: number }>(
  rows: T[], addr: string,
): { pos: number; total: number; entry: T | null } {
  const sorted = [...rows].sort((a, b) => b.net_pnl_eth - a.net_pnl_eth);
  const pos = sorted.findIndex((r) => r.wallet.toLowerCase() === addr);
  return { pos, total: sorted.length, entry: pos >= 0 ? sorted[pos] : null };
}

export async function fetchWalletProfile(
  addr: string, names: Record<string, string>,
): Promise<WalletProfile> {
  const a = addr.toLowerCase();
  const idx = await fetchWalletIndex();
  const overall = (r: WalletRowT) => r.all_in_net_usd ?? r.net_pnl_usd ?? r.net_pnl_eth;
  const overallSorted = [...idx].sort((x, y) => overall(y) - overall(x));
  const oPos = overallSorted.findIndex((r) => r.wallet.toLowerCase() === a);

  const collections: WalletCollectionRow[] = await Promise.all(
    PROFILE_SLUGS.map(async (slug) => {
      const holders = await fetchHolders(slug).catch(() => [] as HolderEntry[]);
      const { pos, total, entry } = rankIn(holders, a);
      return { slug, name: names[slug] ?? slug, rank: pos >= 0 ? pos + 1 : null, total, entry };
    }),
  );
  return {
    address: addr, overall: oPos >= 0 ? overallSorted[oPos] : null,
    overallRank: oPos >= 0 ? oPos + 1 : null, overallTotal: idx.length, collections,
  };
}
