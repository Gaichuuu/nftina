import { useEffect, useMemo, useRef, useState } from "react";

export default function ModelViewer(
  { src, poster, alt, autoplay = true, autoRotate = true, picker = false, randomAnimation = false }:
  { src: string; poster?: string; alt?: string;
    autoplay?: boolean; autoRotate?: boolean; picker?: boolean; randomAnimation?: boolean }) {
  const ref = useRef<HTMLElement | null>(null);
  const boxRef = useRef<HTMLDivElement | null>(null);
  const [anims, setAnims] = useState<string[]>([]);
  const [current, setCurrent] = useState("");
  const [open, setOpen] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const sortedAnims = useMemo(() => [...anims].sort((a, b) => a.localeCompare(b)), [anims]);
  const rotate = autoRotate && !picker;

  useEffect(() => {
    let mounted = true;
    setLoaded(false);
    import("@google/model-viewer").then(() => {
      const el = ref.current as any;
      if (!el || !mounted) return;
      const onLoad = () => {
        if (!mounted) return;
        setLoaded(true);
        const list: string[] = el.availableAnimations ?? [];
        setAnims(list);
        const idle = list.find((n) => /idle/i.test(n)) || list[0] || "";
        const chosen = randomAnimation && list.length
          ? list[Math.floor(Math.random() * list.length)]
          : idle;
        setCurrent(chosen);
        if (chosen) el.animationName = chosen;
        if (autoplay) {
          el.autoplay = true;
          try { el.play?.({ repetitions: Infinity }); } catch { /* no clips */ }
        }
      };
      if (el.loaded) onLoad();
      el.addEventListener("load", onLoad, { once: true });
      el.addEventListener("error", () => { if (mounted) setLoaded(true); }, { once: true });
    });
    return () => { mounted = false; };
  }, [autoplay, src, randomAnimation]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  function pick(name: string) {
    setCurrent(name);
    setOpen(false);
    const el = ref.current as any;
    if (!el) return;
    el.animationName = name;
    try { el.play?.({ repetitions: Infinity }); } catch { /* no clips */ }
  }

  return (
    <div className="relative h-full w-full">
      <model-viewer
        ref={ref as any}
        src={src} poster={poster} alt={alt}
        autoplay={autoplay || undefined}
        camera-controls
        auto-rotate={rotate || undefined}
        auto-rotate-delay={rotate ? 0 : undefined}
        rotation-per-second={rotate ? "24deg" : undefined}
        interaction-prompt="none" loading="eager" touch-action="pan-y"
        camera-orbit="180deg 75deg auto"
        style={{ width: "100%", height: "100%", background: "transparent",
                 ["--poster-color" as any]: "transparent" }} />
      {!loaded && (
        <div role="status" aria-label="Loading 3D model"
             className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
          <span className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-hypeB
                           [animation-duration:.8s]" />
        </div>
      )}
      {picker && anims.length > 1 && (
        <div ref={boxRef} className="absolute left-2 top-2 z-20 max-w-[85%] font-mono text-[10px]">
          <button type="button" onClick={() => setOpen((o) => !o)} aria-label="animation"
                  className="flex w-full items-center gap-1.5 rounded-sm border border-line bg-bg/85 px-2 py-1 text-ink outline-none hover:border-hypeB/40">
            <span className="truncate">{current || "animation"}</span>
            <span className="shrink-0 text-muted">{open ? "▲" : "▼"} {anims.length}</span>
          </button>
          {open && (
            <ul className="mt-1 max-h-60 w-max min-w-full overflow-y-auto rounded-sm border border-line bg-bg/95 shadow-lg">
              {sortedAnims.map((a) => (
                <li key={a}>
                  <button type="button" onClick={() => pick(a)}
                          className={`block w-full whitespace-nowrap px-2 py-1 text-left hover:bg-panel ${a === current ? "text-hypeB" : "text-ink"}`}>
                    {a}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
