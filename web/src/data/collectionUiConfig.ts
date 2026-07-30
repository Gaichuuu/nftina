export const DEFAULT_TABS = ["Tokens", "Holders", "Overview"] as const;

export type CollectionUi = {
  tabs?: string[];
  showFilter?: boolean;
  hideLossPct?: boolean;
  floorLabel?: string;
  showcase3d?: boolean;
};

export const COLLECTION_UI: Record<string, CollectionUi> = {
  genesis_reissue_1155: { showFilter: false },
  valentines: { showFilter: false, hideLossPct: true },
  wilderness: { showFilter: false, hideLossPct: true },
  tournament_prizes: { showFilter: false },
  sandbox: { tabs: ["Tokens", "Overview"], floorLabel: "off-chain", showcase3d: true },
};

export function tabsFor(slug: string, hasUtility = false): string[] {
  const tabs = COLLECTION_UI[slug]?.tabs ?? [...DEFAULT_TABS];
  return hasUtility ? [...tabs, "Utility"] : [...tabs];
}
export function showFilterFor(slug: string): boolean | undefined {
  return COLLECTION_UI[slug]?.showFilter;
}
export function hideLossPctFor(slug: string): boolean {
  return COLLECTION_UI[slug]?.hideLossPct ?? false;
}
export function floorLabelFor(slug: string): string | undefined {
  return COLLECTION_UI[slug]?.floorLabel;
}
export function isShowcase3d(slug: string): boolean {
  return COLLECTION_UI[slug]?.showcase3d ?? false;
}
