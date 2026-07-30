import { cpSync, existsSync, rmSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC = join(__dirname, "..", "..", "site", "data");
const DEST = join(__dirname, "..", "public", "data");

if (!existsSync(SRC)) {
  console.error(
    "\n[build-data] site/data not found.\n" +
      "Run the pipeline build first, from the repo root:\n" +
      "    python -m scripts.build_site_data\n",
  );
  process.exit(1);
}
rmSync(DEST, { recursive: true, force: true });
cpSync(SRC, DEST, { recursive: true });
console.log(`[build-data] copied site/data -> web/public/data`);

const MODELS_SRC = join(__dirname, "..", "..", "data", "media", "sandbox3d");
const MODELS_DEST = join(__dirname, "..", "public", "sandbox3d");
rmSync(MODELS_DEST, { recursive: true, force: true });
const wanted = JSON.parse(readFileSync(join(SRC, "sandbox3d.json"), "utf8"))
  .map((e) => e.model.replace(/^\/sandbox3d\//, ""));
if (wanted.length) {
  mkdirSync(MODELS_DEST, { recursive: true });
  const missing = [];
  let copied = 0;
  for (const f of wanted) {
    const src = join(MODELS_SRC, f);
    if (existsSync(src)) { cpSync(src, join(MODELS_DEST, f)); copied++; } else missing.push(f);
  }
  console.log(`[build-data] copied ${copied}/${wanted.length} sandbox model(s) -> web/public/sandbox3d`);
  if (missing.length)
    console.warn(`[build-data] MISSING models (will 404): ${missing.join(", ")} — run fetch_token_media --sandbox-only`);
}
