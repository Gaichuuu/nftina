import { render, screen } from "@testing-library/react";
import FindingsPage from "./FindingsPage";
import { findings } from "@/data/bundled";

it("shows the flow legs, ledger, and insider card", () => {
  render(<FindingsPage />);
  expect(screen.getByText(/where did the money go/i)).toBeInTheDocument();
  expect(screen.getAllByText("→ Sent to Aoki").length).toBeGreaterThan(0);
  expect(screen.getByText(findings.insider.note)).toBeInTheDocument();
  expect(screen.getAllByText(/unknown/i).length).toBeGreaterThan(1);
  const insiderRows = findings.payout_ledger.filter((r) => r.kind === "insider");
  expect(screen.getAllByText(/cashed out →/).length).toBe(
    insiderRows.filter((r) => r.endpoint).length);
  expect(screen.queryByText(/kalish/i)).toBeNull();
});

it("links every ledger address to Etherscan", () => {
  const { container } = render(<FindingsPage />);
  for (const r of findings.payout_ledger.filter((r) => r.recipient_addr)) {
    expect(container.querySelector(`a[href="https://etherscan.io/address/${r.recipient_addr}"]`)).not.toBeNull();
  }
  const tx = findings.payout_ledger.map((r) => r.note.match(/0x[0-9a-f]{64}/)?.[0]).find(Boolean);
  expect(tx).toBeTruthy();
  expect(container.querySelector(`a[href="https://etherscan.io/tx/${tx}"]`)).not.toBeNull();
});

it("renders the known-wallets table with a linked row per wallet", () => {
  const { container } = render(<FindingsPage />);
  expect(screen.getByRole("heading", { name: "Known wallets" })).toBeInTheDocument();
  expect(findings.known_wallets.length).toBeGreaterThan(0);
  for (const w of findings.known_wallets) {
    expect(screen.getByText(w.name)).toBeInTheDocument();
    expect(container.querySelector(`a[href="https://etherscan.io/address/${w.address}"]`)).not.toBeNull();
  }
});
