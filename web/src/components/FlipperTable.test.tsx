import { render, screen } from "@testing-library/react";
import FlipperTable from "./FlipperTable";
import type { Flippers } from "@/data/schemas";

const flippers: Flippers = {
  total_gains_eth: 1084.29,
  total_gains_usd: 2609301.04,
  realized_losses_eth: 145.86,
  count_profitable: 1819,
  identified_in_top: 1,
  top: [
    { wallet: "0x3e3ee1bc33cd30ef3e6daf9998794ed73b0b65a5", label: null, ens: null,
      ens_verified: false, eth_spent: 0.2, eth_received: 27.16,
      realized_pnl_eth: 26.96, realized_pnl_usd: 62000, tokens_held: 3 },
    { wallet: "0x4c5264c87e1bffa462261a14402f1645d127a804", label: "neo808.eth",
      ens: "neo808.eth", ens_verified: true, eth_spent: 13.03, eth_received: 33.83,
      realized_pnl_eth: 25.88, realized_pnl_usd: 70789, tokens_held: 10 },
  ],
};

test("shows each trader's full address", () => {
  render(<FlipperTable flippers={flippers} />);
  expect(screen.getByText("0x3e3ee1bc33cd30ef3e6daf9998794ed73b0b65a5")).toBeInTheDocument();
  expect(screen.getByText("0x4c5264c87e1bffa462261a14402f1645d127a804")).toBeInTheDocument();
});

test("links each trader to Etherscan", () => {
  render(<FlipperTable flippers={flippers} />);
  const link = screen.getByText("0x4c5264c87e1bffa462261a14402f1645d127a804").closest("a") as HTMLAnchorElement;
  expect(link.href).toBe(
    "https://etherscan.io/address/0x4c5264c87e1bffa462261a14402f1645d127a804");
});

test("shows the profitable-wallet total and total gains", () => {
  render(<FlipperTable flippers={flippers} />);
  expect(screen.getByText(/1,819 profitable wallets total/)).toBeInTheDocument();
  expect(screen.getByText("+1084.29 Ξ")).toBeInTheDocument();
});
