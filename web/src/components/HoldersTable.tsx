import { useEffect, useMemo, useState } from "react";
import { fetchHolders } from "@/data/runtime";
import type { HolderEntry } from "@/data/schemas";
import { etherscanAddr } from "@/lib/format";
import useInfiniteScroll from "@/lib/useInfiniteScroll";
import { walletName, hasWalletName, useWalletIdentities } from "@/data/identities";
import Bar from "./Bar";
import NetPnl from "./NetPnl";
import PnlButton from "./PnlButton";
import WalletAvatar from "./WalletAvatar";
import WalletPnlDialog from "./WalletPnlDialog";
import XferCell from "./XferCell";

const PAGE = 50;

type SortKey = "lost" | "gained" | "owned" | "minted";
const SORTS: Record<SortKey, (a: HolderEntry, b: HolderEntry) => number> = {
  lost: (a, b) => a.net_pnl_eth - b.net_pnl_eth,
  gained: (a, b) => b.net_pnl_eth - a.net_pnl_eth,
  owned: (a, b) => b.tokens_held - a.tokens_held,
  minted: (a, b) => (b.tokens_minted ?? 0) - (a.tokens_minted ?? 0),
};
const SORT_LABELS: [SortKey, string][] = [
  ["lost", "Most lost"], ["gained", "Most gained"], ["owned", "Most owned"], ["minted", "Most minted"],
];

export default function HoldersTable({ slug }: { slug: string }) {
  const [rows, setRows] = useState<HolderEntry[] | null>(null);
  const [sort, setSort] = useState<SortKey>("owned");
  const [pnlWallet, setPnlWallet] = useState<string | null>(null);
  const { shown, reset, sentinelRef } = useInfiniteScroll(PAGE);
  useWalletIdentities();

  useEffect(() => {
    let ok = true;
    setRows(null); reset();
    fetchHolders(slug).then((r) => { if (ok) setRows(r); }).catch(() => { if (ok) setRows([]); });
    return () => { ok = false; };
  }, [slug, reset]);

  const sorted = useMemo(() => (rows ? [...rows].sort(SORTS[sort]) : []), [rows, sort]);
  const heldMax = useMemo(() => Math.max(1, ...(rows ?? []).map((r) => r.tokens_held)), [rows]);

  if (rows === null)
    return <div className="py-16 text-center font-mono text-[12px] text-muted">loading holders…</div>;
  if (rows.length === 0)
    return <div className="py-16 text-center font-mono text-[12px] text-muted">no holder data.</div>;

  return (
    <div className="py-7">
      <div className="mb-2 flex items-center justify-between gap-2 font-mono text-[10px] text-muted">
        <span>{rows.length.toLocaleString()} wallets</span>
        <span className="flex items-center gap-2">
          <label htmlFor="holders-sort">sort</label>
          <select id="holders-sort" value={sort}
                  onChange={(e) => { setSort(e.target.value as SortKey); reset(); }}
                  className="rounded-sm border border-line bg-panel px-1.5 py-0.5 text-ink">
            {SORT_LABELS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </span>
      </div>
      <div className="overflow-x-auto rounded-md border border-line">
        <table className="w-full min-w-170 text-[12.5px] tabular-nums">
          <thead className="bg-panel2 font-mono text-[10px] font-semibold uppercase tracking-widest text-muted">
            <tr>
              <th className="px-4 py-3 text-left">WALLET</th>
              <th className="px-4 py-3 text-left">OWNS</th>
              <th className="px-4 py-3 text-right">MINTED</th>
              <th className="px-4 py-3 text-right">BOUGHT</th>
              <th className="px-4 py-3 text-right">SOLD</th>
              <th className="px-4 py-3 text-right"
                  title="Net tokens moved in/out via non-sale transfer (airdrops, gifts)">TRANSFERS</th>
              <th className="px-4 py-3 text-right">NET LOST / GAINED</th>
            </tr>
          </thead>
          <tbody>
            {sorted.slice(0, shown).map((e) => {
              const named = hasWalletName(e.wallet);
              return (
                <tr key={e.wallet}
                    className="border-t border-line align-middle transition-colors hover:bg-hover">
                  <td className="px-4 py-3.25">
                    <div className="flex items-center gap-2.5">
                      <a href={etherscanAddr(e.wallet)} target="_blank" rel="noopener noreferrer"
                         className="flex min-w-0 items-center gap-2.5 no-underline hover:opacity-90"
                         title={`${e.wallet} · view on Etherscan`}>
                        <WalletAvatar addr={e.wallet} />
                        <span className="min-w-0">
                          {named && (
                            <span className="block truncate font-bold text-ink">
                              {walletName(e.wallet)}{e.metazoo && <span title="MetaZoo-controlled"> ⚑</span>}
                            </span>
                          )}
                          <span className="block break-all font-mono text-[11px] text-dim">
                            {e.wallet}{!named && e.metazoo && <span title="MetaZoo-controlled"> ⚑</span>}
                          </span>
                        </span>
                      </a>
                      <PnlButton onClick={() => setPnlWallet(e.wallet)} />
                    </div>
                  </td>
                  <td className="px-4 py-3.25">
                    <div className="flex items-center gap-2">
                      <span className="min-w-6.5 text-right font-bold text-ink">{e.tokens_held}</span>
                      <Bar value={e.tokens_held} max={heldMax} variant="own" min={4}
                           className="w-16 shrink-0" />
                    </div>
                  </td>
                  <td className="px-4 py-3.25 text-right text-dim">{e.tokens_minted ?? 0}</td>
                  <td className="px-4 py-3.25 text-right text-dim">{e.tokens_bought}</td>
                  <td className="px-4 py-3.25 text-right text-dim">{e.tokens_sold}</td>
                  <td className="px-4 py-3.25 text-right"><XferCell e={e} /></td>
                  <td className="px-4 py-3.25"><NetPnl ethv={e.net_pnl_eth} usdv={e.net_pnl_usd} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="mt-2 text-center font-mono text-[10px] text-muted">
        {Math.min(shown, sorted.length).toLocaleString()} / {sorted.length.toLocaleString()} wallets
      </div>
      {shown < sorted.length && <div ref={sentinelRef} aria-hidden className="h-px" />}
      <p className="mt-2 font-mono text-[10px] leading-normal text-muted">
        Every wallet that held, minted, bought, or sold in this collection. Owned = minted + bought
        + transfers − sold, where transfers are non-sale moves in/out (airdrops, gifts). Net = realized
        P&amp;L (sales minus cost) minus unrealized loss (held tokens vs current floor) minus gas fees paid,
        valued when the ETH moved. The bar shows tokens still owned. Rows link to Etherscan;
        the P&amp;L button opens the wallet's full breakdown.
      </p>
      {pnlWallet && <WalletPnlDialog address={pnlWallet} onClose={() => setPnlWallet(null)} />}
    </div>
  );
}
