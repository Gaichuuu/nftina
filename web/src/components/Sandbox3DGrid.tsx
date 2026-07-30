import { sandbox3d } from "@/data/bundled";
import ModelViewer from "./ModelViewer";

export default function Sandbox3DGrid() {
  if (sandbox3d.length === 0)
    return <div className="p-6 text-center text-muted">no 3D assets.</div>;
  return (
    <div className="grid grid-cols-1 gap-3 py-4 sm:grid-cols-2 sm:p-4 lg:grid-cols-3">
      {sandbox3d.map((a) => (
        <div key={a.token_id} className="rounded-sm border border-line bg-panel">
          <div className="aspect-square w-full">
            <ModelViewer src={a.model} poster={a.image ?? undefined} alt={a.name} picker />
          </div>
          <div className="flex items-baseline justify-between gap-2 p-1.5">
            <span className="truncate text-[11px] font-bold text-ink">{a.name}</span>
            {a.supply != null && (
              <span className="shrink-0 font-mono text-[9px] text-muted">{a.supply.toLocaleString()} minted</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
