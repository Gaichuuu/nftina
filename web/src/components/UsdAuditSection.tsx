import { usdAudit } from "@/data/bundled";
import { eth, compactUsd } from "@/lib/format";
import { StatCell, StatStrip } from "@/components/StatCell";

const IN_SOURCES: { key: string; label: string }[] = [
  { key: "mint_proceeds", label: "NFT mint sales" },
  { key: "royalties", label: "Royalties · OpenSea creator earnings" },
  { key: "other_in", label: "Bootstrap · other" },
];

export default function UsdAuditSection() {
  if (!usdAudit) return null;
  const { headline: h, by_class, monthly, method } = usdAudit;
  const inTotal = Object.values(by_class.in).reduce((s, c) => s + c.eth, 0) || 1;
  const inRows = [
    ...IN_SOURCES.filter((s) => by_class.in[s.key]),
    ...Object.keys(by_class.in)
      .filter((k) => !IN_SOURCES.some((s) => s.key === k))
      .map((k) => ({ key: k, label: k })),
  ];
  const max = Math.max(1, ...monthly.map((m) => m.usd_mark));
  const peak = monthly.reduce((a, b) => (b.usd_mark > a.usd_mark ? b : a), monthly[0]);
  const last = monthly[monthly.length - 1];
  const chartLabel = monthly.length
    ? `Monthly treasury balance, marked to market: peaked at ${compactUsd(peak.usd_mark)} `
      + `in ${peak.month}, ending at ${compactUsd(last.usd_mark)} in ${last.month}`
    : "Monthly treasury balance, marked to market";
  return (
    <section className="mt-16">
      <div className="eyebrow text-hypeB">Treasury audit</div>
      <h2 className="mb-5 text-[28px] font-black tracking-tight">
        Where the treasury’s money came from
      </h2>
      <StatStrip className="grid-cols-1 sm:grid-cols-3">
        {inRows.map((r) => {
          const c = by_class.in[r.key];
          return (
            <StatCell key={r.key} big={eth(c.eth)}
                      sub={`${compactUsd(c.usd)} · ${Math.round((c.eth / inTotal) * 100)}%`}
                      label={r.label} />
          );
        })}
      </StatStrip>
      <p className="note-box mt-3.5">
        Of the <span className="font-bold text-ink">{eth(h.received_eth)}</span> the treasury ever took in,
        roughly four-fifths was primary <span className="font-bold text-ink">NFT mint sales</span>. The{" "}
        <span className="font-bold text-ink">royalties</span> slice reached MetaZoo mostly through OpenSea’s
        off-chain creator-earnings payout, not a direct on-chain stream: about 80% of the royalty buyers
        generated on Coin Tokens, with roughly a quarter of the later Seaport royalties split to team wallets.
      </p>
      {(() => {
        const o = by_class.out;
        const projEth = (o.project_costs?.eth ?? 0) + h.gas_eth;
        const projUsd = (o.project_costs?.usd ?? 0) + h.gas_usd_at_spend;
        const outTotal = Object.values(o).reduce((s, c) => s + c.eth, 0) + h.gas_eth || 1;
        const cells: { eth: number; usd: number; label: string; tone?: "hype" | "loss" }[] = [
          { eth: o.aoki?.eth ?? 0, usd: o.aoki?.usd ?? 0, label: "→ Aoki", tone: "hype" as const },
          { eth: o.insider?.eth ?? 0, usd: o.insider?.usd ?? 0, label: "insiders → cashed out", tone: "loss" as const },
          { eth: projEth, usd: projUsd, label: "project costs · gas + ops" },
          { eth: o.intra_cluster?.eth ?? 0, usd: o.intra_cluster?.usd ?? 0, label: "intra-cluster · own contracts" },
          { eth: o.other_out?.eth ?? 0, usd: o.other_out?.usd ?? 0, label: "unattributed payouts" },
        ].filter((c) => c.eth > 0);
        return (
          <>
            <h2 className="mb-5 mt-11 text-[28px] font-black tracking-tight">
              Where the treasury’s money went
            </h2>
            <StatStrip className={`grid-cols-2 max-sm:[&>*:nth-child(odd):last-child]:col-span-2 ${
              ["sm:grid-cols-1", "sm:grid-cols-1", "sm:grid-cols-2", "sm:grid-cols-3",
               "sm:grid-cols-4", "sm:grid-cols-5"][cells.length]}`}>
              {cells.map((c) => (
                <StatCell key={c.label} tone={c.tone} big={eth(c.eth)}
                          sub={`${compactUsd(c.usd)} · ${Math.round((c.eth / outTotal) * 100)}%`}
                          label={c.label} />
              ))}
            </StatStrip>
            <p className="note-box mt-3.5">
              Most of what left the treasury went to <span className="font-bold text-ink">insider cash-outs</span>{" "}
              (to Coinbase/FTX) and <span className="font-bold text-ink">Steve Aoki</span>. The rest is{" "}
              <span className="font-bold text-ink">project costs</span> (gas for contract deploys and reward
              mints/airdrops, plus a few token swaps), money moved <span className="font-bold text-ink">between
              MetaZoo’s own contracts</span>, and a small tail of unattributed transfers to unlabeled wallets.
              On-chain is a floor: the bulk of real project costs (physical card printing, fiat operations) never
              touched these wallets.
            </p>
            <h2 className="mb-5 mt-11 text-[28px] font-black tracking-tight">
              The USD reconciliation
            </h2>
          </>
        );
      })()}
      <StatStrip className="grid-cols-2 sm:grid-cols-4">
        <StatCell big={eth(h.received_eth)}
                  sub={compactUsd(h.received_usd_at_receipt)} label="received at receipt" />
        <StatCell big={eth(h.paid_eth)}
                  sub={compactUsd(h.paid_usd_at_spend)} label="paid out at spend" />
        <StatCell big={eth(h.gas_eth)}
                  sub={compactUsd(h.gas_usd_at_spend)} label="burned as gas fees" />
        <StatCell tone="gain" big={eth(h.still_held_eth)}
                  sub={compactUsd(h.still_held_usd_now)} label="still held on-chain today" />
      </StatStrip>
      <p className="note-box mt-3.5">
        It balances: received = paid + gas + still-held. The treasury is essentially{" "}
        <span className="font-bold text-ink">empty today ({eth(h.still_held_eth)} ≈ {compactUsd(h.still_held_usd_now)})</span>.
        The received−paid gap was almost all gas, not ETH sitting in a wallet. Because the money left
        near-immediately (not held through the crash), only{" "}
        <span className="font-bold text-loss">{compactUsd(h.depreciation_gap_usd)}</span> was lost to ETH’s
        price falling between when it arrived and when it left, small relative to where the money went.
      </p>
      <div role="img" aria-label={chartLabel}
           className="mt-4 flex h-30 items-end gap-0.5 rounded-md border border-line bg-panel3 p-3.5">
        {monthly.map((m) => (
          <div key={m.month} title={`${m.month}: ${m.eth_balance} Ξ ≈ ${compactUsd(m.usd_mark)}`}
               className="flex h-full flex-1 flex-col justify-end">
            <span className="block w-full rounded-t-xs"
                  style={{ height: `${Math.max(2, (m.usd_mark / max) * 100)}%`,
                           background: "rgba(255,107,107,.6)" }} />
          </div>
        ))}
      </div>
      <p className="mt-2.5 font-mono text-[10px] text-muted">
        treasury balance, marked to market monthly · {method.valuation}
      </p>
      <p className="mt-1 max-w-xl text-[11px] text-dim">{method.caveats.join(" ")}</p>
    </section>
  );
}
