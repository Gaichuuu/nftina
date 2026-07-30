import { render, screen } from "@testing-library/react";
import CollectionContentView from "./CollectionContent";

test("overview mode renders paragraphs", () => {
  render(<CollectionContentView mode="Overview"
    content={{ overview: ["Hello world."], utility: [] }} />);
  expect(screen.getByText("Hello world.")).toBeInTheDocument();
});

const PRODUCT = {
  id: "valentines_box", name: "MetaZoo Valentine's Day", price_usd: 30,
  note: "MetaZoo airdropped a Valentines NFT for each box purchased.",
  image: "https://cdn.example/utility/valentines_box.jpg",
};

test("utility mode renders a tile per product with name, price and note", () => {
  render(<CollectionContentView mode="Utility"
    content={{ overview: [], utility: [PRODUCT] }} />);
  expect(screen.getByText("MetaZoo Valentine's Day")).toBeInTheDocument();
  expect(screen.getByText("$30")).toBeInTheDocument();
  expect(screen.getByText(/airdropped a Valentines NFT/)).toBeInTheDocument();
  expect(screen.getByRole("img", { name: /Valentine/i }))
    .toHaveAttribute("src", PRODUCT.image);
});

test("a product with no price reads as free to holders", () => {
  render(<CollectionContentView mode="Utility"
    content={{ overview: [], utility: [{ ...PRODUCT, price_usd: null }] }} />);
  expect(screen.getByText(/free to holders/i)).toBeInTheDocument();
});

test("a product with no image renders a placeholder, not a broken img", () => {
  render(<CollectionContentView mode="Utility"
    content={{ overview: [], utility: [{ ...PRODUCT, image: null }] }} />);
  expect(screen.queryByRole("img")).toBeNull();
  expect(screen.getByText("MetaZoo Valentine's Day")).toBeInTheDocument();
});

test("utility mode with no products shows a fallback line", () => {
  render(<CollectionContentView mode="Utility" content={{ overview: [], utility: [] }} />);
  expect(screen.getByText(/no utility items yet/i)).toBeInTheDocument();
});

test("empty content shows a fallback line", () => {
  render(<CollectionContentView mode="Overview"
    content={{ overview: [], utility: [] }} />);
  expect(screen.getByText(/no .* yet/i)).toBeInTheDocument();
});

test("overview does not render an off-chain basis callout", () => {
  render(<CollectionContentView mode="Overview"
    content={{ overview: ["body"], utility: [],
      off_chain_basis: { unit_cost_usd: 100, unit_label: "MetaZoo NFT PFP Box",
        note: "box note", floor_usd: 3.58, loss_pct: -96.4 } }} />);
  expect(screen.getByText("body")).toBeInTheDocument();
  expect(screen.queryByText("box note")).toBeNull();
  expect(screen.queryByText("-96%")).toBeNull();
});
