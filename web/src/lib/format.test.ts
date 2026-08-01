import { describe, it, expect } from "vitest";
import { eth, usd, compactUsd, ethUsd, shortAddr, pct, cdnResized, longDate } from "./format";

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

describe("longDate", () => {
  it("writes prose dates as 'March 7th, 2021'", () => {
    expect(longDate("2021-03-07")).toBe("March 7th, 2021");
    expect(longDate("2026-07-29T14:55:54.721559+00:00")).toBe("July 29th, 2026");
  });

  it("gets the awkward ordinals right", () => {
    expect(longDate("2022-01-01")).toBe("January 1st, 2022");
    expect(longDate("2022-01-02")).toBe("January 2nd, 2022");
    expect(longDate("2022-01-03")).toBe("January 3rd, 2022");
    expect(longDate("2022-01-11")).toBe("January 11th, 2022");
    expect(longDate("2022-01-12")).toBe("January 12th, 2022");
    expect(longDate("2022-01-13")).toBe("January 13th, 2022");
    expect(longDate("2022-01-21")).toBe("January 21st, 2022");
  });

  it("reads the date in UTC, not the viewer's timezone", () => {
    expect(longDate("2022-01-11T00:30:00Z")).toBe("January 11th, 2022");
  });

  it("passes through anything it cannot parse", () => {
    expect(longDate("not a date")).toBe("not a date");
  });
});
