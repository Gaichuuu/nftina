import { useMemo } from "react";
import { Link } from "react-router-dom";
import type { WalletProfile } from "@/data/runtime";
import { eth, usd, etherscanAddr, tileGradient, cdnResized } from "@/lib/format";
import { collections } from "@/data/bundled";
import { walletName, hasWalletName, useWalletIdentities } from "@/data/identities";
import Bar from "./Bar";
import LoopMedia from "./LoopMedia";
import NetPnl, { Signed } from "./NetPnl";
import WalletAvatar from "./WalletAvatar";
import XferCell from "./XferCell";

/** metric tiles */
function Metric({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-panel2 px-4.5 py-3 text-left">
      <div className="mb-1 font-mono text-[9px] font-semibold uppercase tracking-widest text-muted">
        {label}
      </div>
      {children}
    </div>
  );
}

function RankScale({ rank, total, addr }: { rank: number; total: number; addr: string }) {
  const pct = total > 1 ? ((rank - 1) / (total - 1)) * 100 : 0;
  return (
    <div className="hidden shrink-0 flex-col items-center pl-1 sm:flex" style={{ width: 88 }}
         aria-label={`Overall rank ${rank} of ${total}`}>
      <div className="mb-2 font-mono text-[9px] leading-none tracking-[0.08em] text-muted">RANK #1</div>
      <div className="relative w-1.5 flex-1 rounded-full"
           style={{ background: "linear-gradient(180deg,#8be9ff,#ff5cf0)", minHeight: 120 }}>
        <div className="absolute left-1/2 flex items-center gap-1"
             style={{ top: `${pct}%`, transform: "translate(-50%,-50%)" }}>
          <WalletAvatar addr={addr} size={22} />
          <span className="whitespace-nowrap rounded bg-panel px-1 font-mono text-[10px] text-ink
                           ring-1 ring-line">
            #{rank.toLocaleString()}
          </span>
        </div>
      </div>
      <div className="mt-2 font-mono text-[9px] leading-none tracking-[0.08em] text-muted">
        {total.toLocaleString()}
      </div>
    </div>
  );
}

/** Column-group dividers */
const GROUP_L = "border-l border-line";

