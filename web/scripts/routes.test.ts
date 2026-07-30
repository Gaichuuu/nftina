import { describe, it, expect } from "vitest";
import { SLUGS } from "@/data/bundled";
import { buildRoutes } from "./routelist";

describe("prerender route list", () => {
  it("prerenders home, collections index, findings, 10 collection details", () => {
    const urls = buildRoutes().map((r) => r.url);
    expect(urls).toContain("/");
    expect(urls).toContain("/collections");
    expect(urls).toContain("/where-did-the-money-go");
    for (const s of SLUGS) expect(urls).toContain(`/collections/${s}`);
    expect(urls.filter((u) => u.startsWith("/collections/"))).toHaveLength(10);
    expect(buildRoutes()).toHaveLength(13);
  });
});
