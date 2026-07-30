import { useMemo, useState } from "react";
import type { WalletProfile } from "@/data/runtime";
import { usd, etherscanAddr } from "@/lib/format";
import { collections } from "@/data/bundled";
import { walletName, hasWalletName, useWalletIdentities } from "@/data/identities";
import Bar from "./Bar";
import NetPnl from "./NetPnl";
import WalletAvatar from "./WalletAvatar";
import XferCell from "./XferCell";

function UsdNet({ usdv }: { usdv: number }) {
  const down = usdv < 0;
  return (
    <div className={`text-[18px] font-bold ${down ? "text-loss" : "text-gain"}`}>
      {down ? "−" : "+"}{usd(Math.abs(usdv))}
    </div>
  );
}

function OwnedCell({ n, max }: { n: number; max: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="min-w-5 text-right font-bold text-ink">{n}</span>
      <Bar value={n} max={max} gradient="held" min={6} className="h-1.5 w-12 shrink-0 rounded-[3px]" />
    </div>
  );
}

function CollectionLogo({ src, alt }: { src?: string | null; alt: string }) {
  const [failed, setFailed] = useState(false);
  return (
    <span className="inline-block h-6 w-6 shrink-0 overflow-hidden rounded"
          style={{ background: "radial-gradient(circle at 40% 30%,#3a2358,#160a24)" }}>
      {src && !failed && (
        <img src={src} alt={alt} loading="lazy" onError={() => setFailed(true)}
             className="h-full w-full object-cover" />
      )}
    </span>
  );
}

function RankScale({ rank, total, addr }: { rank: number; total: number; addr: string }) {
  const pct = total > 1 ? ((rank - 1) / (total - 1)) * 100 : 0;
  return (
    <div className="hidden shrink-0 flex-col items-center pl-1 sm:flex" style={{ width: 74 }}
         aria-label={`Overall rank ${rank} of ${total}`}>
      <div className="mb-1 font-mono text-[9px] leading-none text-muted">RANK #1</div>
      <div className="relative w-1.5 flex-1 rounded-full"
           style={{ background: "linear-gradient(180deg,#8be9ff,#ff5cf0)", minHeight: 100 }}>
        <div className="absolute left-1/2 flex items-center gap-1"
             style={{ top: `${pct}%`, transform: "translate(-50%,-50%)" }}>
          <WalletAvatar addr={addr} size={22} />
          <span className="whitespace-nowrap rounded bg-panel px-1 font-mono text-[9px] text-ink">
            #{rank.toLocaleString()}
          </span>
        </div>
      </div>
      <div className="mt-1 font-mono text-[9px] leading-none text-muted">{total.toLocaleString()}</div>
    </div>
  );
}

