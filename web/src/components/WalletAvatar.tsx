import { useState } from "react";
import type { CSSProperties } from "react";
import { walletName, hasWalletName, walletAvatar, useWalletIdentities } from "@/data/identities";

function identicon(addr: string): CSSProperties {
  const h = addr.toLowerCase().replace(/^0x/, "").padEnd(18, "0");
  const seg = (i: number) => parseInt(h.slice(i, i + 6), 16);
  const hue1 = seg(0) % 360, hue2 = seg(6) % 360, ang = seg(12) % 360;
  return { background: `linear-gradient(${ang}deg, hsl(${hue1} 68% 56%), hsl(${hue2} 66% 42%))` };
}

export default function WalletAvatar({ addr, size = 26 }: { addr: string; size?: number }) {
  const [failed, setFailed] = useState(false);
  useWalletIdentities();
  const name = hasWalletName(addr) ? walletName(addr) : null;
  const isEns = !!name && name.toLowerCase().endsWith(".eth");
  const style = { width: size, height: size, flex: `0 0 ${size}px` };
  const pfp = walletAvatar(addr);
  const src = pfp
    ? pfp
    : isEns
      ? `https://metadata.ens.domains/mainnet/avatar/${encodeURIComponent(name!)}`
      : null;
  if (src && !failed) {
    return (
      <img src={src} alt="" loading="lazy" onError={() => setFailed(true)}
           className="rounded-full object-cover ring-1 ring-line" style={style} />
    );
  }
  return <div aria-hidden className="rounded-full ring-1 ring-line" style={{ ...style, ...identicon(addr) }} />;
}
