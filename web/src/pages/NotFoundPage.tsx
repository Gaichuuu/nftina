import { Link } from "react-router-dom";
import Container from "@/components/Container";

export default function NotFoundPage() {
  return (
    <section aria-label="404">
      <Container className="py-24">
        <h1 className="text-[40px] font-black leading-none tracking-[-0.03em] text-ink sm:text-[52px]">
          Not on the mint list.
        </h1>
        <p className="mt-4 text-[15px] leading-[1.6] text-dim">
          This page does not exist. The losses, however, are real.
        </p>
        <Link to="/" className="hype-btn mt-8 inline-block px-7.5 py-3.5 text-[15px] no-underline
                                hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(255,92,240,.28)]">
          ← Back to the wreckage
        </Link>
      </Container>
    </section>
  );
}
