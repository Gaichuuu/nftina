import { sandbox3d } from "@/data/bundled";

export const MODEL_LIMIT_BYTES = 4_000_000;

export const MODEL_POOL = (() => {
  const small = sandbox3d.filter((a) => (a.model_bytes ?? Infinity) <= MODEL_LIMIT_BYTES);
  return small.length ? small : sandbox3d;
})();

export type Model3d = (typeof MODEL_POOL)[number];

export const DEFAULT_MODEL: Model3d | undefined =
  MODEL_POOL.find((a) => a.name.toLowerCase().includes("space penguins")) ?? MODEL_POOL[0];

export function randomModel(): Model3d | null {
  return MODEL_POOL.length ? MODEL_POOL[Math.floor(Math.random() * MODEL_POOL.length)] : null;
}
