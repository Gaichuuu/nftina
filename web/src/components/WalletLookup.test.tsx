import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import WalletLookup from "./WalletLookup";

vi.mock("@/data/runtime", () => ({
  fetchWalletProfile: vi.fn().mockResolvedValue({
    address: "0xabc",
    overall: { wallet: "0xabc", eth_spent: 5, eth_received: 0, realized_pnl_eth: 0,
               realized_loss: 0, unrealized_loss: 5, tokens_held: 2, net_pnl_eth: -5,
               net_pnl_usd: -12000, offchain_cost_usd: 1100, all_in_net_usd: -13100,
               loss_rank: 42 },
    overallRank: 42, overallTotal: 1837,
    collections: [
      { slug: "coin_tokens", name: "MetaZoo Coin Tokens", rank: 7, total: 2729,
        entry: { wallet: "0xabc", tokens_held: 3, tokens_bought: 0, tokens_sold: 3,
                 tokens_minted: 4, tokens_received: 2, tokens_sent: 0,
                 net_pnl_eth: -5, net_pnl_usd: -12000, unrealized_loss: 5,
                 realized_pnl_eth: 0, metazoo: false } },
      { slug: "pfp_2", name: "MetaZoo Games PFP 2.0", rank: 3, total: 2381,
        entry: { wallet: "0xabc", tokens_held: 11, tokens_bought: 0, tokens_sold: 0,
                 tokens_minted: 11, tokens_received: 0, tokens_sent: 0,
                 net_pnl_eth: -0.02, net_pnl_usd: -34.66, unrealized_loss: 0,
                 realized_pnl_eth: 0, all_in_net_usd: -1134.66, metazoo: false } },
    ],
  }),
}));

it("shows overall rank and a per-collection ranked row", async () => {
  render(<MemoryRouter><WalletLookup /></MemoryRouter>);
  fireEvent.change(screen.getByPlaceholderText(/0x/i), { target: { value: "0xabc" } });
  fireEvent.click(screen.getByRole("button", { name: /check/i }));
  await waitFor(() => expect(screen.getAllByText("#42").length).toBeGreaterThan(0), { timeout: 3000 });
  expect(screen.getByText(/of 1,837/)).toBeInTheDocument();
  expect(screen.getByText("MetaZoo Coin Tokens")).toBeInTheDocument();
  expect(screen.getByText("#7")).toBeInTheDocument();
  expect(screen.getByText("/2,729")).toBeInTheDocument();
  expect(screen.getByText("+2")).toBeInTheDocument();
  expect(screen.getByText(/\(off-chain\)/)).toBeInTheDocument();
  expect(screen.getByText(/\$1,135/)).toBeInTheDocument();
  expect(screen.getByText("On-chain P&L")).toBeInTheDocument();
  expect(screen.getByText("Total USD")).toBeInTheDocument();
  expect(screen.getByText(/-\$13,100|−\$13,100/)).toBeInTheDocument();
  expect(screen.getByText(/of 1,837/)).toBeInTheDocument();
});
