import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchTokens } from "@/data/runtime";
import type { TokenRow } from "@/data/schemas";
import useInfiniteScroll from "@/lib/useInfiniteScroll";
import TokenThumb from "./TokenThumb";

const PAGE = 48;
const ALT_CONTRACT_LABELS: Record<string, string> = {
  "0x8c5acf6dbd24c66e6fd44d4a4c3d7a2d955aaad2": "the Mintable Gasless Store",
};
const SORTS: Record<string, (a: TokenRow, b: TokenRow) => number> = {
  high: (a, b) => b.last_paid_eth - a.last_paid_eth,
  low: (a, b) => a.last_paid_eth - b.last_paid_eth,
  id: (a, b) => Number(a.token_id) - Number(b.token_id),
  recent: (a, b) => (b.last_paid_date ?? "").localeCompare(a.last_paid_date ?? ""),
};
const SORT_LABELS: [string, string][] = [
  ["high", "Highest paid"], ["low", "Lowest paid"], ["id", "Token ID"], ["recent", "Recently paid"],
];

export function typeOf(t: TokenRow): string {
  if (t.type) return t.type;
  return (t.name ?? "").replace(/\s*#?\d+\s*$/, "").trim();
}

export default function TokenGrid(
  { slug, contract, showFilter: showFilterProp }:
  { slug: string; contract?: string; showFilter?: boolean },
) {
  const [rows, setRows] = useState<TokenRow[] | null>(null);
  const [sort, setSort] = useState("high");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const { shown, reset, sentinelRef } = useInfiniteScroll(PAGE);

  const toggleType = useCallback((v: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(v) ? next.delete(v) : next.add(v);
      return next;
    });
    reset();
  }, [reset]);

  useEffect(() => {
    let ok = true;
    setRows(null); reset(); setSelected(new Set());
    fetchTokens(slug).then((r) => { if (ok) setRows(r); }).catch(() => { if (ok) setRows([]); });
    return () => { ok = false; };
  }, [slug, reset]);

  const { types, counts } = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const t of rows ?? []) { const k = typeOf(t); if (k) counts[k] = (counts[k] ?? 0) + 1; }
    return { types: Object.keys(counts).sort(), counts };
  }, [rows]);
  const filtered = useMemo(() => {
    const r = rows ?? [];
    return selected.size === 0 ? r : r.filter((t) => selected.has(typeOf(t)));
  }, [rows, selected]);
  const sorted = useMemo(() => [...filtered].sort(SORTS[sort]), [filtered, sort]);
  const alt = useMemo(() => (rows ?? []).filter((r) => r.contract), [rows]);

  if (rows === null) return <div className="p-6 text-center text-muted">loading tokens…</div>;
  if (rows.length === 0) return <div className="p-6 text-center text-muted">no token data.</div>;

  const showFilter = showFilterProp ?? (types.length >= 2 && types.length <= 40);
  return (
    <div className="py-4 sm:p-4">
      <div className="flex flex-col gap-4 sm:flex-row">
        {showFilter && (
          <aside className="max-sm:hidden sm:w-52 sm:shrink-0" aria-label="filter by type">
            <div className="mb-1.5 flex items-baseline justify-between font-mono text-[10px] text-muted">
              <span>FILTER</span>
              {selected.size > 0 && (
                <button onClick={() => { setSelected(new Set()); reset(); }}
                        className="text-hypeB hover:underline">clear</button>
              )}
            </div>
            <div className="flex max-h-[70vh] flex-col gap-1 overflow-y-auto rounded-sm border border-line
                            bg-panel/60 p-2">
              {types.map((v) => (
                <label key={v} className="flex cursor-pointer items-start gap-1.5 text-[11px] text-ink">
                  <input type="checkbox" checked={selected.has(v)} onChange={() => toggleType(v)}
                         className="accent-hypeB" />
                  <span className="flex-1 wrap-break-word leading-tight">{v}</span>
                  <span className="font-mono text-[10px] text-muted">{counts[v]}</span>
                </label>
              ))}
            </div>
          </aside>
        )}
        <div className="flex-1">
          <div className="mb-2 flex items-start justify-between gap-2 font-mono text-[10px] text-muted">
            <div className="flex min-w-0 flex-wrap items-center gap-1.5">
              {[...selected].map((v) => (
                <button key={v} onClick={() => toggleType(v)}
                        title={`Remove ${v} filter`}
                        className="flex items-center gap-1 rounded-full border border-hypeB/40 bg-hypeB/10
                                   px-2 py-0.5 font-sans text-[11px] leading-tight text-hypeB hover:bg-hypeB/20">
                  {v}<span aria-hidden className="text-[13px] leading-none">×</span>
                </button>
              ))}
            </div>
            <select id="token-sort" aria-label="sort" value={sort} onChange={(e) => setSort(e.target.value)}
                    className="shrink-0 rounded-sm border border-line bg-panel px-1.5 py-0.5 text-ink">
              {SORT_LABELS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">
            {sorted.slice(0, shown).map((t) => <TokenThumb key={t.token_id} t={t} contract={contract} />)}
          </div>
          <div className="mt-3 text-center font-mono text-[10px] text-muted">
            {Math.min(shown, sorted.length)} / {sorted.length} tokens
          </div>
          {alt.length > 0 && (
            <div className="mt-1 text-center font-mono text-[10px] text-muted">
              {rows.length - alt.length} tokens on the primary contract + {alt.length} on{" "}
              {ALT_CONTRACT_LABELS[alt[0].contract!] ?? "a second contract"}
            </div>
          )}
          {shown < sorted.length && <div ref={sentinelRef} aria-hidden className="h-px" />}
        </div>
      </div>
    </div>
  );
}
