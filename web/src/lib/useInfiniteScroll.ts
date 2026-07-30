import { useCallback, useRef, useState } from "react";

export default function useInfiniteScroll(pageSize: number) {
  const [shown, setShown] = useState(pageSize);
  const io = useRef<IntersectionObserver | null>(null);

  const reset = useCallback(() => setShown(pageSize), [pageSize]);

  const sentinelRef = useCallback((el: HTMLDivElement | null) => {
    io.current?.disconnect();
    io.current = null;
    if (el && typeof IntersectionObserver !== "undefined") {
      io.current = new IntersectionObserver((entries) => {
        if (entries.some((e) => e.isIntersecting)) setShown((n) => n + pageSize);
      }, { rootMargin: "600px" });
      io.current.observe(el);
    }
  }, [pageSize]);

  return { shown, reset, sentinelRef };
}
