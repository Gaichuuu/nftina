import { render, screen, fireEvent } from "@testing-library/react";
import TokenThumb from "./TokenThumb";

const base = { token_id: "1", last_paid_eth: 0.1, last_paid_date: null,
  last_paid_usd: 400, floor_eth: 0.005, floor_usd: 20 };

test("renders the CDN image when present", () => {
  render(<TokenThumb t={{ ...base, name: "Bigfoot", image: "https://cdn/1.png" }} />);
  const img = screen.getByAltText("Bigfoot") as HTMLImageElement;
  expect(img.src).toBe("https://cdn/1.png");
});

test("falls back to gradient after image load error", () => {
  render(<TokenThumb t={{ ...base, name: "Bigfoot", image: "https://cdn/broken.png" }} />);
  const img = screen.getByAltText("Bigfoot");
  fireEvent.error(img);
  expect(screen.queryByAltText("Bigfoot")).toBeNull(); 
});

test("shows gradient when image is null", () => {
  const { container } = render(<TokenThumb t={{ ...base, name: null, image: null }} />);
  expect(container.querySelector("img")).toBeNull();
});

const t = { token_id: "83", name: "MetaZoo Games Token #83", image: null,
  last_paid_eth: 5.7, last_paid_date: "2022-01", last_paid_usd: 21463.58,
  floor_eth: 0.00487, floor_usd: 16.25 };

it("links to OpenSea and shows only the negative dollar amount", () => {
  render(<TokenThumb t={t} contract="0x2d366be8fa4d15c289964dd4adf7be6cc5e896e8" />);
  expect(screen.getByRole("link")).toHaveAttribute("href",
    "https://opensea.io/assets/ethereum/0x2d366be8fa4d15c289964dd4adf7be6cc5e896e8/83");
  expect(screen.getByText("-$21,447")).toBeInTheDocument(); 
  expect(screen.queryByText(/Ξ/)).toBeNull();
});

it("renders a plain tile with no loss figure when not under water or without a contract", () => {
  render(<TokenThumb t={{ ...t, floor_usd: 30000 }} />);
  expect(screen.queryByRole("link")).toBeNull();
  expect(screen.queryByText(/\$/)).toBeNull();
});

it("prefers the per-token contract over the grid contract for the OpenSea link", () => {
  render(<TokenThumb t={{ ...t, contract: "0x8c5acf6dbd24c66e6fd44d4a4c3d7a2d955aaad2" }}
                     contract="0x2d366be8fa4d15c289964dd4adf7be6cc5e896e8" />);
  expect(screen.getByRole("link")).toHaveAttribute("href",
    "https://opensea.io/assets/ethereum/0x8c5acf6dbd24c66e6fd44d4a4c3d7a2d955aaad2/83");
});

it("plays the animation loop when a token has one, with the still as poster", () => {
  const { container } = render(
    <TokenThumb t={{ ...base, name: "Mothman", image: "https://cdn/still.jpg", video: "https://cdn/loop.mp4" }} />);
  const vid = container.querySelector("video")!;
  expect(vid).toBeInTheDocument();
  expect(vid.getAttribute("src")).toBe("https://cdn/loop.mp4");
  expect(vid.getAttribute("poster")).toBe("https://cdn/still.jpg");
  expect(vid).toHaveAttribute("loop");
  expect(vid).toHaveAttribute("playsinline");
  expect((vid as HTMLVideoElement).muted || vid.hasAttribute("muted")).toBe(true);
  expect(container.querySelector("img")).toBeNull();
});

it("shows the still when a token has no video", () => {
  const { container } = render(<TokenThumb t={{ ...base, name: "Mothman", image: "https://cdn/still.jpg" }} />);
  expect(container.querySelector("video")).toBeNull();
  expect(container.querySelector("img")).toBeInTheDocument();
});
