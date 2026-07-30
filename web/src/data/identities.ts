import { useEffect, useState } from "react";
import { shortAddr } from "@/lib/format";

let names: Record<string, string> = {};
let avatars: Record<string, string> = {};
let loaded = false;
let inflight: Promise<void> | null = null;
const listeners = new Set<() => void>();

export function loadIdentities(): Promise<void> {
  if (loaded) return Promise.resolve();
  if (inflight) return inflight;
  const grab = async (path: string) => {
    try {
      const res = await fetch(path);
      return res.ok ? ((await res.json()) as Record<string, string>) : {};
    } catch {
      return {};
    }
  };
  inflight = Promise.all([
    grab("/data/wallet_identities.json"),
    grab("/data/wallet_avatars.json"),
  ]).then(([n, a]) => {
    names = n;
    avatars = a;
    loaded = true;
    inflight = null;
    listeners.forEach((fn) => fn());
  });
  return inflight;
}

export function useWalletIdentities(): boolean {
  const [ready, setReady] = useState(loaded);
  useEffect(() => {
    if (loaded) return;
    const fn = () => setReady(true);
    listeners.add(fn);
    void loadIdentities();
    return () => {
      listeners.delete(fn);
    };
  }, []);
  return ready;
}

export function walletName(addr: string): string {
  return names[addr.toLowerCase()] ?? shortAddr(addr);
}

export function hasWalletName(addr: string): boolean {
  return addr.toLowerCase() in names;
}

export function walletAvatar(addr: string): string | null {
  return avatars[addr.toLowerCase()] ?? null;
}

export function addrForName(name: string): string | null {
  const q = name.trim().toLowerCase();
  if (!q) return null;
  for (const [a, n] of Object.entries(names)) {
    if (n.toLowerCase() === q) return a;
  }
  return null;
}

export function __setIdentities(n: Record<string, string>, a: Record<string, string>) {
  names = n;
  avatars = a;
  loaded = true;
  listeners.forEach((fn) => fn());
}
