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
  const cashedToExchange = insiderRows.filter((r) => EXCHANGE_RE.test(r.endpoint ?? "")).length;
  return (
    <div>
      {/* hero  */}
      <section style={{ background: "radial-gradient(90% 130% at 82% 20%, #241238, #0c0912 64%)" }}>
        <Container className="pb-10 pt-14">
      <header className="max-w-180">
        <div className="eyebrow text-loss">The investigation</div>
        <h1 className="text-[40px] font-black leading-none tracking-[-0.03em] text-ink sm:text-[52px]">
          Where did the money go?
        </h1>
        <p className="mt-4 max-w-180 text-pretty text-[15px] leading-[1.6] text-dim">
          The most common question about MetaZoo's finances. Every figure below is reconstructed
          from public transactions.
        </p>
      </header>

      {/* stats */}
      <StatStrip className="mt-9 grid-cols-2 sm:grid-cols-4">
        <StatCell big={eth(legs.secondary_volume_eth)}
                  sub={compactUsd(legs.secondary_volume_usd)} label="Secondary volume in" />
        <StatCell big={eth(legs.royalties_eth)}
                  sub={compactUsd(legs.royalties_usd)} label="Royalties to MetaZoo" />
        <StatCell tone="hype" big={eth(legs.aoki_eth)}
                  sub={compactUsd(legs.aoki_usd)} label="Sent to Aoki" />
        <StatCell tone="loss" big={eth(legs.insider_eth)}
                  sub={compactUsd(legs.insider_usd)} label="Insiders cashed out" />
      </StatStrip>
      <p className="mt-3 max-w-180 font-mono text-[10px] leading-normal text-muted">
        USD valued when each amount moved.
      </p>
        </Container>
      </section>
      <Container className="pb-12">

      {/* profited */}
      <section className="mt-16">
        <div className="eyebrow text-gain">Who profited</div>
        <h2 className="mb-5 text-[28px] font-black tracking-tight">
          Flippers extracted {eth(flippers.total_gains_eth)} / {compactUsd(flippers.total_gains_usd)}
        </h2>
        <FlipperTable flippers={flippers} />
      </section>

      {/* ledger */}
      <section className="mt-16">
        <div className="eyebrow text-loss">Payout ledger</div>
        <h2 className="mb-5 text-[28px] font-black tracking-tight">
          Every payment out of the treasury
        </h2>
        <LedgerTable rows={payout_ledger} />
        <p className="mt-2.5 max-w-225 font-mono text-[10px] leading-normal text-muted">
          Rows marked in-kind or off-chain moved no ETH and are shown for completeness only:
          they are not counted in the MetaZoo to Aoki total above. In-kind NFT transfers are
          valued at the median secondary price in the month they moved.
        </p>
      </section>

      {/* acquisitions */}
      <section className="mt-16">
        <div className="eyebrow text-hypeB">What the money became</div>
        <h2 className="mb-5 text-[28px] font-black tracking-tight">
          Aoki went on an {compactUsd(acquisitions.total_usd)} NFT buying spree
        </h2>
        <AcquisitionTable acq={acquisitions} />
      </section>

      {/* insiders */}
      <section className="mt-16 rounded-md bg-panel p-6"
               style={{ border: "1px solid rgba(255,92,240,.4)" }}>
        <div className="eyebrow text-loss">
          Insider cash-out · {eth(insider.eth)} → {insider.exchange} · <span className="text-ink">unknown</span> on-chain
        </div>
        <p className="mt-3 max-w-225 text-pretty text-[13px] leading-[1.6] text-dim">{insider.note}</p>
        {insiderRows.length > 0 && (
          <>
            <p className="mt-4 max-w-225 font-mono text-[10px] leading-[1.7] text-muted">
              {insiderRows.length} on-chain insider payouts, each to a wallet with no ENS or public
              identity. Each was traced forward until it reached an exchange or went cold:
              {" "}{cashedToExchange} of {insiderRows.length} cashed out to a centralized exchange
              (overwhelmingly Coinbase, one branch to FTX), where the personal account behind the
              deposit is KYC-gated and not public. Dates show that two wallets were paid across
              separate mints. Names like "Coinbase 44" or "Coinbase 3" are Etherscan's public
              name-tags for separate wallets Coinbase itself operates; the number is just which
              of those wallets received the deposit, not an account or a customer ID.
            </p>
            <div className="mt-2.5 grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
              {insiderRows.map((r, i) => {
                const full = /^0x[0-9a-fA-F]{40}$/.test(r.recipient_addr);
                return (
                  <div key={r.recipient_addr || i}
                       className="rounded-sm border border-line bg-panel3 p-3.5 transition-colors
                                  hover:border-[rgba(255,92,240,.4)]">
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
                    <div className="mt-0.5 font-mono text-[11px] tabular-nums text-dim">{usd(r.usd)}</div>
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

      <p className="mt-14 max-w-225 font-mono text-[11px] leading-[1.7] text-muted">
        ETH is fungible. No specific NFT is claimed to be bought with MetaZoo money. Estimates from public on-chain data.
      </p>
      </Container>
    </div>
  );
}
