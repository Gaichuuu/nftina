import { render, screen } from "@testing-library/react";
import Footer from "./Footer";

it("shows the estimates-from-public-data disclaimer", () => {
  render(<Footer />);
  expect(screen.getByText(/estimates from public on-chain data/i)).toBeInTheDocument();
});

it("dates the data as a point-in-time snapshot", () => {
  render(<Footer />);
  expect(screen.getByText(/captured as a snapshot on \w+ \d+, \d{4}/i)).toBeInTheDocument();
});
