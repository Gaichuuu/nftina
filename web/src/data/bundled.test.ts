import { describe, it, expect } from "vitest";
import { summary, collections, volume, findings, SLUGS } from "./bundled";
import { Holders } from "./schemas";
import coinHolders from "sitedata/collections/coin_tokens/holders.json";

describe("bundled data", () => {
  it("summary has headline figures", () => {
    expect(summary.secondary_volume_eth).toBeGreaterThan(0);
    expect(summary.wallets_net_loss).toBeGreaterThan(0);
  });
  it("collections = 10, each with floor_usd", () => {
    expect(collections).toHaveLength(10);
    for (const c of collections) expect(typeof c.floor_usd).toBe("number");
  });
  it("volume ecosystem points carry eth+usd", () => {
    expect(volume.ecosystem[0]).toHaveProperty("usd");
  });
  it("findings legs reconcile to summary secondary volume", () => {
    expect(findings.legs.secondary_volume_eth).toBeCloseTo(summary.secondary_volume_eth, 4);
  });
  it("per-collection holders.json is a single ranked table, most-lost-first", () => {
    const h = Holders.parse(coinHolders);
    expect(h.holders.length).toBeGreaterThan(0);
    expect(h.holders[0].net_pnl_eth).toBeLessThanOrEqual(h.holders[h.holders.length - 1].net_pnl_eth);
  });
  it("SLUGS covers all collections", () => {
    for (const c of collections) expect(SLUGS).toContain(c.collection);
  });
});
