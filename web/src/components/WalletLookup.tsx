import { useState } from "react";
import { fetchWalletProfile, type WalletProfile } from "@/data/runtime";
import { collectionNames, coinStrip } from "@/data/bundled";
import { addrForName, loadIdentities, useWalletIdentities } from "@/data/identities";
import WalletProfileView from "./WalletProfileView";

type State = { status: "idle" | "loading" | "done"; profile?: WalletProfile | null };

export default function WalletLookup() {
  const [q, setQ] = useState("");
  const [s, setS] = useState<State>({ status: "idle" });

  useWalletIdentities();
  async function go() {
    const raw = q.trim();
    if (!raw.toLowerCase().startsWith("0x")) await loadIdentities();
    const query = raw.toLowerCase().startsWith("0x") ? raw : (addrForName(raw) ?? raw);
    setS({ status: "loading" });
    const [profile] = await Promise.all([
      fetchWalletProfile(query, collectionNames).catch(() => null),
      new Promise((r) => setTimeout(r, 1400)),
    ]);
    const found = profile && (profile.overall || profile.collections.some((c) => c.entry))
      ? profile : null;
    setS({ status: "done", profile: found });
  }

  const p = s.profile;
  return (
    <div className="rounded-xl border border-line px-8 py-8 text-center"
         style={{ background: "radial-gradient(120% 140% at 50% 0%, #1c1030, #0f0b16 70%)" }}>
      <div className="mb-5 flex flex-wrap items-center justify-center" aria-hidden>
        {coinStrip.map((c) => (
          <img key={c.token_id} src={c.image} alt="" loading="lazy"
               className="h-16 w-16 rounded-full sm:h-20 sm:w-20" />
        ))}
      </div>
      <h2 className="mt-3.5 text-[32px] font-black tracking-tight">Check your wallet profit &amp; loss</h2>
      <p className="mx-auto mt-1 max-w-110 text-[14px] text-dim">
        Paste address or ENS name for collection
        <br/>breakdown and overall rank.
      </p>
      <div className="mx-auto mt-6.5 mb-4 flex max-w-130 overflow-hidden rounded-full border border-line bg-bg">
        <input value={q} onChange={(e) => setQ(e.target.value)}
               onKeyDown={(e) => e.key === "Enter" && go()} placeholder="0x… or name.eth"
               className="flex-1 bg-transparent px-5 py-3.5 font-mono text-[14px] text-ink outline-none" />
        <button onClick={go} disabled={s.status === "loading"}
                className="hype-btn px-7 text-[14px] disabled:opacity-60">Check P&amp;L</button>
      </div>

      {s.status === "loading" && (
        <div className="mt-8 flex flex-col items-center gap-3">
          <span className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-hypeB" />
          <span className="font-mono text-[12px] text-muted">Thinking…</span>
        </div>
      )}

      {s.status === "done" && p && (
        <div className="mx-auto mt-6 max-w-5xl">
          <WalletProfileView p={p} />
        </div>
      )}

      {s.status === "done" && !p && (
        <p className="mt-4 text-muted">Not found. Count yourself lucky.</p>
      )}
    </div>
  );
}
