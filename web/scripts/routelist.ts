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
      title: "MetaZoo NFTs",
      desc: "Check your wallet's MetaZoo NFT profit & loss report.",
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
