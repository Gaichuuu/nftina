import { Fragment } from "react";
import { etherscanAddr, etherscanTx, shortAddr } from "@/lib/format";
import ExternalIcon from "./ExternalIcon";

const FULL_ADDR = /^0x[0-9a-fA-F]{40}$/;
const HEX_REF = /(0x[0-9a-fA-F]{64}|0x[0-9a-fA-F]{40})(?![0-9a-fA-F])/g;

const linkCls = "font-mono text-dim transition-colors hover:text-hypeA";

export function AddrLink({ addr, className = "" }: { addr: string; className?: string }) {
  if (!FULL_ADDR.test(addr)) {
    return <span className={`break-all font-mono text-muted ${className}`}>{addr}</span>;
  }
  return (
    <a href={etherscanAddr(addr)} target="_blank" rel="noopener noreferrer"
       title="View on Etherscan" className={`break-all ${linkCls} ${className}`}>
      {addr}<ExternalIcon />
    </a>
  );
}

export function LinkedText({ text }: { text: string }) {
  const parts = text.split(HEX_REF);
  return (
    <>
      {parts.map((p, i) => {
        if (i % 2 === 0) return <Fragment key={i}>{p}</Fragment>;
        const isTx = p.length === 66;
        return (
          <a key={i} href={isTx ? etherscanTx(p) : etherscanAddr(p)} target="_blank"
             rel="noopener noreferrer" title={`${p} · view on Etherscan`}
             className={linkCls}>
            {shortAddr(p)}<ExternalIcon />
          </a>
        );
      })}
    </>
  );
}
