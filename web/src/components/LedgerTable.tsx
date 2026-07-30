import type { LedgerRow } from "@/data/schemas";
import { eth, usd, shortAddr } from "@/lib/format";

export default function LedgerTable({ rows }: { rows: LedgerRow[] }) {
  const usdMax = Math.max(1, ...rows.map((r) => Math.abs(r.usd)));
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="w-full text-[13px]">
        <thead className="bg-panel2 font-mono text-[10px] tracking-[1px] text-muted">
          <tr><th className="px-4 py-3 text-left font-semibold">DATE</th>
            <th className="px-4 py-3 text-right font-semibold">ETH</th>
            <th className="w-[34%] px-4 py-3 text-left font-semibold">USD</th>
            <th className="px-4 py-3 text-left font-semibold">RECIPIENT</th></tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const inKind = r.kind === "aoki_inkind";
            const isAoki = r.kind === "aoki" || r.kind === "aoki_offchain" || inKind;
            const noEth = r.kind === "aoki_offchain" || inKind;
            return (
            <tr key={i} className="border-t border-line"
                style={isAoki ? { background: "#1a1030" } : undefined}>
              <td className="whitespace-nowrap px-4 py-3 font-mono text-dim">{r.date}</td>
              <td className="whitespace-nowrap px-4 py-3 text-right font-bold text-ink">
                {noEth ? <span className="font-normal text-muted">{inKind ? "in-kind" : "off-chain"}</span> : eth(r.eth)}</td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="h-1.75 flex-1 overflow-hidden rounded-[4px]" style={{ background: "#1c1526" }}>
                    <span className="block h-full"
                          style={{ width: `${Math.max(2, (Math.abs(r.usd) / usdMax) * 100)}%`,
                                   background: "linear-gradient(90deg,#ff5cf0,#8be9ff)" }} />
                  </div>
                  <span className="min-w-15.5 whitespace-nowrap text-right text-muted">{usd(r.usd)}</span>
                </div>
              </td>
              <td className={`px-4 py-3 ${isAoki ? "font-bold text-hypeB" : "text-dim"}`}>
                {r.recipient}{r.recipient_addr && <span className="font-mono font-normal text-muted"> {shortAddr(r.recipient_addr)}</span>}
                {r.note && <span className="font-normal text-muted"> · {r.note}</span>}
              </td>
            </tr>
          );
          })}
        </tbody>
      </table>
    </div>
  );
}
