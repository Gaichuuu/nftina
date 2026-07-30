export default function PnlButton({ onClick }: { onClick: () => void }) {
  return (
    <button onClick={onClick}
            className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold text-ink
                       transition-transform hover:scale-105"
            style={{ border: "2px solid transparent",
                     background: "linear-gradient(var(--color-bg),var(--color-bg)) padding-box,"
                       + " linear-gradient(90deg,#ff5cf0,#8be9ff) border-box" }}
            title="Show this wallet's profit & loss">P&amp;L</button>
  );
}
