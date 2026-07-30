import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { summary, findings, collections, sandbox3d, SLUGS } from "@/data/bundled";
import { eth, compactUsd, compactUsdDown } from "@/lib/format";
import Container from "@/components/Container";
import { StatCell, StatStrip } from "@/components/StatCell";
import WalletLookup from "@/components/WalletLookup";
// import VolumeChart from "@/components/VolumeChart";
import CollectionTile from "@/components/CollectionTile";
import ModelViewer from "@/components/ModelViewer";

const DEFAULT_HERO = sandbox3d.find((a) => a.name.toLowerCase().includes("space penguins")) ?? sandbox3d[0];

export default function HomePage() {
  const [hero, setHero] = useState(DEFAULT_HERO);
  useEffect(() => {
    if (sandbox3d.length) setHero(sandbox3d[Math.floor(Math.random() * sandbox3d.length)]);
  }, []);

  return (
    <div>
      {/* HERO */}
      <section className="relative overflow-hidden"
               style={{ background: "radial-gradient(90% 120% at 78% 20%, #241238, #0c0912 64%)" }}>
        {hero && (
          <div className="pointer-events-none absolute z-1 hidden lg:block"
               style={{ top: -70, right: 10, width: 760, height: 640 }}>
            <div className="absolute inset-0"
                 style={{ background: "radial-gradient(50% 45% at 55% 42%, rgba(139,233,255,.16), transparent 70%)",
                          animation: "glowpulse 7s ease-in-out infinite" }} />
            <div className="pointer-events-auto h-full w-full">
              <ModelViewer src={hero.model} poster={hero.image ?? undefined} alt={hero.name} randomAnimation />
            </div>
          </div>
        )}
        <Container className="relative z-5 py-13 pt-12">
          <div className="max-w-170">
            <h1 className="mt-5 text-[44px] font-black leading-[0.97] tracking-[-0.035em] text-ink sm:text-[72px]">
              MetaZoo raised <span className="text-hypeB">{compactUsd(summary.total_mint_revenue_usd)}</span>.
            </h1>
            <h1 className="mt-1.5 text-[44px] font-black leading-[0.97] tracking-[-0.035em] text-loss sm:text-[72px]">
              Holders lost {compactUsdDown(summary.total_loss_usd)}.
            </h1>
            <p className="mt-6 max-w-120 text-[16px] leading-[1.55] text-dim2">
              {Math.round(summary.total_loss_eth).toLocaleString()} Ξ vanished across {collections.length} collections
              and {summary.total_wallets.toLocaleString()} wallets.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4.5">
              <Link to="/where-did-the-money-go"
                    className="hype-btn rounded-full px-7.5 py-3.5 text-[15px] no-underline">
                See the findings →
              </Link>
              {/* <span className="max-w-60 font-mono text-[11px] leading-normal text-muted">
                USD valued when each amount moved.
              </span> */}
            </div>
          </div>
        </Container>
        {/* STATS */}
        <div className="relative z-5">
          <Container className="py-0">
            <StatStrip cols={4} className="grid-cols-2 sm:grid-cols-4">
              <StatCell numClass="text-[24px]" tone="hype" big={eth(findings.legs.aoki_eth)}
                        sub={compactUsd(findings.legs.aoki_usd)} label="→ Funds sent to Aoki" />
              <StatCell numClass="text-[24px]" big={eth(findings.legs.royalties_eth)}
                        sub={compactUsd(findings.legs.royalties_usd)} label="royalties taken by MetaZoo" />
              <StatCell numClass="text-[24px]" tone="gain" big={eth(findings.flippers.total_gains_eth)}
                        sub={compactUsd(findings.flippers.total_gains_usd)}
                        label="flippers selling the top" />
              <StatCell numClass="text-[24px]" tone="loss"
                        big={summary.wallets_net_loss.toLocaleString()}
                        label="wallets net underwater" />
            </StatStrip>
          </Container>
        </div>
      </section>

      {/* WALLET LOOKUP */}
      <Container className="pb-2 pt-12"><WalletLookup />
      </Container>

      {/* VOLUME CHART - removed for now */}
      {/* <Container className="pb-2 pt-16">
        <div className="eyebrow tracking-[3px] text-hypeB">The arc · monthly secondary volume</div>
        <div className="mb-4.5 mt-3 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-[30px] font-black tracking-tight">Two months of mania, then silence.</h2>
          {(() => {
            const p = volume.ecosystem.reduce((a, b) => (b.eth > a.eth ? b : a), volume.ecosystem[0]);
            return <span className="font-mono text-[12px] text-muted">
              peak {eth(p.eth)} · {compactUsd(p.usd)} · Jan 2022
            </span>;
          })()}
        </div>
        <VolumeChart points={volume.ecosystem} />
      </Container> */}

      {/* COLLECTIONS */}
      <Container className="pb-12 pt-8">
        <h2 className="mb-5.5 mt-3 text-[30px] font-black tracking-tight">MetaZoo NFT Collections</h2>
        <div className="grid grid-cols-2 gap-3.5 sm:grid-cols-3 lg:grid-cols-5">
          {SLUGS.map((s) => {
            const c = collections.find((x) => x.collection === s);
            return c ? <CollectionTile key={s} c={c} /> : null;
          })}
        </div>
      </Container>
    </div>
  );
}
