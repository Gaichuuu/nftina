import { useEffect, useState } from "react";
import { DEFAULT_MODEL, randomModel, type Model3d } from "@/lib/heroModel";
import ModelViewer from "./ModelViewer";

export default function RandomModel() {
  const [pick, setPick] = useState<Model3d | null>(null);
  useEffect(() => { setPick(randomModel()); }, []);
  if (pick) {
    return <ModelViewer src={pick.model} poster={pick.image ?? undefined} alt={pick.name}
                        randomAnimation />;
  }
  return DEFAULT_MODEL?.image
    ? <img src={DEFAULT_MODEL.image} alt={DEFAULT_MODEL.name}
           className="h-full w-full object-contain" />
    : null;
}
