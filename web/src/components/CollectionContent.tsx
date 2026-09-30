import { useState } from "react";
import type { CollectionContent, UtilityProduct } from "@/data/schemas";
import { usd, ethUsd, placeholderGradient, cdnResized } from "@/lib/format";
import { isShowcase3d } from "@/data/collectionUiConfig";
import { DEFAULT_MODEL } from "@/lib/heroModel";
import LoopMedia from "./LoopMedia";
import RandomModel from "./RandomModel";

function inline(raw: string) {
  const parts = raw.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  if (parts.length === 1) return raw;
  return parts.map((s, i) =>
    s.startsWith("**") && s.endsWith("**")
      ? <strong key={i} className="font-bold text-ink">{s.slice(2, -2)}</strong>
      : <span key={i}>{s}</span>);
}

function OverviewBlocks({ blocks }: { blocks: string[] }) {
  return (
    <div className="flex flex-col gap-3">
      {blocks.map((raw, i) => {
        if (raw.startsWith("# "))
          return <h3 key={i} className="mt-4 text-[22px] font-black tracking-tight text-ink first:mt-0">{raw.slice(2)}</h3>;
        const bold = /^\*\*(.+)\*\*$/.exec(raw);
        if (bold)
          return <div key={i} className="mt-2 text-[15px] font-bold text-ink">{bold[1]}</div>;
        if (raw.startsWith("- "))
          return (
            <div key={i} className="relative pl-4 text-[15px] leading-[1.6] text-dim2">
              <span className="absolute left-0 text-hypeB">·</span>{inline(raw.slice(2))}
            </div>
          );
        return <p key={i} className="text-[15px] leading-[1.7] text-dim2">{inline(raw)}</p>;
      })}
    </div>
  );
}

function ProductTile({ p }: { p: UtilityProduct }) {
  const [failed, setFailed] = useState(false);
  const show = p.image && !failed;
  return (
    <div className="overflow-hidden rounded-md border border-line bg-panel">
      <div className="h-40 w-full bg-bg">
        {show ? (
          <img src={cdnResized(p.image!, 400)} alt={p.name} loading="lazy" onError={() => setFailed(true)}
               className={`h-full w-full ${p.fit ? "object-contain" : "object-cover"}`} />
        ) : (
          <div className="h-full w-full" style={{ background: placeholderGradient(p.name) }} />
        )}
      </div>
      <div className="p-3">
        <div className="text-[13px] font-bold leading-tight text-ink">{p.name}</div>
        <div className="mt-1 text-[12px] font-bold text-hypeB">
          {p.price_eth != null
            ? ethUsd(p.price_eth, p.price_usd)
            : p.price_usd == null ? "Free to holders" : usd(p.price_usd)}
        </div>
        <p className="mt-1.5 text-[12px] leading-normal text-dim2">{p.note}</p>
      </div>
    </div>
  );
}

function ShowcaseModel() {
  if (!DEFAULT_MODEL) return null;
  return (
    <div className="aspect-square w-full overflow-hidden rounded-md border border-line"
         style={{ background: "radial-gradient(60% 55% at 50% 45%, rgba(139,233,255,.14), transparent 72%)" }}>
      <RandomModel />
    </div>
  );
}

export default function CollectionContentView(
  { mode, content, slug = "" }:
  { mode: "Overview" | "Utility"; content: CollectionContent; slug?: string },
) {
  if (mode === "Overview") {
    if (!content.overview.length)
      return <div className="py-16 text-center font-mono text-[12px] text-muted">no overview yet.</div>;
    const img = content.overview_image;
    const video = content.overview_video;
    const model3d = isShowcase3d(slug);
    const hasFigure = Boolean(img || video || model3d);
    return (
      <div className="py-7">
        <div className={hasFigure ? "flex flex-col gap-8 lg:flex-row lg:items-start" : ""}>
          <div className={hasFigure ? "min-w-0 lg:flex-1" : "max-w-180"}>
            <OverviewBlocks blocks={content.overview} />
          </div>
          {hasFigure && (
            <figure className="order-first lg:order-0 lg:sticky lg:top-22.25 lg:w-[38%] lg:shrink-0">
              {model3d ? <ShowcaseModel /> : video ? (
                <LoopMedia video={video} image={img} className="w-full rounded-md border border-line"
                           alt={content.overview_image_caption ?? "Collection art"} />
              ) : (
                <img src={cdnResized(img!, 1000)} alt={content.overview_image_caption ?? "Collection art"}
                     loading="lazy" className="w-full rounded-md border border-line" />
              )}
              {content.overview_image_caption && (
                <figcaption className="mt-2 font-mono text-[10px] leading-normal text-muted">
                  {content.overview_image_caption}
                </figcaption>
              )}
            </figure>
          )}
        </div>
      </div>
    );
  }
  const products = content.utility;
  if (!products.length && !content.utility_intro)
    return <div className="py-16 text-center font-mono text-[12px] text-muted">no utility items yet.</div>;
  return (
    <div className="py-7">
      {content.utility_intro && (
        <p className="max-w-3xl text-[15px] leading-[1.7] text-dim2">{inline(content.utility_intro)}</p>
      )}
      {products.length > 0 && (
        <div className={`grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5${content.utility_intro ? " mt-6" : ""}`}>
          {products.map((p) => <ProductTile key={p.id} p={p} />)}
        </div>
      )}
    </div>
  );
}
