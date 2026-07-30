import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import CollectionTile from "./CollectionTile";

const base = {
  collection: "coin_tokens", name: "MetaZoo Coin Tokens", contract: "0x2d",
  standard: "erc721", total_transfers: 0, total_mints: 0, unique_minters: 0,
  mint_revenue_eth: 1, mint_revenue_usd: 1, secondary_sales: 0, secondary_volume_eth: 0,
  royalty_eth: 0, floor_eth: 0.005, include_in_loss_calc: true, floor_usd: 15,
};

it("renders a real image when c.image is set", () => {
  render(<MemoryRouter><CollectionTile c={{ ...base, image: "https://cdn/coin_tokens.png" }} /></MemoryRouter>);
  const img = screen.getByRole("img");
  expect(img).toHaveAttribute("src", "https://cdn/coin_tokens.png");
});

it("renders the gradient placeholder when c.image is null", () => {
  render(<MemoryRouter><CollectionTile c={{ ...base, image: null }} /></MemoryRouter>);
  expect(screen.queryByRole("img")).toBeNull();
});
