export default function ExternalIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 12 12" aria-hidden="true" fill="none" stroke="currentColor"
         strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"
         className={`ml-[0.3em] inline-block h-[0.85em] w-[0.85em] shrink-0 align-[-0.05em] opacity-70 ${className}`}>
      <path d="M7 1.5h3.5V5M10.5 1.5 5.5 6.5M9 7.5v2.25a.75.75 0 0 1-.75.75h-6a.75.75 0 0 1-.75-.75v-6a.75.75 0 0 1 .75-.75H4.5" />
    </svg>
  );
}
