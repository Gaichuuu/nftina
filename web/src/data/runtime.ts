import { z } from "zod";
import { WalletRow, TokenRow, Holders } from "./schemas";
import type { Holders as HoldersT, HolderEntry, WalletRow as WalletRowT } from "./schemas";

let walletCache: WalletRow[] | null = null;
export async function fetchWalletIndex(): Promise<WalletRow[]> {
  if (walletCache) return walletCache;
  const res = await fetch("/data/wallet_index.json");
  if (!res.ok) throw new Error(`wallet_index ${res.status}`);
  walletCache = z.array(WalletRow).parse(await res.json());
  return walletCache;
}

const tokenCache: Record<string, TokenRow[]> = {};
export async function fetchTokens(slug: string): Promise<TokenRow[]> {
  if (tokenCache[slug]) return tokenCache[slug];
  const res = await fetch(`/data/collections/${slug}/tokens.json`);
  if (!res.ok) throw new Error(`tokens ${slug} ${res.status}`);
  tokenCache[slug] = z.array(TokenRow).parse(await res.json());
  return tokenCache[slug];
}

const holdersCache: Record<string, HoldersT["holders"]> = {};
export async function fetchHolders(slug: string): Promise<HoldersT["holders"]> {
  if (holdersCache[slug]) return holdersCache[slug];
  const res = await fetch(`/data/collections/${slug}/holders.json`);
  if (!res.ok) throw new Error(`holders ${slug} ${res.status}`);
  holdersCache[slug] = Holders.parse(await res.json()).holders;
  return holdersCache[slug];
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
): { pos: number; total: number } {
  const sorted = [...rows].sort((a, b) => b.net_pnl_eth - a.net_pnl_eth);
  return { pos: sorted.findIndex((r) => r.wallet.toLowerCase() === addr), total: sorted.length };
}

export async function fetchWalletProfile(
  addr: string, names: Record<string, string>,
): Promise<WalletProfile> {
  const a = addr.toLowerCase();
  const idx = await fetchWalletIndex();
  const overall = (r: WalletRowT) => r.all_in_net_usd ?? r.net_pnl_usd ?? r.net_pnl_eth;
  const overallSorted = [...idx].sort((x, y) => overall(y) - overall(x));
  const oPos = overallSorted.findIndex((r) => r.wallet.toLowerCase() === a);

  const collections: WalletCollectionRow[] = [];
  for (const slug of PROFILE_SLUGS) {
    const holders = await fetchHolders(slug).catch(() => [] as HolderEntry[]);
    const { pos, total } = rankIn(holders, a);
    const entry = pos >= 0
      ? [...holders].sort((x, y) => y.net_pnl_eth - x.net_pnl_eth)[pos] : null;
    collections.push({ slug, name: names[slug] ?? slug, rank: pos >= 0 ? pos + 1 : null, total, entry });
  }
  return {
    address: addr, overall: oPos >= 0 ? overallSorted[oPos] : null,
    overallRank: oPos >= 0 ? oPos + 1 : null, overallTotal: idx.length, collections,
  };
}
