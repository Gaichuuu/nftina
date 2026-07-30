import { render, screen } from "@testing-library/react";
import NetPnl from "./NetPnl";

it("signs ETH and USD independently when they disagree", () => {
  render(<NetPnl ethv={0.61875} usdv={-6273.47} />);
  const gain = screen.getByText(/^\+/);
  const loss = screen.getByText(/^−/);
  expect(gain.textContent).toMatch(/0\.6/);
  expect(gain.className).toContain("text-gain");
  expect(loss.textContent).toMatch(/6,273/);
  expect(loss.className).toContain("text-loss");
});

it("tones both as a loss when both are negative", () => {
  render(<NetPnl ethv={-2} usdv={-4000} />);
  for (const el of screen.getAllByText(/^−/)) expect(el.className).toContain("text-loss");
});
