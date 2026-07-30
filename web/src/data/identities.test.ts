import { beforeEach, expect, it, vi } from "vitest";
import { walletName, hasWalletName, walletAvatar, addrForName, loadIdentities,
         __setIdentities } from "./identities";

const A = "0xFDB120707FEAB4215117267A0269FEC1A28EC4F7";

beforeEach(() => __setIdentities({}, {}));

it("falls back to the truncated address until the maps arrive", () => {
  expect(hasWalletName(A)).toBe(false);
  expect(walletName(A)).toMatch(/^0xfdb1.*f7$/i);
  expect(walletAvatar(A)).toBeNull();
});

it("resolves names and pfps case-insensitively once loaded", () => {
  __setIdentities({ [A.toLowerCase()]: "Argos Anon" },
                  { [A.toLowerCase()]: "https://cdn/argos.jpg" });
  expect(walletName(A)).toBe("Argos Anon");
  expect(hasWalletName(A)).toBe(true);
  expect(walletAvatar(A)).toBe("https://cdn/argos.jpg");
  expect(addrForName("  ARGOS ANON ")).toBe(A.toLowerCase());
  expect(addrForName("nobody")).toBeNull();
  expect(addrForName("")).toBeNull();
});

it("degrades to empty maps when the files are missing, never throwing", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404 }));
  vi.resetModules();
  const mod = await import("./identities");
  await expect(mod.loadIdentities()).resolves.toBeUndefined();
  expect(mod.walletName(A)).toMatch(/^0xfdb1/i);
  vi.unstubAllGlobals();
});

it("fetches each map once and shares the in-flight promise", async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
  vi.stubGlobal("fetch", fetchMock);
  vi.resetModules();
  const mod = await import("./identities");
  await Promise.all([mod.loadIdentities(), mod.loadIdentities()]);
  expect(fetchMock).toHaveBeenCalledTimes(2);
  await mod.loadIdentities();
  expect(fetchMock).toHaveBeenCalledTimes(2);
  vi.unstubAllGlobals();
});

it("keeps loadIdentities resolvable after __setIdentities preloads", async () => {
  __setIdentities({ "0xa": "A" }, {});
  await expect(loadIdentities()).resolves.toBeUndefined();
});
