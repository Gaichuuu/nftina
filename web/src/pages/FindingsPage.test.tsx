import { render, screen } from "@testing-library/react";
import FindingsPage from "./FindingsPage";

it("shows the flow legs, ledger, and insider-unknown card", () => {
  render(<FindingsPage />);
  expect(screen.getByText(/where did the money go/i)).toBeInTheDocument();
  expect(screen.getAllByText("→ Aoki").length).toBeGreaterThan(0);
  expect(screen.getAllByText(/identity/i).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/unknown/i).length).toBeGreaterThan(1);
  expect(screen.getByText(/on-chain insider payouts/i)).toBeInTheDocument();
  expect(screen.queryByText(/kalish/i)).toBeNull();
});
