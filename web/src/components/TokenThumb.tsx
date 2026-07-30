import { useState } from "react";
import type { TokenRow } from "@/data/schemas";
import { usd, osAssetUrl, placeholderGradient } from "@/lib/format";

export default function TokenThumb({ t, contract }:
  { t: TokenRow; contract?: string }) {
  const [failed, setFailed] = useState(false);
  const [videoFailed, setVideoFailed] = useState(false);
  const osContract = t.contract ?? contract;
  const showVideo = t.video && !videoFailed;
  const showImg = t.image && !failed;
  const loss = t.floor_usd - t.last_paid_usd;
  const body = (
    <>
      {showVideo ? (
        <video src={t.video!} poster={t.image ?? undefined} autoPlay loop muted playsInline
               preload="metadata" onError={() => setVideoFailed(true)}
               aria-label={t.name ?? `token ${t.token_id}`}
               className="aspect-square w-full object-cover" />
      ) : showImg ? (
        <img src={t.image!} alt={t.name ?? `token ${t.token_id}`} loading="lazy"
             onError={() => setFailed(true)} className="aspect-square w-full object-cover" />
      ) : (
        <div className="aspect-square w-full" style={{ background: placeholderGradient(t.token_id) }} />
      )}
      <div className="p-2">
        <div className="wrap-break-word text-[11px] font-bold text-ink">{t.name ?? `#${t.token_id}`}</div>
        <div className="flex items-baseline justify-between gap-1">
          <span className="font-mono text-[10px] text-loss">{loss < 0 ? usd(loss) : " "}</span>
          {t.supply != null && (
            <span className="shrink-0 font-mono text-[9px] text-muted">{t.supply.toLocaleString()} minted</span>
          )}
        </div>
      </div>
    </>
  );
  const cls = "block overflow-hidden rounded-md border border-line bg-panel no-underline transition-colors hover:border-hypeB/40";
  return osContract ? (
    <a href={osAssetUrl(osContract, t.token_id)}
       target="_blank" rel="noopener noreferrer" className={cls}>{body}</a>
  ) : (
    <div className={cls}>{body}</div>
  );
}
