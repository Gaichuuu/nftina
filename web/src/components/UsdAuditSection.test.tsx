import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

const AUDIT = vi.hoisted(() => ({
  headline: { received_eth: 550.9, received_usd_at_receipt: 1900000,
              paid_eth: 515.2, paid_usd_at_spend: 900000,
              residual_eth: 35.7, gas_eth: 35.6, gas_usd_at_spend: 90000,
              still_held_eth: 0.1, still_held_usd_now: 200,
              reconciles_eth: 0.0, depreciation_gap_usd: 880000 },
  by_class: { in: { mint_proceeds: { eth: 500, usd: 1700000 } },
              out: { aoki: { eth: 210, usd: 400000 } } },
  method: { wallets: ["0x77b9"], valuation: "Binance daily close", caveats: ["NFT-side only."] },
}));

vi.mock("@/data/bundled", async (orig) => ({ ...(await orig()), usdAudit: AUDIT }));
import UsdAuditSection from "./UsdAuditSection";

it("renders the reconciliation headline with paired ETH/USD figures", () => {
  render(<UsdAuditSection />);
  expect(screen.getByText(/received at receipt/i)).toBeInTheDocument();
  expect(screen.getByText(/\$1\.9M/)).toBeInTheDocument();
  expect(screen.getByText(/\$880K/)).toBeInTheDocument();
  expect(screen.getByText(/burned as gas fees/i)).toBeInTheDocument();
  expect(screen.getByText(/still held on-chain today/i)).toBeInTheDocument();
  expect(screen.queryByText(/still held, at today's price/i)).toBeNull();
});

it("always renders the methodology caveats (the figures are estimates; disclosure must ship)", () => {
  render(<UsdAuditSection />);
  expect(screen.getByText(/NFT-side only\./)).toBeInTheDocument();
});

it("renders nothing when the audit is null", async () => {
  vi.resetModules();
  vi.doMock("@/data/bundled", async (orig) => ({ ...(await orig()), usdAudit: null }));
  const { default: NullSection } = await import("./UsdAuditSection");
  const { container } = render(<NullSection />);
  expect(container.firstChild).toBeNull();
});
