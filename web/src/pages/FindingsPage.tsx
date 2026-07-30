import { findings } from "@/data/bundled";
import { eth, usd, compactUsd, etherscanAddr } from "@/lib/format";
import Container from "@/components/Container";
import { StatCell, StatStrip } from "@/components/StatCell";
import LedgerTable from "@/components/LedgerTable";
import AcquisitionTable from "@/components/AcquisitionTable";
import FlipperTable from "@/components/FlipperTable";
import WalletAvatar from "@/components/WalletAvatar";
import UsdAuditSection from "@/components/UsdAuditSection";

export default function FindingsPage() {
  const { legs, flippers, payout_ledger, acquisitions, insider } = findings;
  const insiderRows = payout_ledger.filter((r) => r.kind === "insider");
  const cashedToExchange = insiderRows.filter((r) => /coinbase|ftx|binance|kraken/i.test(r.endpoint ?? "")).length;
  return (
    <div>
      {/* hero  */}
      <section style={{ background: "radial-gradient(90% 130% at 82% 20%, #241238, #0c0912 64%)" }}>
        <Container className="pb-9 pt-12">
      <header className="max-w-180">
        <h1 className="mt-4 text-[40px] font-black leading-none tracking-[-0.03em] text-ink sm:text-[56px]">
          Where did the money go?
        </h1>
        <p className="mt-4 text-[15px] leading-[1.6] text-dim">
          A common question when it comes to MetaZoo finanances. The figures below are reconstructed from public transactions.
        </p>
      </header>

      {/* stats */}
      <StatStrip cols={4} className="mt-9 grid-cols-2 sm:grid-cols-4">
        <StatCell numClass="text-[24px]" big={eth(legs.secondary_volume_eth)}
                  sub={compactUsd(legs.secondary_volume_usd)} label="secondary volume in" />
        <StatCell numClass="text-[24px]" big={eth(legs.royalties_eth)}
                  sub={compactUsd(legs.royalties_usd)} label="MetaZoo royalties" />
        <StatCell numClass="text-[24px]" tone="hype" big={eth(legs.aoki_eth)}
                  sub={compactUsd(legs.aoki_usd)} label="→ Aoki" />
        <StatCell numClass="text-[24px]" tone="loss" big={eth(legs.insider_eth)}
                  sub={compactUsd(legs.insider_usd)} label="insiders → cashed out" />
      </StatStrip>
      <p className="mt-3 max-w-180 font-mono text-[10px] leading-normal text-muted">
        USD valued when each amount moved.
      </p>
        </Container>
      </section>
      <Container className="pb-12">
      {/* {findings.pfp2_offchain_revenue_usd ? (
        <p className="mt-3 text-[13px] text-dim">
          PFP 2.0 off-chain box sales: MetaZoo took an estimated{" "}
          <span className="font-bold text-ink">{usd(findings.pfp2_offchain_revenue_usd)}</span>{" "}
          gross, at $100 per PFP box before box costs. Off-chain and not part of the on-chain totals above.
        </p>
      ) : null} */}

      {/* profited */}
      <section className="mt-13">
      <h2 className="mb-5 text-[26px] font-black tracking-tight">
          Flippers extracted {eth(flippers.total_gains_eth)} / {compactUsd(flippers.total_gains_usd)}
        </h2>
        <div className="mt-3.5"><FlipperTable flippers={flippers} /></div>
      </section>

      {/* ledger */}
      <section className="mt-13">
        <div className="eyebrow mb-4 text-loss">Payout ledger</div>
        <LedgerTable rows={payout_ledger} />
        <p className="mt-2.5 font-mono text-[10px] leading-normal text-muted">
          Rows marked in-kind or off-chain moved no ETH and are shown for completeness only:
          they are not counted in the MetaZoo to Aoki total above. In-kind NFT transfers are
          valued at the median secondary price in the month they moved.
        </p>
      </section>

      {/* acquisitions */}
      <section className="mt-13">
        <div className="eyebrow mb-1.5 text-hypeB">What the money became</div>
        <h2 className="mb-5 text-[26px] font-black tracking-tight">
          Aoki goes on manic {compactUsd(acquisitions.total_usd)} NFT buying spree
        </h2>
        <AcquisitionTable acq={acquisitions} />
      </section>

      {/* insiders */}
      <section className="mt-9 rounded-md p-5.5" style={{ border: "1px dashed var(--color-hypeA)" }}>
        <div className="eyebrow text-loss">
          Insider cash-out · {eth(insider.eth)} → {insider.exchange} · <span className="text-ink">unknown</span> on-chain
        </div>
        <p className="mt-3 text-[13px] leading-[1.6] text-dim">{insider.note}</p>
        {insiderRows.length > 0 && (
          <>
            <p className="mt-4 font-mono text-[10px] leading-normal text-muted">
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
                  <div key={r.recipient_addr || i} className="rounded-sm border border-line bg-panel p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {r.recipient_addr && <WalletAvatar addr={r.recipient_addr} size={22} />}
                        <span className="eyebrow text-muted">unknown</span>
                      </div>
                      <span className="font-mono text-[10px] text-muted">{r.date}</span>
                    </div>
                    {full ? (
                      <a href={etherscanAddr(r.recipient_addr)} target="_blank" rel="noopener noreferrer"
                         className="mt-2 block break-all font-mono text-[10.5px] text-dim hover:text-hypeA">
                        {r.recipient_addr}
                      </a>
                    ) : (
                      <div className="mt-2 break-all font-mono text-[10.5px] text-muted">
                        {r.recipient_addr || r.recipient}
                      </div>
                    )}
                    <div className="mt-2 text-[15px] font-extrabold leading-none text-loss">{eth(r.eth)}</div>
                    <div className="mt-0.5 text-[11px] text-dim">{usd(r.usd)}</div>
                    {r.endpoint && (
                      <div className="mt-1.5 text-[10px] font-bold">
                        <span className="text-muted">cashed out → </span>
                        <span className={/coinbase|ftx|binance|kraken/i.test(r.endpoint)
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

      <p className="mt-10 font-mono text-[11px] leading-[1.6] text-muted">
        ETH is fungible. No specific NFT is claimed to be bought with MetaZoo money. Estimates from public on-chain data.
      </p>
      </Container>
    </div>
  );
}
