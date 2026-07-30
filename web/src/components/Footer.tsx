import Container from "@/components/Container";
import { summary } from "@/data/bundled";

const SNAPSHOT = summary.generated_at
  ? new Date(summary.generated_at).toLocaleDateString("en-US",
      { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" })
  : null;

export default function Footer() {
  // const year = new Date().getFullYear();
  return (
    <footer className="border-t-2 py-5 font-mono text-[11px] leading-relaxed text-muted"
            style={{ borderColor: "var(--color-hypeA)", background: "#080610" }}>
      <Container>
        Figures are estimates from public on-chain data captured as a snapshot{SNAPSHOT ? ` on ${SNAPSHOT}` : ""}. 
      </Container>
    </footer>
  );
}
