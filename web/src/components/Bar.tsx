const GRADIENTS = {
  held: "linear-gradient(90deg,#8be9ff,#6bff9d)",
  gain: "linear-gradient(90deg,#6bff9d,#8be9ff)",
  hype: "linear-gradient(90deg,#ff5cf0,#8be9ff)",
} as const;

/** Ranked-value bar on the shared #1c1526 track. `min` keeps a nonzero value
 * visible; a zero value renders an empty track. */
export default function Bar(
  { value, max, gradient = "hype", min = 2, className = "h-1.75 flex-1 rounded-[4px]" }:
  { value: number; max: number; gradient?: keyof typeof GRADIENTS; min?: number; className?: string },
) {
  return (
    <div className={`overflow-hidden ${className}`} style={{ background: "#1c1526" }}>
      <span className="block h-full"
            style={{ width: `${value > 0 ? Math.max(min, (value / max) * 100) : 0}%`,
                     background: GRADIENTS[gradient] }} />
    </div>
  );
}
