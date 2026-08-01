export default function Tabs({ tabs, active, onChange }:
  { tabs: string[]; active: string; onChange: (t: string) => void }) {
  return (
    <div className="flex overflow-x-auto border-b border-line font-mono text-[12px]
                    max-sm:-mx-5 max-sm:px-5">
      {tabs.map((t) => (
        <button key={t} onClick={() => onChange(t)}
          className={`shrink-0 whitespace-nowrap px-3 py-2.5 uppercase sm:px-4 ${active === t
            ? "font-extrabold text-ink" : "text-muted"}`}
          style={active === t ? { borderBottom: "2px solid var(--color-hypeA)" } : undefined}>
          {t}
        </button>
      ))}
    </div>
  );
}
