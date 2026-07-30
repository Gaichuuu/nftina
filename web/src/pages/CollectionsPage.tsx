import { useNavigate } from "react-router-dom";
import { collections, summary } from "@/data/bundled";
import type { Collection } from "@/data/schemas";
import LoopMedia from "@/components/LoopMedia";
import { eth, compactUsd } from "@/lib/format";
import Container from "@/components/Container";
import { StatCell, StatStrip } from "@/components/StatCell";

function Thumb({ c }: { c: Collection }) {
  return (
    <div className="h-11 w-11 shrink-0 overflow-hidden rounded-md"
         style={{ background: "radial-gradient(circle at 40% 30%,#3a2358,#160a24)" }}>
      <LoopMedia image={c.image} video={c.video} alt={c.name}
                 className="h-full w-full object-cover" />
    </div>
  );
}

function floorLabel(c: Collection): string {
  if (c.collection === "sandbox") return "off-chain";
  return c.floor_eth > 0 ? `${c.floor_eth} Ξ` : "n/a";
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
          <h1 className="mt-4 text-[40px] font-black leading-none tracking-[-0.03em] text-ink sm:text-[52px]">
            MetaZoo NFT Collections
          </h1>
          <div className="mt-8.5">
            <StatStrip cols={4} className="grid-cols-2 sm:grid-cols-4">
              <StatCell numClass="text-[24px]" big={totalMints.toLocaleString()}
                        label="Total mints" />
              <StatCell numClass="text-[24px]" big={eth(summary.total_mint_revenue_eth)}
                        sub={compactUsd(summary.total_mint_revenue_usd)} label="Mint revenue" />
              <StatCell numClass="text-[24px]" big={eth(summary.secondary_volume_eth)}
                        sub={compactUsd(ranked.reduce((s, c) => s + (c.secondary_volume_usd ?? 0), 0))}
                        label="Secondary volume" />
              <StatCell numClass="text-[24px]" tone="hype"
                        big={eth(summary.royalties_to_metazoo_eth)}
                        sub={compactUsd(ranked.reduce((s, c) => s + (c.royalty_usd ?? 0), 0))}
                        label="→ MetaZoo royalties" />
            </StatStrip>
          </div>
        </Container>
      </section>

      {/* ranked table */}
      <Container className="pb-12 pt-8">
        <div className="overflow-x-auto rounded-lg border border-line">
          <table className="w-full text-[13px]">
            <thead className="bg-panel2 font-mono text-[10px] tracking-[1px] text-muted">
              <tr>
                <th className="px-4.5 py-3.5 text-left font-semibold">COLLECTION</th>
                <th className="px-4.5 py-3.5 text-right font-semibold">MINTS</th>
                <th className="px-4.5 py-3.5 text-right font-semibold">MINT REVENUE</th>
                <th className="w-[26%] px-4.5 py-3.5 text-left font-semibold">SECONDARY VOLUME</th>
                <th className="px-4.5 py-3.5 text-right font-semibold">ROYALTIES</th>
                <th className="px-4.5 py-3.5 text-right font-semibold">FLOOR</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((c) => (
                <tr key={c.collection} onClick={() => nav(`/collections/${c.collection}`)}
                    className="cursor-pointer border-t border-line hover:bg-panel/50">
                  <td className="px-4.5 py-3.5">
                    <div className="flex items-center gap-3.5">
                      <Thumb c={c} />
                      <div>
                        <div className="text-[14px] font-bold text-ink">{c.name}</div>
                        <div className="mt-0.5 font-mono text-[10px] text-muted">{c.standard}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4.5 py-3.5 text-right text-dim2">
                    {c.total_mints > 0 ? c.total_mints.toLocaleString() : <span className="text-muted">n/a</span>}</td>
                  <td className="px-4.5 py-3.5 text-right">
                    {c.mint_revenue_eth > 0 ? (
                      <><div className="font-bold text-ink">{eth(c.mint_revenue_eth)}</div>
                        <div className="font-mono text-[10px] text-muted">{compactUsd(c.mint_revenue_usd)}</div></>
                    ) : <span className="text-muted">n/a</span>}
                  </td>
                  <td className="px-4.5 py-3.5">
                    <div className="flex items-center gap-2.5">
                      <div className="h-1.75 flex-1 overflow-hidden rounded-[4px]" style={{ background: "#1c1526" }}>
                        <span className="block h-full"
                              style={{ width: `${c.secondary_volume_eth > 0 ? Math.max(1.5, (c.secondary_volume_eth / secMax) * 100) : 0}%`,
                                       background: "linear-gradient(90deg,#ff5cf0,#8be9ff)" }} />
                      </div>
                      <span className="min-w-18.5 text-right text-dim2">
                        {c.secondary_volume_eth > 0 ? (
                          <><div>{eth(c.secondary_volume_eth)}</div>
                            {c.secondary_volume_usd != null &&
                              <div className="font-mono text-[10px] text-muted">{compactUsd(c.secondary_volume_usd)}</div>}</>
                        ) : <span className="text-muted">n/a</span>}</span>
                    </div>
                  </td>
                  <td className="px-4.5 py-3.5 text-right text-hypeB">
                    {c.royalty_eth > 0 ? (
                      <><div>{eth(c.royalty_eth)}</div>
                        {c.royalty_usd != null &&
                          <div className="font-mono text-[10px] text-muted">{compactUsd(c.royalty_usd)}</div>}</>
                    ) : <span className="text-muted">n/a</span>}</td>
                  <td className="px-4.5 py-3.5 text-right text-dim2">{floorLabel(c)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Container>
    </div>
  );
}
