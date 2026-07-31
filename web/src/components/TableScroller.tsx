import type { ReactNode } from "react";

export default function TableScroller({ children, className = "" }:
  { children: ReactNode; className?: string }) {
  return (
    <div className={`overflow-x-auto rounded-md border border-line max-sm:-mx-5
                     max-sm:rounded-none max-sm:border-x-0 ${className}`}>
      {children}
    </div>
  );
}
