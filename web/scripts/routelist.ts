import { collections } from "@/data/bundled";

export interface Route {
  url: string;
  title: string;
  desc: string;
  priority: string;
}

export function buildRoutes(): Route[] {
  const routes: Route[] = [
    {
      url: "/",
      title: "metazoonfts.com · MetaZoo NFT losses, on-chain",
      desc: "On-chain evidence of the MetaZoo NFT collapse: holder losses, MetaZoo's take, and the ETH trail to Steve Aoki.",
      priority: "1.0",
    },
    {
      url: "/collections",
      title: "The Collections · every MetaZoo NFT drop, ranked · metazoonfts.com",
      desc: "All ten MetaZoo NFT collections ranked by on-chain secondary volume: mints, mint revenue, royalties, and floor.",
      priority: "0.8",
    },
    {
      url: "/where-did-the-money-go",
      title: "Findings · where did the money go? · metazoonfts.com",
      desc: "The full on-chain money trail: MetaZoo treasury → Aoki → blue-chip NFTs, and insider cash-out.",
      priority: "0.9",
    },
  ];

  for (const c of collections) {
    routes.push({
      url: `/collections/${c.collection}`,
      title: `${c.name} · losses & holders · metazoonfts.com`,
      desc: `${c.name}: on-chain mints, secondary volume, MetaZoo royalties, and the holders who lost the most.`,
      priority: "0.7",
    });
  }
  return routes;
}
