import { useState } from "react";
import type { Flippers } from "@/data/schemas";
import { eth, usd, compactUsd, etherscanAddr } from "@/lib/format";
import { walletName, hasWalletName, useWalletIdentities } from "@/data/identities";
import Bar from "./Bar";
import TableScroller from "./TableScroller";
import PnlButton from "./PnlButton";
import WalletAvatar from "./WalletAvatar";
import WalletPnlDialog from "./WalletPnlDialog";

export default function FlipperTable({ flippers }: { flippers: Flippers }) {
  const [pnlWallet, setPnlWallet] = useState<string | null>(null);
  useWalletIdentities();
  const usdMax = Math.max(1, ...flippers.top.map((f) => f.realized_pnl_usd));
  return (
    <>
    <TableScroller>
      <table className="w-full min-w-150 text-[12.5px] tabular-nums">
        <thead className="bg-panel2 font-mono text-[10px] font-semibold uppercase tracking-widest text-muted">
          <tr>
            <th className="px-4 py-3 text-left">TRADER</th>
            <th className="px-4 py-3 text-right">ETH IN → OUT</th>
            <th className="px-4 py-3 text-right">REALIZED GAIN</th>
            <th className="w-[30%] px-4 py-3 text-left">USD</th>
          </tr>
        </thead>
        <tbody>
          {flippers.top.map((f) => {
            const named = hasWalletName(f.wallet);
            return (
              <tr key={f.wallet}
                  className="border-t border-line align-middle transition-colors hover:bg-hover">
                <td className="px-4 py-3.25">
                  <div className="flex items-center gap-2.5">
                    <a href={etherscanAddr(f.wallet)} target="_blank" rel="noopener noreferrer"
                       className="flex min-w-0 items-center gap-2.5 no-underline hover:opacity-90"
                       title={`${f.wallet} · view on Etherscan`}>
                      <WalletAvatar addr={f.wallet} />
                      <span className="min-w-0">
                        <span className="block truncate font-bold text-ink">
                          {named ? walletName(f.wallet) : "Unknown wallet"}
                          {named && f.ens && f.ens_verified &&
                            <span className="ml-1 text-[9px] text-gain">✦ ENS</span>}
                        </span>
                        <span className="block break-all font-mono text-[11px] text-dim">{f.wallet}</span>
                      </span>
                    </a>
                    <PnlButton onClick={() => setPnlWallet(f.wallet)} />
                  </div>
                </td>
                <td className="px-4 py-3.25 text-right font-mono text-[11px] whitespace-nowrap text-dim">
                  {eth(f.eth_spent)} → {eth(f.eth_received)}
                </td>
                <td className="px-4 py-3.25 text-right font-bold whitespace-nowrap text-gain">+{eth(f.realized_pnl_eth)}</td>
                <td className="px-4 py-3.25">
                  <div className="flex items-center gap-2">
                    <Bar value={f.realized_pnl_usd} max={usdMax} variant="own" />
                    <span className="min-w-15.5 whitespace-nowrap text-right text-dim">{usd(f.realized_pnl_usd)}</span>
                  </div>
                </td>
              </tr>
            );
          })}
          <tr className="border-t border-line bg-total text-muted">
            <td className="px-4 py-3.25">…{flippers.count_profitable.toLocaleString()} profitable wallets total</td>
            <td className="px-4 py-3.25"></td>
            <td className="px-4 py-3.25 text-right font-bold whitespace-nowrap text-gain">+{eth(flippers.total_gains_eth)}</td>
            <td className="px-4 py-3.25 text-right whitespace-nowrap">{compactUsd(flippers.total_gains_usd)}</td>
          </tr>
        </tbody>
      </table>
    </TableScroller>
    {pnlWallet && <WalletPnlDialog address={pnlWallet} onClose={() => setPnlWallet(null)} />}
    </>
  );
}
