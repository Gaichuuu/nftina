import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import HomePage from "./HomePage";

it("shows headline loss + findings link", () => {
  render(<MemoryRouter><HomePage /></MemoryRouter>);
  expect(screen.getByText(/holders lost/i)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /findings/i })).toHaveAttribute(
    "href", "/where-did-the-money-go");
});
