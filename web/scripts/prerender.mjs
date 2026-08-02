import { readFileSync, writeFileSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const DIST = join(ROOT, "dist");
const SITE_DATA = join(ROOT, "..", "site", "data");
const SITE = "https://metazoonfts.com";

const { render, compactUsd, compactUsdDown } = await import(
  pathToFileURL(join(DIST, "server", "entry-server.js")).href
);

const template = readFileSync(join(DIST, "index.html"), "utf8");
const collections = JSON.parse(
  readFileSync(join(SITE_DATA, "collections.json"), "utf8"),
);
const summary = JSON.parse(readFileSync(join(SITE_DATA, "summary.json"), "utf8"));

const ogImageAlt =
  `MetaZoo raised ${compactUsd(summary.total_mint_revenue_usd)}. ` +
  `Holders lost ${compactUsdDown(summary.total_loss_usd)}.`;

const escapeHtml = (s) =>
  String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

function buildRoutes() {
  const routes = [
    {
      url: "/",
      title: "MetaZoo NFTs",
      desc: "Check your wallet profit & loss and see how you rank.",
      priority: "1.0",
    },
    {
      url: "/collections",
      title: "MetaZoo NFT Collections",
      desc: "Every contract MetaZoo minted, ranked by its volume that moved through the secondary markets.",
      priority: "0.8",
    },
    {
      url: "/where-did-the-money-go",
      title: "Findings · where did the money go?",
      desc: "One of the great MetaZoo mysteries. Using the power of the blockchain, we're able to reconstruct the flow of money from public transactions.",
      priority: "0.9",
    },
  ];

  for (const c of collections) {
    routes.push({
      url: `/collections/${c.collection}`,
      title: `${c.name}`,
      desc: `See the collection's tokens, holders, overview, and utility.`,
      priority: "0.7",
    });
  }
  return routes;
}

function pageFor(route) {
  const appHtml = render(route.url);
  const title = escapeHtml(route.title);
  const desc = escapeHtml(route.desc);
  const canonical = `${SITE}${route.url}`;

  return template
    .replace(/<title>[\s\S]*?<\/title>/, `<title>${title}</title>`)
    .replace(
      /<meta\s+name="description"[^>]*>/,
      `<meta name="description" content="${desc}" />`,
    )
    .replace(
      /<meta\s+property="og:title"[^>]*>/,
      `<meta property="og:title" content="${title}" />`,
    )
    .replace(
      /<meta\s+property="og:description"[^>]*>/,
      `<meta property="og:description" content="${desc}" />`,
    )
    .replace(
      /<meta\s+property="og:url"[^>]*>/,
      `<meta property="og:url" content="${canonical}" />\n    <link rel="canonical" href="${canonical}" />`,
    )
    .replace(
      /<meta\s+property="og:image:alt"[^>]*>/,
      `<meta property="og:image:alt" content="${escapeHtml(ogImageAlt)}" />`,
    )
    .replace('<div id="root"></div>', `<div id="root">${appHtml}</div>`);
}

function outPath(url) {
  if (url === "/") return join(DIST, "index.html");
  return join(DIST, url.replace(/^\//, ""), "index.html");
}

const routes = buildRoutes();
for (const route of routes) {
  const file = outPath(route.url);
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, pageFor(route), "utf8");
}

writeFileSync(
  join(DIST, "404.html"),
  pageFor({
    url: "/__not_found__",
    title: "404 · Not on the ledger · metazoonfts.com",
    desc: "That page isn't part of the archive.",
  }),
  "utf8",
);

const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${routes
  .map(
    (r) =>
      `  <url><loc>${SITE}${r.url}</loc><priority>${r.priority}</priority></url>`,
  )
  .join("\n")}
</urlset>
`;
writeFileSync(join(DIST, "sitemap.xml"), sitemap, "utf8");

rmSync(join(DIST, "server"), { recursive: true, force: true });

console.log(
  `prerendered ${routes.length} routes → dist/ (+ sitemap.xml, ${routes.length} urls)`,
);
