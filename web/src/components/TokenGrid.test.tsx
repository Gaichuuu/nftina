import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, beforeAll, beforeEach } from "vitest";
import TokenGrid from "./TokenGrid";
import type { TokenRow } from "@/data/schemas";

let ioCallback: (entries: { isIntersecting: boolean }[]) => void = () => {};
let ioConstructCount = 0;
beforeAll(() => {
  (globalThis as any).IntersectionObserver = class {
    constructor(cb: any) { ioCallback = cb; ioConstructCount++; }
    observe() {} unobserve() {} disconnect() {}
  };
});
beforeEach(() => { ioConstructCount = 0; });

vi.mock("@/data/runtime", () => ({
  fetchTokens: vi.fn((slug: string) => {
    if (slug === "coin_tokens") {
      return Promise.resolve([
        { token_id: "83", name: null, image: null, last_paid_eth: 5.7, last_paid_date: "2022-01",
          last_paid_usd: 21463.58, floor_eth: 0.005, floor_usd: 16.25 },
      ]);
    }
    const rows: TokenRow[] = Array.from({ length: 60 }, (_, i) => ({
      token_id: String(i + 1),
      name: `${i % 2 ? "MZG Hodag" : "MZG Bigfoot"} #${i + 1}`,
      image: null, last_paid_eth: i + 1, last_paid_date: null,
      last_paid_usd: (i + 1) * 100, floor_eth: 0, floor_usd: 0,
    }));
    if (slug === "genesis_2021_mixed") {
      rows[0] = { ...rows[0], contract: "0x8c5acf6dbd24c66e6fd44d4a4c3d7a2d955aaad2" };
      rows[1] = { ...rows[1], contract: "0x8c5acf6dbd24c66e6fd44d4a4c3d7a2d955aaad2" };
    }
    return Promise.resolve(rows);
  }),
}));

const firstTile = () => screen.getAllByText(/#\d+/)[0].textContent;

it("renders a token tile with its dollar loss", async () => {
  render(<TokenGrid slug="coin_tokens" />);
  await waitFor(() => expect(screen.getByText(/#83/)).toBeInTheDocument());
  expect(screen.getByText("-$21,447")).toBeInTheDocument();
});

it("lazy-loads more tiles when the sentinel intersects (no Load more button)", async () => {
  render(<TokenGrid slug="genesis_2021" />);
  await waitFor(() => screen.getByText(/48 \/ 60 tokens/));
  expect(screen.queryByRole("button", { name: /load more/i })).toBeNull();
  ioCallback([{ isIntersecting: true }]);
  await waitFor(() => screen.getByText(/60 \/ 60 tokens/));
});

it("filters by derived type via checkboxes (multi-select)", async () => {
  render(<TokenGrid slug="genesis_2021" />);
  await waitFor(() => screen.getByText(/48 \/ 60 tokens/));
  fireEvent.click(screen.getByRole("checkbox", { name: /MZG Hodag/i }));
  await waitFor(() => screen.getByText(/30 \/ 30 tokens/));
  fireEvent.click(screen.getByRole("checkbox", { name: /MZG Bigfoot/i }));
  await waitFor(() => screen.getByText(/48 \/ 60 tokens/));
  expect(screen.getByRole("button", { name: "MZG Hodag" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "clear" }));
  await waitFor(() => screen.getByText(/48 \/ 60 tokens/));
});

it("defaults to highest-paid first and re-sorts to lowest on selection", async () => {
  render(<TokenGrid slug="genesis_2021" />);
  await waitFor(() => screen.getByText(/48 \/ 60 tokens/));
  expect(firstTile()).toContain("#60");
  fireEvent.change(screen.getByLabelText(/sort/i), { target: { value: "low" } });
  expect(firstTile()).toContain("#1");
  expect(screen.queryByText(/Mintable Gasless Store/)).toBeNull();
});

it("shows the cross-contract split note when rows carry a contract", async () => {
  render(<TokenGrid slug="genesis_2021_mixed" />);
  await waitFor(() => screen.getByText(/48 \/ 60 tokens/));
  expect(screen.getByText(/58 tokens on the primary contract \+ 2 on the Mintable Gasless Store/i))
    .toBeInTheDocument();
});

it("does not tear down and rebuild the IntersectionObserver on a sort-only re-render", async () => {
  render(<TokenGrid slug="genesis_2021" />);
  await waitFor(() => screen.getByText(/48 \/ 60 tokens/));
  const countAfterMount = ioConstructCount;
  expect(countAfterMount).toBeGreaterThan(0);
  fireEvent.change(screen.getByLabelText(/sort/i), { target: { value: "low" } });
  expect(screen.getByText(/48 \/ 60 tokens/)).toBeInTheDocument();
  expect(ioConstructCount).toBe(countAfterMount);
});
