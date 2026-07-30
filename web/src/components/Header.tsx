import { Link, NavLink } from "react-router-dom";
import Container from "@/components/Container";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `no-underline hover:text-ink ${isActive ? "text-ink" : "text-dim2"}`;

export default function Header() {
  return (
    <header className="relative overflow-hidden"
            style={{ background: "linear-gradient(90deg,#3b1d6e,#0e2a63)" }}>
      <Container className="flex items-center justify-between py-5">
        <Link to="/" className="font-mono text-[15px] font-extrabold tracking-wide text-ink no-underline">
          METAZOO<span className="text-hypeB">NFTS</span><span className="font-medium text-muted">.com</span>
        </Link>
        <nav className="flex gap-6.5 font-mono text-[12px] tracking-[0.5px]">
          <NavLink to="/" end className={navClass}>Home</NavLink>
          <NavLink to="/collections" className={navClass}>Collections</NavLink>
          <NavLink to="/where-did-the-money-go" className={navClass}>Findings</NavLink>
        </nav>
      </Container>
    </header>
  );
}
