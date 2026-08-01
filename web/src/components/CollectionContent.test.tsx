import { renderToString } from "react-dom/server";
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


it("renders inline **bold** lead-ins instead of printing literal asterisks", () => {
  render(<CollectionContentView mode="Overview" content={{
    overview: ["**It was claimed, not sold.** The boxes shipped in December.",
               "- **Allow list** · 0.1 ETH"],
    utility: [],
  } as never} />);
  expect(screen.getByText("It was claimed, not sold.").tagName).toBe("STRONG");
  expect(screen.getByText("Allow list").tagName).toBe("STRONG");
  expect(document.body.textContent).not.toMatch(/\*\*/);
});

test("an overview with a video renders looping media with the image as its poster", () => {
  const html = renderToString(<CollectionContentView mode="Overview" content={{
    overview: ["The Mothman."], utility: [],
    overview_image: "https://cdn.example/mothman.jpg",
    overview_video: "https://cdn.example/mothman.mp4",
  }} />);
  expect(html).toContain("<video");
  expect(html).toContain("https://cdn.example/mothman.mp4");
  expect(html).toContain('poster="https://cdn.example/mothman.jpg"');
});

test("a 3d showcase collection renders a model instead of the authored image", () => {
  const html = renderToString(<CollectionContentView mode="Overview" slug="sandbox"
    content={{ overview: ["Six voxel characters."], utility: [] }} />);
  expect(html).toContain("space-penguins");
  expect(html).toContain("Six voxel characters.");
});

test("a collection with no figure at all still renders its blocks", () => {
  const html = renderToString(<CollectionContentView mode="Overview"
    content={{ overview: ["Just words."], utility: [] }} />);
  expect(html).toContain("Just words.");
  expect(html).not.toContain("<img");
});

test("token art is fitted whole while a product photo crops to fill", () => {
  render(<CollectionContentView mode="Utility" content={{ overview: [], utility: [
    { ...PRODUCT, id: "photo", name: "Dim Mak box" },
    { ...PRODUCT, id: "art", name: "Manta Ray token", fit: true },
  ] }} />);
  expect(screen.getByRole("img", { name: "Dim Mak box" })).toHaveClass("object-cover");
  expect(screen.getByRole("img", { name: "Manta Ray token" })).toHaveClass("object-contain");
});
