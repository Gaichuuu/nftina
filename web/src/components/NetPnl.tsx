import { eth, usd } from "@/lib/format";

export default function NetPnl({ ethv, usdv }: { ethv: number; usdv: number }) {
  return (
    <div className="text-right tabular-nums">
      <div className={`text-[12.5px] font-bold ${ethv < 0 ? "text-loss" : "text-gain"}`}>
        {ethv < 0 ? "" : "+"}{eth(ethv)}
      </div>
      <div className={`font-mono text-[11px] opacity-75 ${usdv < 0 ? "text-loss" : "text-gain"}`}>
        {usdv < 0 ? "" : "+"}{usd(usdv)}
      </div>
    </div>
  );
}
