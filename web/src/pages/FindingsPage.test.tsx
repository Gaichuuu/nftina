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
