import type { LedgerRow } from "@/data/schemas";
import { eth, usd, shortAddr } from "@/lib/format";
import Bar from "./Bar";

export default function LedgerTable({ rows }: { rows: LedgerRow[] }) {
  const usdMax = Math.max(1, ...rows.map((r) => Math.abs(r.usd)));
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="w-full min-w-175 text-[12.5px] tabular-nums">
        <thead className="bg-panel2 font-mono text-[10px] font-semibold uppercase tracking-widest text-muted">
          <tr><th className="px-4 py-3 text-left">DATE</th>
            <th className="px-4 py-3 text-right">ETH</th>
            <th className="w-[34%] px-4 py-3 text-left">USD</th>
            <th className="px-4 py-3 text-left">RECIPIENT</th></tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const inKind = r.kind === "aoki_inkind";
            const isAoki = r.kind === "aoki" || r.kind === "aoki_offchain" || inKind;
            const noEth = r.kind === "aoki_offchain" || inKind;
            return (
            <tr key={i} className="border-t border-line transition-colors hover:bg-hover"
                style={isAoki ? { background: "#1a1030" } : undefined}>
              <td className="whitespace-nowrap px-4 py-3.25 font-mono text-[11px] text-dim">{r.date}</td>
              <td className="whitespace-nowrap px-4 py-3.25 text-right font-bold text-ink">
                {noEth ? <span className="font-normal text-muted">{inKind ? "in-kind" : "off-chain"}</span> : eth(r.eth)}</td>
              <td className="px-4 py-3.25">
                <div className="flex items-center gap-2">
                  <Bar value={Math.abs(r.usd)} max={usdMax} />
                  <span className="min-w-15.5 whitespace-nowrap text-right text-muted">{usd(r.usd)}</span>
                </div>
              </td>
              <td className={`max-w-105 px-4 py-3.25 ${isAoki ? "font-bold text-hypeB" : "text-dim"}`}>
                {r.recipient}{r.recipient_addr && <span className="font-mono font-normal text-muted"> {shortAddr(r.recipient_addr)}</span>}
                {r.note && <span className="block text-[11px] font-normal leading-normal text-muted">{r.note}</span>}
              </td>
            </tr>
          );
          })}
        </tbody>
      </table>
    </div>
  );
}
