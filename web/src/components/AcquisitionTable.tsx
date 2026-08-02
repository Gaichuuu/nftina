import { useState } from "react";
import type { Findings, TopItem } from "@/data/schemas";
import { eth, usd, compactUsd, pct, placeholderGradient, osAssetUrl, cdnResized } from "@/lib/format";
import Bar from "./Bar";
import TableScroller from "./TableScroller";

type BlueChip = Findings["acquisitions"]["by_collection"][number];

const DISPLAY_NAMES: Record<string, string> = {
  CRYPTOPUNKS: "CryptoPunks",
  BoredApeYachtClub: "Bored Ape Yacht Club",
};
const displayName = (name: string) => DISPLAY_NAMES[name] ?? name;

function CollThumb({ b, size }: { b: BlueChip; size: string }) {
  const [failed, setFailed] = useState(false);
  const show = b.image && !failed;
  return show ? (
    <img src={cdnResized(b.image!, 64)} alt={displayName(b.name)} loading="lazy" onError={() => setFailed(true)}
         className={`${size} shrink-0 rounded-[6px] object-cover`} />
  ) : (
    <div className={`${size} shrink-0 rounded-[6px]`} style={{ background: placeholderGradient(b.name) }} />
  );
}

function ExampleTile({ item }: { item: TopItem }) {
  const [failed, setFailed] = useState(false);
  const show = item.image && !failed;
  const href = item.contract ? osAssetUrl(item.contract, item.token_id) : undefined;
  const inner = (
    <div className="overflow-hidden rounded-sm border border-line bg-panel
                    transition-colors hover:border-hypeB/40">
      <div className="aspect-square w-full">
        {show ? (
          <img src={cdnResized(item.image!, 480)} alt={`${displayName(item.name)} #${item.token_id}`} loading="lazy"
               onError={() => setFailed(true)} className="h-full w-full object-cover" />
        ) : (
          <div className="h-full w-full" style={{ background: placeholderGradient(item.name + item.token_id) }} />
        )}
      </div>
      <div className="p-1.5">
        <div className="truncate text-[11px] font-bold text-ink">{displayName(item.name)} #{item.token_id}</div>
        <div className="font-mono text-[10px] tabular-nums text-dim">{eth(item.eth)} / {usd(item.usd)}</div>
      </div>
    </div>
  );
  return href ? (
    <a href={href} target="_blank" rel="noopener noreferrer" title="View on OpenSea"
       className="no-underline">{inner}</a>
  ) : inner;
}

export default function AcquisitionTable({ acq }: { acq: Findings["acquisitions"] }) {
  const underwater = acq.underwater ?? acq.by_collection.filter((b) => b.loss_pct != null).slice(0, 5);
  const examples = acq.top_examples ?? [];
  const rows = acq.by_collection.slice(0, 8);
  const usdMax = Math.max(1, ...rows.map((b) => b.usd));
  return (
    <div>
      {underwater.length > 0 && (
        <div className={`mb-3 mt-1 grid gap-2 ${examples.length > 0 ? "grid-cols-1 sm:grid-cols-5" : "grid-cols-2 sm:grid-cols-5"}`}>
          {underwater.map((b, i) => {
            const ex = examples.find((e) => e.contract === b.contract) ?? examples[i];
            const stat = (
              <div className="flex flex-col justify-center rounded-sm border border-loss/35 bg-panel px-2.5 py-3.5 text-center">
                <div className="text-[26px] font-extrabold leading-none tabular-nums text-loss">{pct(b.loss_pct!)}</div>
                <div className="mt-1 truncate text-[11px] font-bold text-ink">{displayName(b.name)}</div>
                <div className="font-mono text-[9.5px] tabular-nums text-muted">
                  paid ~{eth(b.avg_paid_eth!)}{" "}
                  <span className="max-sm:block">→ floor ~{eth(b.floor_eth!)}</span></div>
              </div>
            );
            return ex ? (
              <div key={b.contract} className="grid grid-cols-2 items-stretch gap-2 sm:flex sm:flex-col">
                <div className="sm:order-last"><ExampleTile item={ex} /></div>
                {stat}
              </div>
            ) : (
              <div key={b.contract}>{stat}</div>
            );
          })}
        </div>
      )}
      {underwater.length === 0 && examples.length > 0 && (
        <div className="mb-3 mt-1 grid grid-cols-2 gap-2 sm:grid-cols-5">
          {examples.map((item) => (
            <ExampleTile key={`${item.contract}_${item.token_id}`} item={item} />
          ))}
        </div>
      )}
      <TableScroller className="mt-3.5">
        <table className="w-full min-w-135 text-[12.5px] tabular-nums">
          <thead className="bg-panel2 font-mono text-[10px] font-semibold uppercase tracking-widest text-muted">
            <tr><th className="px-4 py-3 text-left">COLLECTION</th><th className="px-4 py-3 text-right">BOUGHT</th>
              <th className="px-4 py-3 text-right">HOLDS</th>
              <th className="w-[34%] px-4 py-3 text-left">USD</th><th className="px-4 py-3 text-right">ETH</th></tr>
          </thead>
          <tbody>
            {rows.map((b) => (
              <tr key={b.contract}
                  className="border-t border-line align-middle transition-colors hover:bg-hover">
                <td className="px-4 py-3.25">
                  <div className="flex items-center gap-2.5">
                    <CollThumb b={b} size="h-7 w-7" />
                    <span className="min-w-0 truncate">{displayName(b.name)}</span>
                  </div>
                </td>
                <td className="px-4 py-3.25 text-right text-dim">{b.purchases}</td>
                <td className="px-4 py-3.25 text-right">
                  {b.held_now == null ? <span className="text-muted">n/a</span>
                    : <span className={b.held_now === 0 ? "text-muted" : "text-gain"}>{b.held_now}</span>}
                </td>
                <td className="px-4 py-3.25">
                  <div className="flex items-center gap-2">
                    <Bar value={b.usd} max={usdMax} />
                    <span className="min-w-14 whitespace-nowrap text-right text-dim">{usd(b.usd)}</span>
                  </div>
                </td>
                <td className="px-4 py-3.25 text-right whitespace-nowrap">{eth(b.eth)}</td>
              </tr>
            ))}
            <tr className="border-t border-line bg-total text-muted">
              <td className="px-4 py-3.25">…{acq.total_purchases} buys total</td>
              <td className="px-4 py-3.25"></td><td className="px-4 py-3.25"></td>
              <td className="px-4 py-3.25 text-right whitespace-nowrap">{compactUsd(acq.total_usd)}</td>
              <td className="px-4 py-3.25 text-right whitespace-nowrap">{eth(acq.total_eth)}</td>
            </tr>
          </tbody>
        </table>
      </TableScroller>
    </div>
  );
}
