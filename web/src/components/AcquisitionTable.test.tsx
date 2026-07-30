import { render, screen, fireEvent } from "@testing-library/react";
import AcquisitionTable from "./AcquisitionTable";
import type { Findings } from "@/data/schemas";

const acq: Findings["acquisitions"] = {
  total_eth: 100,
  total_usd: 400000,
  total_purchases: 2,
  by_collection: [
    { contract: "0xabc", name: "CryptoPunks", purchases: 7, eth: 100, usd: 400000, held_now: 5,
      image: "https://cdn/punks.avif", avg_paid_eth: 93.26, floor_eth: 31.99, loss_pct: -65.7 },
    { contract: "0xshare", name: "Shared Store", purchases: 16, eth: 1, usd: 1, held_now: null,
      image: null },
  ],
  underwater: [
    { contract: "0xabc", name: "CryptoPunks", purchases: 7, eth: 100, usd: 400000, held_now: 5,
      image: "https://cdn/punks.avif", avg_paid_eth: 93.26, floor_eth: 31.99, loss_pct: -65.7 },
  ],
  top_examples: [
    { name: "CRYPTOPUNKS", token_id: "8705", contract: "0xabc", eth: 150, usd: 486672,
      date: "2021-08-28", marketplace: "cryptopunks", image: "https://cdn/punk8705.png" },
  ],
  top_items: [],
};

test("renders one marquee NFT example per collection, linking to OpenSea", () => {
  render(<AcquisitionTable acq={acq} />);
  const img = screen.getByAltText("CRYPTOPUNKS #8705") as HTMLImageElement;
  expect(img.src).toBe("https://cdn/punk8705.png");
  const link = img.closest("a") as HTMLAnchorElement;
  expect(link.href).toBe("https://opensea.io/assets/ethereum/0xabc/8705");
});

test("renders the collection image (logo) when present", () => {
  render(<AcquisitionTable acq={acq} />);
  const imgs = screen.getAllByAltText("CryptoPunks") as HTMLImageElement[];
  expect(imgs.length).toBeGreaterThan(0);
  expect(imgs[0].src).toBe("https://cdn/punks.avif");
});

test("falls back to gradient after image load error", () => {
  render(<AcquisitionTable acq={acq} />);
  const imgs = screen.getAllByAltText("CryptoPunks");
  const before = imgs.length;
  fireEvent.error(imgs[0]);
  expect(screen.queryAllByAltText("CryptoPunks").length).toBe(before - 1);
});

test("keeps by_collection table rows intact", () => {
  render(<AcquisitionTable acq={acq} />);
  expect(screen.getAllByText(/CryptoPunks/).length).toBeGreaterThan(0);
  expect(screen.getByText(/2 buys total/)).toBeTruthy();
});

test("shows held-now count and marks multi-tenant contracts n/a", () => {
  render(<AcquisitionTable acq={acq} />);
  expect(screen.getByText("5")).toBeInTheDocument();
  expect(screen.getAllByText("n/a").length).toBeGreaterThan(0);
});

test("renders the underwater blue-chip loss % (paid → floor)", () => {
  render(<AcquisitionTable acq={acq} />);
  expect(screen.getByText("-66%")).toBeInTheDocument();
  expect(screen.getByText(/paid ~93\.26 Ξ → floor ~31\.99 Ξ/)).toBeInTheDocument();
});
