import { Link } from "react-router-dom";
import { summary, findings, collections, SLUGS } from "@/data/bundled";
import { eth, compactUsd, compactUsdDown } from "@/lib/format";
import Container from "@/components/Container";
import { StatCell, StatStrip } from "@/components/StatCell";
import WalletLookup from "@/components/WalletLookup";
// import VolumeChart from "@/components/VolumeChart";
import CollectionTile from "@/components/CollectionTile";
import RandomModel from "@/components/RandomModel";
import { DEFAULT_MODEL as DEFAULT_HERO } from "@/lib/heroModel";

export default function HomePage() {
  return (
    <div>
      {/* HERO */}
      <section className="relative overflow-hidden"
               style={{ background: "radial-gradient(90% 120% at 78% 20%, #241238, #0c0912 64%)" }}>
        <Container className="relative z-5 pt-12">
          <div className="anim-rise max-w-170">
            <h1 className="text-balance text-[44px] font-black leading-[0.97] tracking-[-0.035em] text-ink sm:text-[72px]">
              MetaZoo raised <span className="text-hypeB">{compactUsd(summary.total_mint_revenue_usd)}</span>.
            </h1>
            <h1 className="mt-1.5 text-balance text-[44px] font-black leading-[0.97] tracking-[-0.035em] text-loss sm:text-[72px]">
              Holders lost {compactUsdDown(summary.total_loss_usd)}.
            </h1>
            <p className="mt-6 max-w-120 text-pretty text-[16px] leading-[1.55] text-dim2">
              {Math.round(summary.total_loss_eth).toLocaleString()} Ξ vanished across {collections.length} collections
              and {summary.total_wallets.toLocaleString()} wallets.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-4.5">
              <Link to="/where-did-the-money-go"
                    className="hype-btn px-7.5 py-3.5 text-[15px] no-underline
                               hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(255,92,240,.28)]">
                See the findings →
              </Link>
            </div>
          </div>
        </Container>
        {/* HERO MODEL */}
        {DEFAULT_HERO && (
          <div className="pointer-events-none relative z-1 mx-auto mt-4 h-65 w-full max-w-90
                          max-sm:mt-0 max-sm:h-50
                          lg:absolute lg:right-2.5 lg:-top-17.5 lg:mx-0 lg:mt-0 lg:h-160 lg:w-190 lg:max-w-none">
            <div className="absolute inset-0"
                 style={{ background: "radial-gradient(50% 45% at 55% 42%, rgba(139,233,255,.16), transparent 70%)",
                          animation: "glowpulse 7s ease-in-out infinite" }} />
            <div className="pointer-events-auto h-full w-full">
              <RandomModel />
            </div>
          </div>
        )}
        {/* STATS */}
        <div className="relative z-5 pb-14">
          <Container className="pt-11">
            <StatStrip className="anim-rise-stagger grid-cols-2 sm:grid-cols-4">
              <StatCell bg="bg-bg" tone="hype" big={eth(findings.legs.aoki_eth)}
                        sub={compactUsd(findings.legs.aoki_usd)} label="→ Sent to Aoki" />
              <StatCell bg="bg-bg" big={eth(findings.legs.royalties_eth)}
                        sub={compactUsd(findings.legs.royalties_usd)} label="→ MetaZoo Royalties" />
              <StatCell bg="bg-bg" tone="gain" big={eth(findings.flippers.total_gains_eth)}
                        sub={compactUsd(findings.flippers.total_gains_usd)}
                        label="→ Taken by flippers" />
              <StatCell bg="bg-bg" tone="loss"
                        big={summary.wallets_net_loss.toLocaleString()}
                        sub={`of ${summary.total_wallets.toLocaleString()}`}
                        label="Wallets net underwater" />
            </StatStrip>
          </Container>
        </div>
      </section>

      {/* WALLET LOOKUP */}
      <Container className="pb-2 pt-0"><WalletLookup />
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
        <div className="mt-3">
          <h2 className="section-h2 mb-5.5">MetaZoo NFT collections</h2>
        </div>
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
