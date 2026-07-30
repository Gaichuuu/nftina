export const DEFAULT_TABS = ["Tokens", "Holders", "Overview"] as const;

export type CollectionUi = {
  tabs?: string[];
  showFilter?: boolean;
};

export const COLLECTION_UI: Record<string, CollectionUi> = {
  genesis_reissue_1155: { showFilter: false },
  valentines: { tabs: ["Tokens", "Holders", "Overview"], showFilter: false },
  wilderness: { tabs: ["Tokens", "Holders", "Overview"], showFilter: false },
  tournament_prizes: { showFilter: false },
  sandbox: { tabs: ["Tokens", "Overview"] },
};

export function tabsFor(slug: string, hasUtility = false): string[] {
  const tabs = COLLECTION_UI[slug]?.tabs ?? [...DEFAULT_TABS];
  return hasUtility ? [...tabs, "Utility"] : [...tabs];
}
export function showFilterFor(slug: string): boolean | undefined {
  return COLLECTION_UI[slug]?.showFilter;
}
