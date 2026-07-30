import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Header from "./Header";

function renderHeader() {
  return render(<MemoryRouter><Header /></MemoryRouter>);
}

it("shows the brand and the three nav links (Home, Collections, Findings)", () => {
  renderHeader();
  expect(screen.queryByText(/MINT LIVE/i)).toBeNull();
  expect(screen.getByRole("link", { name: /^Home$/ })).toHaveAttribute("href", "/");
  expect(screen.getByRole("link", { name: /^Collections$/ })).toHaveAttribute("href", "/collections");
  expect(screen.getByRole("link", { name: /^Findings$/ }))
    .toHaveAttribute("href", "/where-did-the-money-go");
});
