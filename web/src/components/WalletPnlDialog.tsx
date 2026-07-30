import { useEffect, useState } from "react";
import { fetchWalletProfile, type WalletProfile } from "@/data/runtime";
import { collections } from "@/data/bundled";
import WalletProfileView from "./WalletProfileView";

const NAMES = Object.fromEntries(collections.map((c) => [c.collection, c.name]));

export default function WalletPnlDialog({ address, onClose }: { address: string; onClose: () => void }) {
  const [profile, setProfile] = useState<WalletProfile | null | "loading">("loading");

  useEffect(() => {
    let ok = true;
    setProfile("loading");
    fetchWalletProfile(address, NAMES)
      .then((p) => { if (ok) setProfile(p); })
      .catch(() => { if (ok) setProfile(null); });
    return () => { ok = false; };
  }, [address]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 p-3 sm:p-8"
         role="dialog" aria-modal="true" aria-label="Wallet profit and loss" onClick={onClose}>
      <div className="w-full max-w-5xl rounded-xl border border-line bg-bg p-5 shadow-2xl"
           onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <div className="font-mono text-[11px] uppercase tracking-[1px] text-muted">Wallet profit &amp; loss</div>
          <button onClick={onClose} aria-label="Close"
                  className="rounded px-2 py-1 font-mono text-[13px] text-dim hover:text-ink">✕</button>
        </div>
        {profile === "loading" && (
          <div className="flex flex-col items-center gap-3 py-12">
            <span className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-hypeB" />
            <span className="font-mono text-[12px] text-muted">Loading…</span>
          </div>
        )}
        {profile && profile !== "loading" && <WalletProfileView p={profile} />}
        {profile === null && (
          <p className="py-10 text-center text-muted">No P&amp;L data for this wallet.</p>
        )}
      </div>
    </div>
  );
}
