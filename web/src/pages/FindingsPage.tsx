import { findings } from "@/data/bundled";
import { eth, usd, compactUsd, etherscanAddr } from "@/lib/format";
import Container from "@/components/Container";
import { StatCell, StatStrip } from "@/components/StatCell";
import LedgerTable from "@/components/LedgerTable";
import AcquisitionTable from "@/components/AcquisitionTable";
import FlipperTable from "@/components/FlipperTable";
import WalletAvatar from "@/components/WalletAvatar";
import UsdAuditSection from "@/components/UsdAuditSection";

const EXCHANGE_RE = /coinbase|ftx|binance|kraken/i;

export default function FindingsPage() {
  const { legs, flippers, payout_ledger, acquisitions, insider } = findings;
  const insiderRows = payout_ledger.filter((r) => r.kind === "insider");
  return (
    <div>
      {/* hero  */}
      <section style={{ background: "radial-gradient(90% 130% at 82% 20%, #241238, #0c0912 64%)" }}>
        <Container className="pb-10 pt-12">
      <header className="max-w-180">
        <h1 className="text-[40px] font-black leading-none tracking-[-0.03em] text-ink sm:text-[52px]">
          Where did the money go?
        </h1>
        <p className="mt-4 max-w-180 text-pretty text-[15px] leading-[1.6] text-dim">
          One of the great MetaZoo mysteries. Using the power of the blockchain, we're able to reconstruct the financial flow of money from public transactions.
        </p>
      </header>

      {/* stats */}
      <StatStrip className="mt-8 grid-cols-2 sm:grid-cols-4">
        <StatCell big={eth(legs.secondary_volume_eth)}
                  sub={compactUsd(legs.secondary_volume_usd)} label="Secondary volume in" />
        <StatCell big={eth(legs.royalties_eth)}
                  sub={compactUsd(legs.royalties_usd)} label="→ MetaZoo Royalties" />
        <StatCell tone="hype" big={eth(legs.aoki_eth)}
                  sub={compactUsd(legs.aoki_usd)} label="→ Sent to Aoki" />
        <StatCell tone="loss" big={eth(legs.insider_eth)}
                  sub={compactUsd(legs.insider_usd)} label="→ Insiders cashed out" />
      </StatStrip>
      <p className="mt-3 max-w-180 font-mono text-[10px] leading-normal text-muted">
        USD valued when each amount moved.
      </p>
        </Container>
      </section>
      <Container className="pb-12">

      {/* profited */}
      <section className="mt-4">
        <h2 className="section-h2 mb-5">
          Flippers extracted {eth(flippers.total_gains_eth)} / {compactUsd(flippers.total_gains_usd)}
        </h2>
        <FlipperTable flippers={flippers} />
      </section>

      {/* ledger */}
      <section className="mt-16">
        <h2 className="section-h2 mb-5">
          Treasury payout ledger
        </h2>
        <LedgerTable rows={payout_ledger} />
        <p className="mt-2.5 max-w-225 font-mono text-[10px] leading-normal text-muted">
          in-kind and off-chain rows
          are not counted in the AOKI total above. 
        </p>
      </section>

      {/* acquisitions */}
      <section className="mt-16">
        <h2 className="section-h2 mb-5">
          Aoki goes on a manic {compactUsd(acquisitions.total_usd)} NFT buying spree
        </h2>
        <AcquisitionTable acq={acquisitions} />
        <p className="mt-5 max-w-225 font-mono text-[11px] leading-[1.7] text-muted">
          ETH is fungible. No specific NFT is claimed to be bought with MetaZoo money.
        </p>
      </section>

      {/* insiders */}
      <h2 className="section-h2 mt-16 mb-5">
      Insider cash-out</h2>
      <section className="mt-0 rounded-md border border-hypeA/40 bg-panel p-6 max-sm:-mx-5
                          max-sm:rounded-none max-sm:border-x-0 max-sm:px-5">
        <div className="eyebrow text-loss">
          {eth(insider.eth)} → {insider.exchange} · <span className="text-ink">unknown</span> on-chain
        </div>
        <p className="mt-3 max-w-225 text-pretty text-[13px] leading-[1.6] text-dim">{insider.note}</p>
        {insiderRows.length > 0 && (
          <>
            <div className="mt-4 grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
              {insiderRows.map((r, i) => {
                const full = /^0x[0-9a-fA-F]{40}$/.test(r.recipient_addr);
                return (
                  <div key={r.recipient_addr || i}
                       className="rounded-sm border border-line bg-panel3 p-3.5 transition-colors
                                  hover:border-hypeA/40">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {r.recipient_addr && <WalletAvatar addr={r.recipient_addr} size={22} />}
                        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                          unknown</span>
                      </div>
                      <span className="font-mono text-[10px] text-muted">{r.date}</span>
                    </div>
                    {full ? (
                      <a href={etherscanAddr(r.recipient_addr)} target="_blank" rel="noopener noreferrer"
                         className="mt-2 block break-all font-mono text-[10.5px] text-dim
                                    transition-colors hover:text-hypeA">
                        {r.recipient_addr}
                      </a>
                    ) : (
                      <div className="mt-2 break-all font-mono text-[10.5px] text-muted">
                        {r.recipient_addr || r.recipient}
                      </div>
                    )}
                    <div className="mt-2 text-[16px] font-extrabold leading-none tabular-nums text-loss">{eth(r.eth)}</div>
                    <div className="font-mono text-[11px] tabular-nums text-dim">{usd(r.usd)}</div>
                    {r.endpoint && (
                      <div className="mt-1.5 text-[10px] font-bold">
                        <span className="text-muted">cashed out → </span>
                        <span className={EXCHANGE_RE.test(r.endpoint)
                          ? "text-hypeA" : "text-dim"}>{r.endpoint}</span>
                      </div>
                    )}
                    {r.note && <div className="mt-1.5 text-[10px] leading-[1.4] text-muted">{r.note}</div>}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </section>

      <UsdAuditSection />
      </Container>
    </div>
  );
}
