import Container from "@/components/Container";
import { summary } from "@/data/bundled";
import { longDate } from "@/lib/format";

const SNAPSHOT = summary.generated_at ? longDate(summary.generated_at) : null;

export default function Footer() {
  // const year = new Date().getFullYear();
  return (
    <footer className="border-t-2 py-5 font-mono text-[11px] leading-[1.7] text-muted"
            style={{ borderColor: "var(--color-hypeA)", background: "#080610" }}>
      <Container>
        Figures are estimates from public on-chain data captured as a snapshot{SNAPSHOT ? ` on ${SNAPSHOT}` : ""}. 
      </Container>
    </footer>
  );
}
