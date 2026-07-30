import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import HoldersTable from "./HoldersTable";

const WALLET = "0xabc0000000000000000000000000000000000001";

vi.mock("@/data/runtime", () => ({
  fetchHolders: () => Promise.resolve([
    { wallet: WALLET, tokens_held: 2,
      tokens_bought: 2, tokens_sold: 0, tokens_minted: 2, unrealized_loss: 0,
      unrealized_loss_usd: 0, realized_pnl_eth: 0, realized_pnl_usd: 0,
      net_pnl_eth: -0.2, net_pnl_usd: -400, eth_spent: 0.2, eth_received: 0,
      metazoo: false },
  ]),
  fetchWalletProfile: () => Promise.resolve({
    address: WALLET, overall: { wallet: WALLET, net_pnl_eth: -0.2, net_pnl_usd: -400,
      all_in_net_usd: -400, offchain_cost_usd: 0, realized_pnl_eth: 0, realized_loss: 0,
      unrealized_loss: 0.2, tokens_held: 2, loss_rank: 5 },
    overallRank: 5, overallTotal: 4633, collections: [],
  }),
  PROFILE_SLUGS: [],
}));

describe("HoldersTable", () => {
  it("renders a MINTED column and value", async () => {
    render(<HoldersTable slug="coin_tokens" />);
    expect(await screen.findByText("MINTED")).toBeInTheDocument();
  });

  it("opens a P&L dialog from the per-row button", async () => {
    render(<HoldersTable slug="coin_tokens" />);
    const btn = await screen.findByRole("button", { name: /P&L/i });
    fireEvent.click(btn);
    await waitFor(() => expect(screen.getByText(/Wallet profit & loss/i)).toBeInTheDocument());
    expect(screen.getByText(/of 4,633/)).toBeInTheDocument();
  });
});
