import { Link } from "react-router-dom";
import type { Collection } from "@/data/schemas";
import { hideLossPctFor } from "@/data/collectionUiConfig";
import { pct, eth, tileGradient, cdnResized } from "@/lib/format";
import LoopMedia from "./LoopMedia";

export default function CollectionTile({ c }: { c: Collection }) {
  const lossPct = hideLossPctFor(c.collection) ? null : (c.loss_pct ?? null);
  return (
    <Link to={`/collections/${c.collection}`}
          className="block rounded-md border border-line bg-panel p-2.5 no-underline
                     transition-[border-color,transform,background] duration-[.18s]
                     hover:-translate-y-0.75 hover:border-[rgba(139,233,255,.5)] hover:bg-[#1a1326]">
      <div className="aspect-square w-full overflow-hidden rounded-sm"
           style={{ background: tileGradient }}>
        <LoopMedia image={c.image && cdnResized(c.image, 480)} video={c.video} alt={c.name}
                   className="h-full w-full object-cover" />
      </div>
      <div className="mt-2.5 truncate text-[12px] font-bold text-ink">{c.name}</div>
      <div className="mt-0.5 flex items-baseline justify-between gap-1 font-mono text-[11px] tabular-nums">
        <span className="truncate text-dim">floor {eth(c.floor_eth)}</span>
        {lossPct != null && (
          <span className={lossPct < 0 ? "shrink-0 text-loss" : "shrink-0 text-gain"}>{pct(lossPct)}</span>
        )}
      </div>
    </Link>
  );
}
