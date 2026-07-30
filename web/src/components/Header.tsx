import { Link, NavLink } from "react-router-dom";
import Container from "@/components/Container";

const navClass = ({ isActive }: { isActive: boolean }) =>
  "border-b-2 pb-1 no-underline transition-colors hover:text-ink "
  + (isActive ? "border-hypeA text-ink" : "border-transparent text-dim2");

export default function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-line"
            style={{ background: "linear-gradient(90deg,#3b1d6e,#0e2a63)",
                     boxShadow: "0 1px 0 rgba(255,92,240,.18)" }}>
      <Container className="flex h-15 items-center justify-between gap-3">
        <Link to="/" className="shrink-0 font-mono text-[13px] font-bold tracking-[0.04em] text-ink no-underline sm:text-[15px]">
          METAZOO<span className="text-hypeB">NFTS</span>
          <span className="hidden font-normal min-[440px]:inline" style={{ color: "#9d90b0" }}>.com</span>
        </Link>
        <nav className="flex gap-3.5 font-mono text-[11px] tracking-wider sm:gap-6.5 sm:text-[12px]">
          <NavLink to="/" end className={navClass}>Home</NavLink>
          <NavLink to="/collections" className={navClass}>Collections</NavLink>
          <NavLink to="/where-did-the-money-go" className={navClass}>Findings</NavLink>
        </nav>
      </Container>
    </header>
  );
}
