import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { collectionBySlug, contentFor } from "@/data/bundled";
import { eth, compactUsd, shortAddr, cdnResized } from "@/lib/format";
import Container from "@/components/Container";
import { StatCell, StatStrip } from "@/components/StatCell";
import Tabs from "@/components/Tabs";
import HoldersTable from "@/components/HoldersTable";
import TokenGrid from "@/components/TokenGrid";
import Sandbox3DGrid from "@/components/Sandbox3DGrid";
import CollectionContentView from "@/components/CollectionContent";
import { tabsFor, showFilterFor, isShowcase3d } from "@/data/collectionUiConfig";

export default function CollectionPage() {
  const { slug = "" } = useParams();
  const c = collectionBySlug(slug);
  const [tab, setTab] = useState("Tokens");
  if (!c) return <div className="p-16 text-center text-dim">No such collection.</div>;
  const content = contentFor(slug);
  const TABS = tabsFor(slug, content.utility.length > 0 || !!content.utility_intro);
  const special = isShowcase3d(slug);
  return (
    <div>
      {/* banner */}
      <div className="relative h-40 overflow-hidden sm:h-55"
           style={{ WebkitMaskImage: "linear-gradient(to bottom, #000 55%, transparent 100%)",
                    maskImage: "linear-gradient(to bottom, #000 55%, transparent 100%)" }}>
        {c.video ? (
          <>
            <video src={c.video} poster={c.image ?? undefined} autoPlay loop muted playsInline
                   preload="metadata" aria-hidden="true"
                   className="absolute inset-0 h-full w-full object-cover" />
            <div className="absolute inset-0"
                 style={{ background: "linear-gradient(180deg,rgba(59,29,110,.55),rgba(12,9,18,.85))" }} />
          </>
        ) : (
          <div className="absolute inset-0 bg-cover bg-center"
               style={{ background: c.image
                 ? `linear-gradient(180deg,rgba(59,29,110,.55),rgba(12,9,18,.85)), url(${cdnResized(c.image, 1600)}) center/cover`
                 : "linear-gradient(180deg,#3b1d6e,#0e2a63,#160a24)" }} />
        )}
      </div>
      <Container>
        {/* title block */}
        <div className="relative -mt-15">
          <nav className="mb-2.5 font-mono text-[11px] text-muted">
            <Link to="/" className="text-hypeB no-underline hover:underline">Home</Link>
            <span className="px-1.5">/</span>
            <Link to="/collections" className="text-dim2 no-underline hover:underline">Collections</Link>
            <span className="px-1.5">/</span>
            <span className="text-dim">{c.name}</span>
          </nav>
          <h1 className="text-[30px] font-black tracking-[-0.03em] sm:text-[40px]">{c.name}</h1>
          <div className="mt-2 font-mono text-[12px] text-muted">
            {shortAddr(c.contract)} · {c.standard} · floor {eth(c.floor_eth)}
          </div>
        </div>

        {special && content.banner && (
          <div className="mt-4 rounded-md border border-line bg-panel/50 p-4 text-[12px] leading-relaxed text-dim">
            {content.banner}
          </div>
        )}

        {/* stat row */}
        <div className="mt-7">
          <StatStrip className="grid-cols-2 sm:grid-cols-5 max-sm:[&>*:last-child]:col-span-2">
            <StatCell big={c.total_mints.toLocaleString()} label="Mints" />
            {(() => {
              const off = content.off_chain_basis?.unit_cost_usd;
              const avgEth = c.total_mints > 0 ? c.mint_revenue_eth / c.total_mints : 0;
              const avgUsd = c.total_mints > 0 ? c.mint_revenue_usd / c.total_mints : 0;
              const sold = content.primary_sale;
              return (
                <StatCell
                          big={off ? `$${off}` : avgEth > 0 ? eth(avgEth) : sold ? sold.label : "Free"}
                          sub={off ? "off-chain box"
                               : avgEth > 0 ? compactUsd(avgUsd) : sold?.sub}
                          label="Mint price" />
              );
            })()}
            <StatCell tone="gain" big={eth(c.mint_revenue_eth)}
                      sub={c.mint_revenue_usd > 0 ? compactUsd(c.mint_revenue_usd) : undefined}
                      label="→ Mint revenue" />
            <StatCell big={eth(c.secondary_volume_eth)}
                      sub={c.secondary_volume_usd != null ? compactUsd(c.secondary_volume_usd) : undefined}
                      label="Secondary vol" />
            <StatCell tone="hype" big={eth(c.royalty_eth)}
                      sub={c.royalty_usd != null ? compactUsd(c.royalty_usd) : undefined}
                      label="→ MetaZoo royalties" />
          </StatStrip>
        </div>

        <div className="mt-7">
          <Tabs tabs={TABS} active={tab} onChange={setTab} />
        </div>
        {tab === "Holders" && <HoldersTable slug={slug} />}
        {tab === "Tokens" && (special ? <Sandbox3DGrid />
          : <TokenGrid slug={slug} contract={c.contract} showFilter={showFilterFor(slug)} />)}
        {tab === "Overview" && <CollectionContentView mode="Overview" content={content} slug={slug} />}
        {tab === "Utility" && <CollectionContentView mode="Utility" content={content} />}
      </Container>
    </div>
  );
}
