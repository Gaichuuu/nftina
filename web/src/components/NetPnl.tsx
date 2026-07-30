import { eth, usd } from "@/lib/format";

export default function NetPnl({ ethv, usdv }: { ethv: number; usdv: number }) {
  return (
    <div className="text-right">
      <div className={`font-bold ${ethv < 0 ? "text-loss" : "text-gain"}`}>
        {ethv < 0 ? "−" : "+"}{eth(Math.abs(ethv))}
      </div>
      <div className={`text-[11px] opacity-80 ${usdv < 0 ? "text-loss" : "text-gain"}`}>
        {usdv < 0 ? "−" : "+"}{usd(Math.abs(usdv))}
      </div>
    </div>
  );
}
