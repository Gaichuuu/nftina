import { z } from "zod";

export const Collection = z.object({
  collection: z.string(), name: z.string(), contract: z.string(), standard: z.string(),
  total_transfers: z.number(), total_mints: z.number(), unique_minters: z.number(),
  mint_revenue_eth: z.number(), mint_revenue_usd: z.number(), secondary_sales: z.number(),
  secondary_volume_eth: z.number(), royalty_eth: z.number(), floor_eth: z.number(),
  include_in_loss_calc: z.boolean(), floor_usd: z.number(),
  secondary_volume_usd: z.number().optional(), royalty_usd: z.number().optional(),
  loss_pct: z.number().nullable().optional(),
  image: z.string().nullable().optional(),
  video: z.string().nullable().optional(),
});
export type Collection = z.infer<typeof Collection>;

export const Sandbox3D = z.object({
  token_id: z.string(), name: z.string(),
  model: z.string(), image: z.string().nullable(),
  model_bytes: z.number().nullable().optional(),
  supply: z.number().nullable().optional(),
});
export type Sandbox3D = z.infer<typeof Sandbox3D>;

export const Summary = z.object({
  collections_count: z.number(), total_wallets: z.number(), total_spent_eth: z.number(),
  total_mint_revenue_eth: z.number(), total_mint_revenue_usd: z.number(),
  secondary_volume_eth: z.number(), royalties_to_metazoo_eth: z.number(),
  realized_gains_eth: z.number(), realized_losses_eth: z.number(),
  unrealized_loss_eth: z.number(), total_loss_eth: z.number(), wallets_net_loss: z.number(),
  total_loss_usd: z.number(), unrealized_loss_usd: z.number(), eth_price_usd: z.number(),
  generated_at: z.string().optional(),
}).passthrough();
export type Summary = z.infer<typeof Summary>;

const Point = z.object({ month: z.string(), eth: z.number(), usd: z.number() });
export const VolumeSeries = z.object({
  ecosystem: z.array(Point), by_collection: z.record(z.array(Point)),
});
export type VolumeSeries = z.infer<typeof VolumeSeries>;

export const HolderEntry = z.object({
  wallet: z.string(),
  tokens_held: z.number(), tokens_bought: z.number(), tokens_sold: z.number(),
  unrealized_loss: z.number(), unrealized_loss_usd: z.number(),
  realized_pnl_eth: z.number(), realized_pnl_usd: z.number(),
  net_pnl_eth: z.number(), net_pnl_usd: z.number(),
  eth_spent: z.number(), eth_received: z.number(), metazoo: z.boolean(),
  tokens_minted: z.number().optional(),
  tokens_received: z.number().optional(), tokens_sent: z.number().optional(),
  gas_spent_eth: z.number().optional(), gas_spent_usd: z.number().optional(),
  all_in_net_usd: z.number().optional(),
});
export type HolderEntry = z.infer<typeof HolderEntry>;
export const Holders = z.object({ holders: z.array(HolderEntry) });
export type Holders = z.infer<typeof Holders>;

export const LedgerRow = z.object({
  date: z.string(), eth: z.number(), usd: z.number(), recipient: z.string(),
  recipient_addr: z.string(), kind: z.enum(["aoki", "aoki_offchain", "aoki_inkind", "insider", "splitter"]), note: z.string(),
  endpoint: z.string().optional(),
});
export type LedgerRow = z.infer<typeof LedgerRow>;
export const TopItem = z.object({
  name: z.string(), token_id: z.string(), eth: z.number(), usd: z.number(),
  date: z.string(), marketplace: z.string(),
  contract: z.string().optional(), image: z.string().nullable().optional(),
});
export const BlueChip = z.object({
  contract: z.string(), name: z.string(), purchases: z.number(),
  eth: z.number(), usd: z.number(),
  image: z.string().nullable().optional(),
  held_now: z.number().nullable().optional(),
  avg_paid_eth: z.number().nullable().optional(),
  floor_eth: z.number().nullable().optional(),
  loss_pct: z.number().nullable().optional(),
});
export type TopItem = z.infer<typeof TopItem>;
export const FlipperRow = z.object({
  wallet: z.string(), label: z.string().nullable(), ens: z.string().nullable(),
  ens_verified: z.boolean(), eth_spent: z.number(), eth_received: z.number(),
  realized_pnl_eth: z.number(), realized_pnl_usd: z.number(), tokens_held: z.number(),
});
export type FlipperRow = z.infer<typeof FlipperRow>;
export const Flippers = z.object({
  total_gains_eth: z.number(), total_gains_usd: z.number(),
  realized_losses_eth: z.number(), count_profitable: z.number(),
  identified_in_top: z.number(), top: z.array(FlipperRow),
});
export type Flippers = z.infer<typeof Flippers>;

