import type { ReactNode } from "react";

export default function Container(
  { children, narrow = false, pad = true, className = "" }:
  { children: ReactNode; narrow?: boolean; pad?: boolean; className?: string }) {
  return (
    <div className={`mx-auto w-full ${pad ? "px-5 sm:px-8" : ""} ${narrow ? "max-w-285" : "max-w-330"} ${className}`}>
      {children}
    </div>
  );
}
