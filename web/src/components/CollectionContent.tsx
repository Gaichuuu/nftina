import { useState } from "react";
import type { CollectionContent, UtilityProduct } from "@/data/schemas";
import { usd, ethUsd, placeholderGradient, cdnResized } from "@/lib/format";

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
              <span className="absolute left-0 text-hypeB">·</span>{raw.slice(2)}
            </div>
          );
        return <p key={i} className="text-[15px] leading-[1.7] text-dim2">{raw}</p>;
      })}
    </div>
  );
}

function ProductTile({ p }: { p: UtilityProduct }) {
  const [failed, setFailed] = useState(false);
  const show = p.image && !failed;
  return (
    <div className="overflow-hidden rounded-md border border-line bg-panel">
      <div className="flex h-40 w-full items-center justify-center bg-bg">
        {show ? (
          <img src={cdnResized(p.image!, 400)} alt={p.name} loading="lazy" onError={() => setFailed(true)}
               className="max-h-full max-w-full object-contain" />
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

export default function CollectionContentView(
  { mode, content }: { mode: "Overview" | "Utility"; content: CollectionContent },
) {
  if (mode === "Overview") {
    if (!content.overview.length)
      return <div className="py-16 text-center font-mono text-[12px] text-muted">no overview yet.</div>;
    const img = content.overview_image;
    return (
      <div className="py-7">
        <div className={img ? "flex flex-col gap-8 lg:flex-row lg:items-start" : ""}>
          <div className={img ? "min-w-0 lg:flex-1" : "max-w-180"}>
            <OverviewBlocks blocks={content.overview} />
          </div>
          {img && (
            <figure className="order-first lg:order-none lg:sticky lg:top-6 lg:w-[38%] lg:shrink-0">
              <img src={cdnResized(img, 1000)} alt={content.overview_image_caption ?? "Collection art"} loading="lazy"
                   className="w-full rounded-md border border-line" />
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
  if (!products.length)
    return <div className="py-16 text-center font-mono text-[12px] text-muted">no utility items yet.</div>;
  return (
    <div className="grid grid-cols-2 gap-4 py-7 sm:grid-cols-3 lg:grid-cols-5">
      {products.map((p) => <ProductTile key={p.id} p={p} />)}
    </div>
  );
}
