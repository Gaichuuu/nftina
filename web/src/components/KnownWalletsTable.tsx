import type { KnownWallet } from "@/data/schemas";
import TableScroller from "./TableScroller";
import WalletAvatar from "./WalletAvatar";
import { AddrLink } from "./AddrLink";

const ROLE: Record<KnownWallet["role"], { label: string; cls: string }> = {
  aoki: { label: "Aoki", cls: "text-hypeB" },
  metazoo: { label: "MetaZoo", cls: "text-hypeA" },
  contract: { label: "MetaZoo contract", cls: "text-dim" },
  insider: { label: "Insider", cls: "text-loss" },
};

export default function KnownWalletsTable({ wallets }: { wallets: KnownWallet[] }) {
  return (
    <TableScroller>
      <table className="w-full min-w-175 text-[12.5px]">
        <thead className="bg-panel2 font-mono text-[10px] font-semibold uppercase tracking-widest text-muted">
          <tr><th className="px-4 py-3 text-left">WALLET</th>
            <th className="px-4 py-3 text-left">ROLE</th>
            <th className="px-4 py-3 text-left">BASIS</th></tr>
        </thead>
        <tbody>
          {wallets.map((w) => (
            <tr key={w.address} className="border-t border-line align-top transition-colors hover:bg-hover">
              <td className="px-4 py-3.25">
                <div className="flex items-start gap-2.5">
                  <WalletAvatar addr={w.address} />
                  <div className="min-w-0">
                    <div className="font-bold text-ink">{w.name}</div>
                    <AddrLink addr={w.address} className="block text-[11px]" />
                  </div>
                </div>
              </td>
              <td className={`whitespace-nowrap px-4 py-3.25 font-mono text-[10px] font-semibold
                               uppercase tracking-[0.14em] ${ROLE[w.role].cls}`}>
                {ROLE[w.role].label}
              </td>
              <td className="max-w-90 px-4 py-3.25 text-[11.5px] leading-normal text-dim">{w.basis}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </TableScroller>
  );
}
