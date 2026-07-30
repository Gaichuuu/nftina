import { describe, it, expect } from "vitest";
import { eth, usd, compactUsd, ethUsd, shortAddr, pct, cdnResized } from "./format";

describe("format", () => {
  it("eth", () => { expect(eth(210.3685)).toBe("210.37 Ξ"); expect(eth(0.00487, 3)).toBe("0.005 Ξ"); });
  it("usd", () => { expect(usd(1225881.8)).toBe("$1,225,882"); });
  it("compactUsd", () => { expect(compactUsd(1225881.8)).toBe("$1.2M"); expect(compactUsd(332000)).toBe("$332K"); expect(compactUsd(-1500)).toBe("−$1K"); expect(compactUsd(-1500000)).toBe("−$1.5M"); });
  it("ethUsd", () => {
    expect(ethUsd(210.3685, 488095)).toBe("210.37 Ξ · $488,095");
    expect(ethUsd(1.5, null)).toBe("1.50 Ξ");
  });
  it("shortAddr", () => { expect(shortAddr("0x2d366be8fa4d15c289964dd4adf7be6cc5e896e8")).toBe("0x2d36…96e8"); });
  it("pct", () => { expect(pct(-99.2)).toBe("−99%"); });
  it("cdnResized", () => {
    expect(cdnResized("https://gaichu.b-cdn.net/nftina/tokens/x.png", 420))
      .toBe("https://gaichu.b-cdn.net/nftina/tokens/x.png?width=420");
    expect(cdnResized("https://gaichu.b-cdn.net/nftina/acquisitions/punk.svg", 420))
      .toBe("https://gaichu.b-cdn.net/nftina/acquisitions/punk.svg");
    expect(cdnResized("https://example.com/a.png", 420)).toBe("https://example.com/a.png");
  });
});
