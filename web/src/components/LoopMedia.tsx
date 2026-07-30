import { useState } from "react";

export default function LoopMedia({ image, video, alt, className }:
  { image?: string | null; video?: string | null; alt: string; className?: string }) {
  const [imgFailed, setImgFailed] = useState(false);
  const [vidFailed, setVidFailed] = useState(false);

  if (video && !vidFailed) {
    return (
      <video src={video} poster={image ?? undefined} autoPlay loop muted playsInline
             preload="metadata" aria-label={alt} className={className}
             onError={() => setVidFailed(true)} />
    );
  }
  if (image && !imgFailed) {
    return (
      <img src={image} alt={alt} loading="lazy" className={className}
           onError={() => setImgFailed(true)} />
    );
  }
  return null;
}
