import { useNavigate } from "react-router-dom";
import { collections, summary } from "@/data/bundled";
import type { Collection } from "@/data/schemas";
import { floorLabelFor } from "@/data/collectionUiConfig";
import Bar from "@/components/Bar";
import LoopMedia from "@/components/LoopMedia";
import { eth, compactUsd, tileGradient, cdnResized } from "@/lib/format";
import Container from "@/components/Container";
import TableScroller from "@/components/TableScroller";
import { StatCell, StatStrip } from "@/components/StatCell";

function Thumb({ c }: { c: Collection }) {
  return (
    <div className="h-11 w-11 shrink-0 overflow-hidden rounded-sm"
         style={{ background: tileGradient }}>
      <LoopMedia image={c.image && cdnResized(c.image, 96)} video={c.video} alt={c.name}
                 className="h-full w-full object-cover" />
    </div>
  );
}

function floorLabel(c: Collection): string {
  return floorLabelFor(c.collection) ?? (c.floor_eth > 0 ? `${c.floor_eth} Ξ` : "n/a");
}

export default function CollectionsPage() {
  const nav = useNavigate();
  const totalMints = collections.reduce((s, c) => s + c.total_mints, 0);
  const secMax = Math.max(1, ...collections.map((c) => c.secondary_volume_eth));
  const ranked = [...collections].sort((a, b) => b.secondary_volume_eth - a.secondary_volume_eth);

  return (
    <div>
      {/* hero */}
      <section style={{ background: "radial-gradient(90% 130% at 82% 20%, #241238, #0c0912 64%)" }}>
        <Container className="pt-12">
          {/* <div className="eyebrow text-hypeB">The catalogue</div> */}
          <h1 className="text-[40px] font-black leading-none tracking-[-0.03em] text-ink sm:text-[52px]">
            MetaZoo NFT collections
          </h1>
          <p className="mt-4 max-w-140 text-pretty text-[15px] leading-[1.6] text-dim">
            Every contract MetaZoo minted, ranked by the money that moved through it on secondary markets.
          </p>
          <div className="mt-8.5">
            <StatStrip className="grid-cols-2 sm:grid-cols-4">
              <StatCell big={totalMints.toLocaleString()}
                        label="Total mints" />
              <StatCell big={eth(summary.total_mint_revenue_eth)}
                        sub={compactUsd(summary.total_mint_revenue_usd)} label="Mint revenue" />
              <StatCell big={eth(summary.secondary_volume_eth)}
                        sub={compactUsd(ranked.reduce((s, c) => s + (c.secondary_volume_usd ?? 0), 0))}
                        label="Secondary volume" />
              <StatCell tone="hype"
                        big={eth(summary.royalties_to_metazoo_eth)}
                        sub={compactUsd(ranked.reduce((s, c) => s + (c.royalty_usd ?? 0), 0))}
                        label="→ MetaZoo royalties" />
            </StatStrip>
          </div>
        </Container>
      </section>

      {/* ranked table */}
      <Container className="pb-12 pt-10">
        <TableScroller>
          <table className="w-full min-w-170 text-[12.5px] tabular-nums">
            <thead className="bg-panel2 font-mono text-[10px] font-semibold uppercase tracking-widest text-muted">
              <tr>
                <th className="px-4 py-3 text-left">COLLECTION</th>
                <th className="px-4 py-3 text-right">MINTS</th>
                <th className="px-4 py-3 text-right">MINT REVENUE</th>
                <th className="w-[26%] px-4 py-3 text-left">SECONDARY VOLUME</th>
                <th className="px-4 py-3 text-right">ROYALTIES</th>
                <th className="px-4 py-3 text-right">FLOOR</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((c) => (
                <tr key={c.collection} onClick={() => nav(`/collections/${c.collection}`)}
                    className="cursor-pointer border-t border-line transition-colors hover:bg-hover">
                  <td className="px-4 py-3.25">
                    <div className="flex items-center gap-3.5">
                      <Thumb c={c} />
                      <div>
                        <div className="text-[14px] font-bold text-ink">{c.name}</div>
                        <div className="font-mono text-[10px] uppercase tracking-[0.06em] text-muted">
                          {c.standard}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3.25 text-right text-dim2">
                    {c.total_mints > 0 ? c.total_mints.toLocaleString() : <span className="text-muted">n/a</span>}</td>
                  <td className="whitespace-nowrap px-4 py-3.25 text-right">
                    {c.mint_revenue_eth > 0 ? (
                      <><div className="font-bold text-ink">{eth(c.mint_revenue_eth)}</div>
                        <div className="font-mono text-[10px] text-muted">{compactUsd(c.mint_revenue_usd)}</div></>
                    ) : <span className="text-muted">n/a</span>}
                  </td>
                  <td className="px-4 py-3.25">
                    <div className="flex items-center gap-2.5">
                      <Bar value={c.secondary_volume_eth} max={secMax} min={1.5} />
                      <span className="min-w-20 whitespace-nowrap text-right text-dim2">
                        {c.secondary_volume_eth > 0 ? (
                          <><div>{eth(c.secondary_volume_eth)}</div>
                            {c.secondary_volume_usd != null &&
                              <div className="font-mono text-[10px] text-muted">{compactUsd(c.secondary_volume_usd)}</div>}</>
                        ) : <span className="text-muted">n/a</span>}</span>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3.25 text-right text-hypeB">
                    {c.royalty_eth > 0 ? (
                      <><div>{eth(c.royalty_eth)}</div>
                        {c.royalty_usd != null &&
                          <div className="font-mono text-[10px] text-muted">{compactUsd(c.royalty_usd)}</div>}</>
                    ) : <span className="text-muted">n/a</span>}</td>
                  <td className="whitespace-nowrap px-4 py-3.25 text-right text-dim2">{floorLabel(c)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroller>
      </Container>
    </div>
  );
}