export default function WalletProfileView({ p }: { p: WalletProfile }) {
  const logos = useMemo(
    () => Object.fromEntries(collections.map((c) => [c.collection, c.image ?? null])), []);
  useWalletIdentities();
  const heldMax = Math.max(1, ...p.collections.map((c) => c.entry?.tokens_held ?? 0));

  return (
    <div className="text-left">
      {/* identity + overall P&L / rank */}
      <div className="flex flex-wrap items-center gap-3.5 rounded-md border border-line bg-panel p-4">
        <WalletAvatar addr={p.address} />
        <div className="min-w-0 flex-1">
          {hasWalletName(p.address) && (
            <div className="truncate text-[15px] font-bold text-ink">{walletName(p.address)}</div>
          )}
          <a href={etherscanAddr(p.address)} target="_blank" rel="noopener noreferrer"
             className="block break-all font-mono text-[11px] text-dim no-underline hover:text-hypeB">
            {p.address}
          </a>
        </div>
        {p.overall && (
          <div className="flex flex-wrap items-center gap-5">
            <div>
              <div className="font-mono text-[9px] uppercase tracking-[1px] text-muted">Wallet P&amp;L</div>
              <NetPnl ethv={p.overall.net_pnl_eth} usdv={p.overall.net_pnl_usd ?? 0} />
              {/* <div className="font-mono text-[9px] text-muted">on-chain</div> */}
            </div>
            <div>
              <div className="font-mono text-[9px] uppercase tracking-[1px] text-muted">Overall (USD)</div>
              <UsdNet usdv={p.overall.all_in_net_usd ?? p.overall.net_pnl_usd ?? 0} />
              {/* <div className="font-mono text-[9px] text-muted">
                {(p.overall.offchain_cost_usd ?? 0) > 0
                  ? `incl. ${usd(p.overall.offchain_cost_usd!)} off-chain*`
                  : "incl. off-chain box"}
              </div> */}
            </div>
            {p.overallRank != null && (
              <div className="text-right">
                <div className="font-mono text-[9px] uppercase tracking-[1px] text-muted">Rank</div>
                <div className="text-[16px] font-black text-ink">#{p.overallRank.toLocaleString()}</div>
                <div className="font-mono text-[10px] text-muted">of {p.overallTotal.toLocaleString()}</div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* per-collection ranked rows (all tracked collections) + a vertical rank scale */}
      <div className="mt-3 flex items-stretch gap-2">
        <div className="min-w-0 flex-1 overflow-x-auto rounded-md border border-line">
          <table className="w-full text-[12px]">
            <thead className="bg-panel2 font-mono text-[10px] tracking-[1px] text-muted">
              <tr>
                <th className="px-3 py-2 text-left font-semibold">RANK</th>
                <th className="px-3 py-2 text-left font-semibold">COLLECTION</th>
                <th className="px-3 py-2 text-left font-semibold">OWNS</th>
                <th className="px-3 py-2 text-right font-semibold">MINTED</th>
                <th className="px-3 py-2 text-right font-semibold">BOUGHT</th>
                <th className="px-3 py-2 text-right font-semibold">SOLD</th>
                <th className="px-3 py-2 text-right font-semibold"
                    title="Net tokens moved in/out via non-sale transfer (airdrops, gifts)">TRANSFERS</th>
                <th className="px-3 py-2 text-right font-semibold">NET</th>
              </tr>
            </thead>
            <tbody>
              {p.collections.map((c) => {
                const e = c.entry;
                return (
                  <tr key={c.slug} className="border-t border-line align-middle">
                    <td className="px-3 py-2.5 font-mono text-[11px] text-dim">
                      {c.rank != null
                        ? <>#{c.rank.toLocaleString()}<span className="text-muted">/{c.total.toLocaleString()}</span></>
                        : <span className="text-muted">n/a</span>}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        <CollectionLogo src={logos[c.slug]} alt={c.name} />
                        <span className={e ? "font-bold text-ink" : "font-bold text-muted"}>{c.name}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5"><OwnedCell n={e?.tokens_held ?? 0} max={heldMax} /></td>
                    <td className="px-3 py-2.5 text-right text-dim">{e?.tokens_minted ?? 0}</td>
                    <td className="px-3 py-2.5 text-right text-dim">{e?.tokens_bought ?? 0}</td>
                    <td className="px-3 py-2.5 text-right text-dim">{e?.tokens_sold ?? 0}</td>
                    <td className="px-3 py-2.5 text-right">{e ? <XferCell e={e} /> : <span className="text-muted">—</span>}</td>
                    <td className="px-3 py-2.5">
                      {e
                        ? <NetPnl ethv={e.net_pnl_eth} usdv={e.net_pnl_usd} />
                        : <div className="text-right text-muted">—</div>}
                      {e && typeof e.all_in_net_usd === "number" && (
                        <div className="mt-0.5 text-right text-[10px] text-loss opacity-80"
                             title="Includes the off-chain physical box, one per mint (not in the on-chain figures)">
                          (off-chain) {usd(e.all_in_net_usd)}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {p.overallRank != null && <RankScale rank={p.overallRank} total={p.overallTotal} addr={p.address} />}
      </div>
      <p className="mt-2 font-mono text-[10px] leading-normal text-muted">
        Overall USD includes off-chain physical box purchases required for certain mints: PFP 2.0 $100, Valentines $30, Wilderness $150
      </p>
    </div>
  );
}
