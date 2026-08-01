import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import CollectionPage from "./CollectionPage";
import { tabsFor } from "@/data/collectionUiConfig";
import { contentFor } from "@/data/bundled";

function renderAt(slug: string) {
  return render(
    <MemoryRouter initialEntries={[`/collections/${slug}`]}>
      <Routes><Route path="/collections/:slug" element={<CollectionPage />} /></Routes>
    </MemoryRouter>);
}

it("defaults to the Tokens tab, not Holders", () => {
  renderAt("coin_tokens");
  expect(screen.queryByText(/net lost \/ gained/i)).toBeNull();
  expect(screen.getByText(/loading tokens|no token data/i)).toBeInTheDocument();
});

it("shows a breadcrumb with the collection name", () => {
  renderAt("coin_tokens");
  expect(screen.getByText("Collections")).toBeInTheDocument();
  expect(screen.getAllByText(/MetaZoo Coin Tokens/i).length).toBeGreaterThan(0);
});

it("handles an unknown slug", () => {
  renderAt("nope");
  expect(screen.getByText(/no such collection/i)).toBeInTheDocument();
});

it("renders the authored overview when the Overview tab is selected", () => {
  renderAt("tournament_prizes");
  fireEvent.click(screen.getByText("Overview"));
  expect(screen.getByText(contentFor("tournament_prizes").overview[0])).toBeInTheDocument();
});

it("shows the sandbox banner without needing a tab click", () => {
  renderAt("sandbox");
  const banner = contentFor("sandbox").banner!;
  expect(banner).toBeTruthy();
  expect(screen.getByText(banner)).toBeInTheDocument();
});

test("the Utility tab appears only for a collection with products", () => {
  expect(tabsFor("coin_tokens", true)).toContain("Utility");
  expect(tabsFor("coin_tokens", false)).not.toContain("Utility");
  expect(tabsFor("coin_tokens", false)).toEqual(["Tokens", "Holders", "Overview"]);
  expect(tabsFor("sandbox", false)).toEqual(["Tokens", "Overview"]);
  expect(tabsFor("valentines", false)).toEqual(["Tokens", "Holders", "Overview"]);
  expect(tabsFor("wilderness", false)).toEqual(["Tokens", "Holders", "Overview"]);
});
