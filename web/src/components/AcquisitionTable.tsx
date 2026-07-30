import { useState } from "react";
import type { Findings, TopItem } from "@/data/schemas";
import { eth, usd, compactUsd, pct, placeholderGradient, osAssetUrl } from "@/lib/format";

type BlueChip = Findings["acquisitions"]["by_collection"][number];

function CollThumb({ b, size }: { b: BlueChip; size: string }) {
  const [failed, setFailed] = useState(false);
  const show = b.image && !failed;
  return show ? (
    <img src={b.image!} alt={b.name} loading="lazy" onError={() => setFailed(true)}
         className={`${size} shrink-0 rounded-sm object-cover`} />
  ) : (
    <div className={`${size} shrink-0 rounded-sm`} style={{ background: placeholderGradient(b.name) }} />
  );
}

function ExampleTile({ item }: { item: TopItem }) {
  const [failed, setFailed] = useState(false);
  const show = item.image && !failed;
  const href = item.contract ? osAssetUrl(item.contract, item.token_id) : undefined;
  const inner = (
    <div className="overflow-hidden rounded-sm border border-line bg-panel transition-colors hover:border-hypeA">
      <div className="aspect-square w-full">
        {show ? (
          <img src={item.image!} alt={`${item.name} #${item.token_id}`} loading="lazy"
               onError={() => setFailed(true)} className="h-full w-full object-cover" />
        ) : (
          <div className="h-full w-full" style={{ background: placeholderGradient(item.name + item.token_id) }} />
        )}
      </div>
      <div className="p-1.5">
        <div className="truncate text-[10px] font-bold text-ink">{item.name} #{item.token_id}</div>
        <div className="text-[9px] text-dim">{eth(item.eth)} / {usd(item.usd)}</div>
      </div>
    </div>
  );
  return href ? (
    <a href={href} target="_blank" rel="noopener noreferrer" title="View on OpenSea">{inner}</a>
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
        <div className="mb-3">
          {/* stat tiles */}
          <div className="mt-1 grid grid-cols-2 gap-2 sm:grid-cols-5">
            {underwater.map((b) => (
              <div key={b.contract}
                   className="rounded-sm border border-loss/40 bg-panel p-2 text-center">
                <div className="text-[26px] font-extrabold leading-none text-loss">{pct(b.loss_pct!)}</div>
                <div className="mt-1 truncate text-[10px] font-bold text-ink">{b.name}</div>
                <div className="text-[9px] text-dim">
                  paid ~{eth(b.avg_paid_eth!)} → floor ~{eth(b.floor_eth!)}</div>
              </div>
            ))}
          </div>
          {/* aligned collection-image tiles */}
        </div>
      )}
      {examples.length > 0 && (
        <div className="mb-3">
          <div className="mt-1 grid grid-cols-2 gap-2 sm:grid-cols-5">
            {examples.map((item) => (
              <ExampleTile key={`${item.contract}_${item.token_id}`} item={item} />
            ))}
          </div>
        </div>
      )}
      <div className="mt-3 overflow-x-auto rounded-sm border border-line">
        <table className="w-full text-[11.5px]">
          <thead className="bg-panel2 font-mono text-[10px] text-muted">
            <tr><th className="p-2 text-left">COLLECTION</th><th className="p-2 text-right">BOUGHT</th>
              <th className="p-2 pr-6 text-right">HOLDS</th>
              <th className="w-[34%] p-2 pl-6 text-left">USD</th><th className="p-2 text-right">ETH</th></tr>
          </thead>
          <tbody>
            {rows.map((b) => (
              <tr key={b.contract} className="border-t border-line align-middle">
                <td className="p-2">
                  <div className="flex items-center gap-2.5">
                    <CollThumb b={b} size="h-7 w-7" />
                    <span className="min-w-0 truncate">{b.name}</span>
                  </div>
                </td>
                <td className="p-2 text-right text-dim">{b.purchases}</td>
                <td className="p-2 pr-6 text-right">
                  {b.held_now == null ? <span className="text-muted">n/a</span>
                    : <span className={b.held_now === 0 ? "text-muted" : "text-gain"}>{b.held_now}</span>}
                </td>
                <td className="p-2 pl-6">
                  <div className="flex items-center gap-2">
                    <div className="h-1.75 flex-1 overflow-hidden rounded-[4px]" style={{ background: "#1c1526" }}>
                      <span className="block h-full"
                            style={{ width: `${Math.max(2, (b.usd / usdMax) * 100)}%`,
                                     background: "linear-gradient(90deg,#ff5cf0,#8be9ff)" }} />
                    </div>
                    <span className="min-w-14 whitespace-nowrap text-right text-dim">{usd(b.usd)}</span>
                  </div>
                </td>
                <td className="p-2 text-right whitespace-nowrap">{eth(b.eth)}</td>
              </tr>
            ))}
            <tr className="border-t border-line text-muted">
              <td className="p-2">…{acq.total_purchases} buys total</td>
              <td className="p-2"></td><td className="p-2"></td>
              <td className="p-2 text-right whitespace-nowrap">{compactUsd(acq.total_usd)}</td>
              <td className="p-2 text-right whitespace-nowrap">{eth(acq.total_eth)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
