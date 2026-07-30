import type { HolderEntry } from "@/data/schemas";

export default function XferCell({ e }: { e: HolderEntry }) {
  const n = (e.tokens_received ?? 0) - (e.tokens_sent ?? 0);
  if (n === 0) return <span className="text-muted">—</span>;
  return <span className="text-dim">{n > 0 ? "+" : "−"}{Math.abs(n)}</span>;
}
