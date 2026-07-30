import { Link } from "react-router-dom";
import type { Collection } from "@/data/schemas";
import { pct, eth } from "@/lib/format";
import LoopMedia from "./LoopMedia";

const HIDE_LOSS_PCT = new Set(["valentines", "wilderness"]);

export default function CollectionTile({ c }: { c: Collection }) {
  const lossPct = HIDE_LOSS_PCT.has(c.collection) ? null : (c.loss_pct ?? null);
  return (
    <Link to={`/collections/${c.collection}`}
          className="block rounded-md border border-line bg-panel p-2.5 no-underline transition-colors hover:border-hypeB/50">
      <div className="aspect-square w-full overflow-hidden rounded-lg"
           style={{ background: "radial-gradient(circle at 40% 30%,#3a2358,#160a24)" }}>
        <LoopMedia image={c.image} video={c.video} alt={c.name}
                   className="h-full w-full object-cover" />
      </div>
      <div className="mt-2.5 text-[12px] font-bold text-ink">{c.name}</div>
      <div className="mt-0.5 flex items-baseline justify-between gap-1 font-mono text-[11px]">
        <span className="truncate text-dim">floor {eth(c.floor_eth)}</span>
        {lossPct != null && (
          <span className={lossPct < 0 ? "shrink-0 text-loss" : "shrink-0 text-gain"}>{pct(lossPct)}</span>
        )}
      </div>
    </Link>
  );
}
