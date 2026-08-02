import { useState } from "react";
import { fetchWalletProfile, type WalletProfile } from "@/data/runtime";
import { collectionNames, coinStrip } from "@/data/bundled";
import { addrForName, loadIdentities, useWalletIdentities } from "@/data/identities";
import { cdnResized } from "@/lib/format";
import Spinner from "./Spinner";
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
    <div className="rounded-2xl border border-line px-4 py-7 text-center max-sm:-mx-5 max-sm:rounded-none
                    max-sm:border-x-0 sm:px-8 sm:py-9"
         style={{ background: "radial-gradient(120% 140% at 50% 0%, #1c1030, #0f0b16 70%)" }}>
      <div className="mb-5 flex flex-wrap items-center justify-center" aria-hidden>
        {coinStrip.map((c) => (
          <img key={c.token_id} src={cdnResized(c.image, 160)} alt="" loading="lazy"
               className="-mx-1.5 h-13 w-13 rounded-full sm:h-19 sm:w-19" />
        ))}
      </div>
      <h2 className="text-[24px] font-black tracking-tight sm:text-[32px]">Check your wallet profit &amp; loss</h2>
      <p className="mx-auto mt-1 max-w-115 text-pretty text-[14px] text-dim">
        Paste an address or ENS name for a collection breakdown and overall rank.
      </p>
      <div className="mx-auto mt-6.5 mb-4 flex max-w-130 overflow-hidden rounded-full border border-line bg-bg
                      transition-colors hover:border-[rgba(139,233,255,.45)]
                      focus-within:border-[rgba(139,233,255,.45)]">
        <input value={q} onChange={(e) => setQ(e.target.value)}
               onKeyDown={(e) => e.key === "Enter" && go()} placeholder="0x… or name.eth"
               className="w-full min-w-0 flex-1 bg-transparent px-4 py-3.25 font-mono text-[14px] text-ink outline-none sm:px-5.5 sm:py-3.75" />
        <button onClick={go} disabled={s.status === "loading"}
                className="hype-btn shrink-0 px-4.5 text-[13px] disabled:opacity-60 sm:px-7 sm:text-[14px]">Check P&amp;L</button>
      </div>

      {s.status === "loading" && (
        <div className="mt-8 flex flex-col items-center gap-3">
          <Spinner />
          <span className="font-mono text-[12px] text-muted">Thinking…</span>
        </div>
      )}

      {s.status === "done" && p && (
        <div className="anim-rise-fast mx-auto mt-6 max-w-5xl">
          <WalletProfileView p={p} />
        </div>
      )}

      {s.status === "done" && !p && (
        <p className="mt-4 text-muted">Not found. Count yourself lucky.</p>
      )}
    </div>
  );
}
