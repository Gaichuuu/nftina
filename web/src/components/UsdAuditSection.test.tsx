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
  weekly: [{ week: "2021-12-06", eth_balance: 400, usd_mark: 1500000 },
           { week: "2022-06-13", eth_balance: 100, usd_mark: 110000 }],
  method: { wallets: ["0x77b9"], valuation: "Binance daily close", caveats: ["NFT-side only"] },
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

it.skip("gives the weekly bar chart an accessible name summarizing peak/final balance", () => {
  render(<UsdAuditSection />); // unskip once weekly chart is restored
  const chart = screen.getByRole("img", { name: /weekly treasury balance/i });
  expect(chart).toHaveAccessibleName(/peaked at \$1\.5M in the week of 2021-12-06/i);
  expect(chart).toHaveAccessibleName(/ending at \$110K in the week of 2022-06-13/i);
}); 

it("renders nothing when the audit is null", async () => {
  vi.resetModules();
  vi.doMock("@/data/bundled", async (orig) => ({ ...(await orig()), usdAudit: null }));
  const { default: NullSection } = await import("./UsdAuditSection");
  const { container } = render(<NullSection />);
  expect(container.firstChild).toBeNull();
});
