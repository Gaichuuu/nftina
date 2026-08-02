const GRADIENTS = {
  value: "linear-gradient(90deg,#ff5cf0,#8be9ff)", /* money moved */
  own: "linear-gradient(90deg,#8be9ff,#6bff9d)",   /* ownership / realized gain */
} as const;

export default function Bar(
  { value, max, variant = "value", className = "flex-1" }:
  { value: number; max: number; variant?: keyof typeof GRADIENTS; className?: string },
) {
  return (
    <div className={`h-1.5 overflow-hidden rounded-[3px] ${className}`}
         style={{ background: "rgba(255,255,255,.09)",
                  boxShadow: "inset 0 0 0 1px rgba(255,255,255,.06)" }}>
      <span className="anim-growbar block h-full"
            style={{ width: `${value > 0 ? (value / max) * 100 : 0}%`,
                     minWidth: value > 0 ? 10 : 0,
                     background: GRADIENTS[variant] }} />
    </div>
  );
}