export default function WalletProfileView({ p }: { p: WalletProfile }) {
  const logos = useMemo(
    () => Object.fromEntries(collections.map((c) => [c.collection, c.image ?? null])), []);
  useWalletIdentities();
  const heldMax = Math.max(1, ...p.collections.map((c) => c.entry?.tokens_held ?? 0));
  const o = p.overall;
  const allIn = o ? (o.all_in_net_usd ?? o.net_pnl_usd ?? 0) : 0;

  return (
    <div className="text-left">
      {/* identity */}
      <div className="flex flex-wrap items-center gap-5 rounded-md border border-line bg-panel px-5 py-4.5">
        <WalletAvatar addr={p.address} size={44} />
        <div className="min-w-0 flex-1">
          <div className="font-mono text-[10px] font-semibold uppercase tracking-widest text-muted">
            Wallet
          </div>
          {hasWalletName(p.address) && (
            <div className="truncate text-[15px] font-bold text-ink">{walletName(p.address)}</div>
          )}
          <a href={etherscanAddr(p.address)} target="_blank" rel="noopener noreferrer"
             className="block break-all font-mono text-[13px] text-dim2 no-underline
                        transition-colors hover:text-hypeB">
            {p.address}
          </a>
        </div>
        {o && (
          <div className="grid w-full grid-cols-1 gap-px overflow-hidden rounded-[10px] border
                          border-line bg-line min-[480px]:grid-cols-3 lg:w-auto lg:min-w-90">
            <Metric label="On-chain P&L">
              <Signed v={o.net_pnl_eth} fmt={eth} className="text-[18px] font-extrabold" />
              <Signed v={o.net_pnl_usd ?? 0} fmt={usd} className="font-mono text-[11px] opacity-75" />
            </Metric>
            <Metric label="Total USD">
              <Signed v={allIn} fmt={usd} className="text-[18px] font-extrabold" />
              {(o.offchain_cost_usd ?? 0) > 0 && (
                <div className="font-mono text-[11px] tabular-nums text-muted">
                  {usd(-o.offchain_cost_usd!)} off-chain
                </div>
              )}
            </Metric>
            <Metric label="Rank">
              {p.overallRank != null ? (
                <>
                  <div className="text-[18px] font-extrabold tabular-nums text-ink">
                    #{p.overallRank.toLocaleString()}
                  </div>
                  <div className="font-mono text-[11px] tabular-nums text-muted">
                    of {p.overallTotal.toLocaleString()}
                  </div>
                </>
              ) : (
                <div className="text-[18px] font-extrabold text-muted">—</div>
              )}
            </Metric>
          </div>
        )}
      </div>

      {/* per-collection ranked rows */}
      <div className="mt-3 flex items-stretch gap-3">
        <div className="min-w-0 flex-1 overflow-x-auto rounded-md border border-line">
          <table className="w-full min-w-150 text-[12.5px] tabular-nums">
            <thead className="bg-panel2 font-mono text-[10px] font-semibold uppercase tracking-widest text-muted">
              <tr>
                <th className="px-4 py-3 text-left">RANK</th>
                <th className="px-4 py-3 text-left">COLLECTION</th>
                <th className={`px-4 py-3 text-left ${GROUP_L}`}>OWNS</th>
                <th className={`px-2.5 py-3 text-right ${GROUP_L}`}>MINTED</th>
                <th className="px-2.5 py-3 text-right">BOUGHT</th>
                <th className="px-2.5 py-3 text-right">SOLD</th>
                <th className="px-2.5 py-3 text-right"
                    title="Net tokens moved in/out via non-sale transfer (airdrops, gifts)">XFERS</th>
                <th className={`px-4 py-3 text-right ${GROUP_L}`}>NET</th>
              </tr>
            </thead>
            <tbody>
              {p.collections.map((c) => {
                const e = c.entry;
                return (
                  <tr key={c.slug}
                      className="border-t border-line align-middle transition-colors hover:bg-hover">
                    <td className="px-4 py-3.25 font-mono text-[11px] text-dim">
                      {c.rank != null
                        ? <>#{c.rank.toLocaleString()}<span className="text-muted">/{c.total.toLocaleString()}</span></>
                        : <span className="text-muted">n/a</span>}
                    </td>
                    <td className="px-4 py-3.25">
                      <Link to={`/collections/${c.slug}`}
                            className="group flex items-center gap-2 no-underline">
                        <span className="inline-block h-6 w-6 shrink-0 overflow-hidden rounded-[6px]"
                              style={{ background: tileGradient }}>
                          <LoopMedia image={logos[c.slug] && cdnResized(logos[c.slug]!, 64)} alt={c.name}
                                     className="h-full w-full object-cover" />
                        </span>
                        <span className={`font-bold transition-colors group-hover:text-hypeB ${e ? "text-ink" : "text-muted"}`}>
                          {c.name}</span>
                      </Link>
                    </td>
                    <td className={`px-4 py-3.25 ${GROUP_L}`}>
                      <div className="flex items-center gap-2">
                        <span className="min-w-5.5 text-right font-bold text-ink">
                          {e?.tokens_held ?? 0}
                        </span>
                        <Bar value={e?.tokens_held ?? 0} max={heldMax} variant="own" min={6}
                             className="w-14 shrink-0" />
                      </div>
                    </td>
                    <td className={`px-2.5 py-3.25 text-right font-mono text-[11.5px] text-dim ${GROUP_L}`}>
                      {e?.tokens_minted ?? 0}
                    </td>
                    <td className="px-2.5 py-3.25 text-right font-mono text-[11.5px] text-dim">
                      {e?.tokens_bought ?? 0}
                    </td>
                    <td className="px-2.5 py-3.25 text-right font-mono text-[11.5px] text-dim">
                      {e?.tokens_sold ?? 0}
                    </td>
                    <td className="px-2.5 py-3.25 text-right font-mono text-[11.5px]">
                      {e ? <XferCell e={e} /> : <span className="text-muted">—</span>}
                    </td>
                    <td className={`px-4 py-3.25 ${GROUP_L}`}>
                      {e
                        ? <NetPnl ethv={e.net_pnl_eth} usdv={e.net_pnl_usd} />
                        : <div className="text-right text-muted">—</div>}
                      {e && typeof e.all_in_net_usd === "number" && (
                        <div className="text-right font-mono text-[10px] text-muted"
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
      <p className="mt-2 max-w-205 font-mono text-[10px] leading-normal text-muted">
        Total USD includes off-chain physical box purchases required for certain mints:
        PFP 2.0 $100, Valentines $30, Wilderness $150.
      </p>
    </div>
  );
}
