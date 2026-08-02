import { useState } from "react";
import { cdnResized } from "@/lib/format";

export default function LoopMedia({ image, video, alt, className, width }:
  { image?: string | null; video?: string | null; alt: string; className?: string;
    width?: number }) {
  const [imgFailed, setImgFailed] = useState(false);
  const [vidFailed, setVidFailed] = useState(false);
  const img = image && width ? cdnResized(image, width) : image;

  if (video && !vidFailed) {
    return (
      <video src={video} poster={img ?? undefined} autoPlay loop muted playsInline
             preload="metadata" aria-label={alt} className={className}
             onError={() => setVidFailed(true)} />
    );
  }
  if (img && !imgFailed) {
    return (
      <img src={img} alt={alt} loading="lazy" className={className}
           onError={() => setImgFailed(true)} />
    );
  }
  return null;
}