export const Findings = z.object({
  legs: z.object({ secondary_volume_eth: z.number(), secondary_volume_usd: z.number(),
    royalties_eth: z.number(), royalties_usd: z.number(),
    aoki_eth: z.number(), aoki_usd: z.number(),
    insider_eth: z.number(), insider_usd: z.number(), eth_price_usd: z.number() }),
  flippers: Flippers,
  payout_ledger: z.array(LedgerRow),
  acquisitions: z.object({ total_eth: z.number(), total_usd: z.number(), total_purchases: z.number(),
    by_collection: z.array(BlueChip),
    underwater: z.array(BlueChip).optional(),
    top_examples: z.array(TopItem).optional(),
    top_items: z.array(TopItem) }),
  insider: z.object({ eth: z.number(), exchange: z.string(), note: z.string() }),
  pfp2_offchain_revenue_usd: z.number().optional(),
});
export type Findings = z.infer<typeof Findings>;

export const TokenRow = z.object({
  token_id: z.string(), name: z.string().nullable(), image: z.string().nullable(),
  type: z.string().nullable().optional(),
  last_paid_eth: z.number(), last_paid_date: z.string().nullable(),
  last_paid_usd: z.number(), floor_eth: z.number(), floor_usd: z.number(),
  contract: z.string().nullable().optional(),
  supply: z.number().nullable().optional(),
  video: z.string().nullable().optional(),
});
export type TokenRow = z.infer<typeof TokenRow>;

export const OffChainBasis = z.object({
  unit_cost_usd: z.number(),
  unit_label: z.string(),
  note: z.string(),
  floor_usd: z.number(),
  loss_pct: z.number(),
});
export const UtilityProduct = z.object({
  id: z.string(),
  name: z.string(),
  price_usd: z.number().nullable().optional(),
  price_eth: z.number().nullable().optional(),
  note: z.string(),
  image: z.string().nullable().optional(),
});
export type UtilityProduct = z.infer<typeof UtilityProduct>;
export const PrimarySale = z.object({ label: z.string(), sub: z.string().optional() });
export type PrimarySale = z.infer<typeof PrimarySale>;
export const CollectionContent = z.object({
  overview: z.array(z.string()),
  utility: z.array(UtilityProduct),
  off_chain_basis: OffChainBasis.optional(),
  primary_sale: PrimarySale.optional(),
  overview_image: z.string().nullable().optional(),
  overview_image_caption: z.string().nullable().optional(),
});
export type CollectionContent = z.infer<typeof CollectionContent>;

export const WalletRow = z.object({
  wallet: z.string(), eth_spent: z.number(), eth_received: z.number(),
  realized_pnl_eth: z.number(), realized_loss: z.number(), unrealized_loss: z.number(),
  tokens_held: z.number(), net_pnl_eth: z.number(), loss_rank: z.number().nullable(),
  net_pnl_usd: z.number().optional(),
  realized_pnl_usd: z.number().optional(), unrealized_loss_usd: z.number().optional(),
  offchain_cost_usd: z.number().optional(), all_in_net_usd: z.number().optional(),
});
export type WalletRow = z.infer<typeof WalletRow>;

const UsdClass = z.object({ eth: z.number(), usd: z.number() });
export const UsdAudit = z.object({
  headline: z.object({
    received_eth: z.number(), received_usd_at_receipt: z.number(),
    paid_eth: z.number(), paid_usd_at_spend: z.number(),
    residual_eth: z.number(),
    gas_eth: z.number(), gas_usd_at_spend: z.number(),
    still_held_eth: z.number(), still_held_usd_now: z.number(),
    reconciles_eth: z.number(),
    depreciation_gap_usd: z.number(),
  }),
  by_class: z.object({ in: z.record(z.string(), UsdClass), out: z.record(z.string(), UsdClass) }),
  monthly: z.array(z.object({ month: z.string(), eth_balance: z.number(), usd_mark: z.number() })),
  method: z.object({ wallets: z.array(z.string()), valuation: z.string(),
                     caveats: z.array(z.string()) }),
}).nullable();
export type UsdAudit = z.infer<typeof UsdAudit>;
