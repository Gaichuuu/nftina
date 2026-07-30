import { Summary, Collection, VolumeSeries, Findings, CollectionContent, Sandbox3D, UsdAudit } from "./schemas";
import summaryJson from "sitedata/summary.json";
import collectionsJson from "sitedata/collections.json";
import volumeJson from "sitedata/volume_series.json";
import findingsJson from "sitedata/findings.json";
import sandbox3dJson from "sitedata/sandbox3d.json";
import usdAuditJson from "sitedata/usd_audit.json";
import coinStripJson from "sitedata/coin_strip.json";
import c_genesis_2021 from "sitedata/collections/genesis_2021/content.json";
import c_genesis_reissue_1155 from "sitedata/collections/genesis_reissue_1155/content.json";
import c_coin_tokens from "sitedata/collections/coin_tokens/content.json";
import c_beasties_s1 from "sitedata/collections/beasties_s1/content.json";
import c_pfp_2 from "sitedata/collections/pfp_2/content.json";
import c_valentines from "sitedata/collections/valentines/content.json";
import c_wilderness from "sitedata/collections/wilderness/content.json";
import c_tournament_prizes from "sitedata/collections/tournament_prizes/content.json";
import c_mothman_1of1 from "sitedata/collections/mothman_1of1/content.json";
import c_sandbox from "sitedata/collections/sandbox/content.json";
import { z } from "zod";

export const summary = Summary.parse(summaryJson);
export const collections = z.array(Collection).parse(collectionsJson);
export const volume = VolumeSeries.parse(volumeJson);
export const findings = Findings.parse(findingsJson);
export const sandbox3d = z.array(Sandbox3D).parse(sandbox3dJson);
export const usdAudit = UsdAudit.parse(usdAuditJson);
export const coinStrip = z.array(z.object({ token_id: z.string(), image: z.string() }))
  .parse(coinStripJson);

export const SLUGS = collections.map((c) => c.collection);

export function collectionBySlug(slug: string) { return collections.find((c) => c.collection === slug); }

export const collectionNames: Record<string, string> =
  Object.fromEntries(collections.map((c) => [c.collection, c.name]));

const CONTENT: Record<string, unknown> = {
  genesis_2021: c_genesis_2021, genesis_reissue_1155: c_genesis_reissue_1155,
  coin_tokens: c_coin_tokens, beasties_s1: c_beasties_s1, pfp_2: c_pfp_2,
  valentines: c_valentines, wilderness: c_wilderness, tournament_prizes: c_tournament_prizes,
  mothman_1of1: c_mothman_1of1, sandbox: c_sandbox,
};
export function contentFor(slug: string) {
  return CollectionContent.parse(CONTENT[slug] ??
    { overview: [], utility: [] });
}

