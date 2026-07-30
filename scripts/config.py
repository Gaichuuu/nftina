"""
MetaZoo NFT Research — Contract Registry & Configuration
---------------------------------------------------------
Updated with full collection inventory based on research:
- Mintable.app pre-Genesis drops confirmed as official MetaZoo (March 2021)
- Valentines confirmed as on-chain ERC-1155 (ticker: MZV)
- Beasties split into Series 1 and Series 2
- Tournament 1/1 prize NFTs documented separately
- HiROQUEST reclassified as Aoki-adjacent, not MetaZoo-issued
- Sandbox characters confirmed (Mothman, Frogman, Space Penguins)
"""
import os

# ---------------------------------------------------------------------------
# NFT Collections
# ---------------------------------------------------------------------------
# Each entry: address, standard (erc721/erc1155/imx), name, supply,
#             mint_date, notes, include_in_loss_calc (default True)

CONTRACTS = {

    # -----------------------------------------------------------------------
    # MINTABLE / IMMUTABLE X (pre-OpenSea, official MetaZoo)
    # -----------------------------------------------------------------------
    # These were sold from the official @MetaZooGames Twitter account on
    # Mintable.app, which used Immutable X (layer-2), NOT mainnet Ethereum.
    # Confirmed drops:
    #   - Squonk Baby NFT: tweeted Mar 9, 2021; 25 available; $0.99 starting bid
    #   - River Dino NFT:  tweeted Mar 16, 2021; $4.99 each
    #   mintable.app/store/MetaZoo-Games-MetaZoo-Games-NFT-Store/2da0a8a1...
    "mintable_early": {
        "address":   "0x8c5acf6dbd24c66e6fd44d4a4c3d7a2d955aaad2",  # Mintable Gasless Store (shared)
        "standard":  "erc721",   # shared Mintable store
        "name":      "MetaZoo Early Drops (Mintable Gasless Store)",
        "supply":    None,        # subset of the shared store
        "mint_date": "2021-03-09",
        "notes":     "Squonk Baby ($0.99, 25) + River Dino ($4.99) etc., lazy-minted in the "
                     "shared Mintable Gasless Store (0x8c5acf6d…) on Ethereum L1. The prior "
                     "'IMX L2 / not on Etherscan' AND 'same contract as genesis' assumptions "
                     "were BOTH wrong (F14). Tokens fetched via fetch_shared (distributor "
                     "0x3dd341…, creator-encoded IDs; article F26). Primary itself is sub-$5 "
                     "fiat (off-chain, 0 on-chain mint value) — but NOT economically negligible "
                     "overall (Plan 5/F27): 385 creator-encoded tokens (352 MZG-classified, 33 "
                     "unresolved/no-name metadata), 148 secondary sales / 134.85 ETH validated "
                     "non-phantom volume via validate_sales (50 sales >=1 ETH, 0 phantom).",
        "shared": True,                  # shared Mintable store
        "distributor": "0x3dd341664b2ffeedf9be108d4fa926dedfa9a0d6",
        "creator_encoded": True,
        "merge_into": "genesis_2021",
        "include_in_loss_calc": True,
    },

    # -----------------------------------------------------------------------
    # GENESIS 2021 (OpenSea / mainnet Ethereum)
    # -----------------------------------------------------------------------
    "genesis_2021": {
        # OWN dedicated ERC-721 contract (OpenSea slug "metazoo-games"),
        # name()='MetaZoo Games', symbol()='MetaZoo Games NFT Store', ERC-721, creator
        # 0x3dd34166… (Mintable deployer that also funded MetaZoo deployer 0x77b9…).
        # NOT the Mintable Gasless Store (that's mintable_early, 0x8c5acf6d…) — separate.
        "address":   "0xa0529c325e2594dcc599ba6e39aa4d6b28834c53",
        "standard":  "erc721",
        "supply":    595,         
        "name":      "MetaZoo Genesis 2021",
        "mint_date": "2021-03-16",
        "notes":     "17 cryptid types (10–100 copies each); 16-bit pixel art; March 2021. "
                     "Holders got 2x Token NFT allowlist slots; physical serialized promo "
                     "cards sent July 2023. Dedicated ERC-721 (~595, not 875); sampled #580 "
                     "'MZG Bigfoot', #300 'MZG Piasa Bird'. Later RE-ISSUED with updated art "
                     "as ERC-1155 on OPENSTORE — see genesis_reissue_1155 (F14).",
        "include_in_loss_calc": True,
    },

    # -----------------------------------------------------------------------
    # MOTHMAN 1/1 (Sotheby's Metaverse)
    # -----------------------------------------------------------------------
    "mothman_1of1": {
        "address":   "0x01ba93514e5eb642ec63e95ef7787b0edd403add",  # token #1017 on the aoki Manifold contract
        "token_id":  "1017",
        "standard":  "erc721",
        "name":      "MetaZoo × Steve Aoki × Gal Yosef — Mothman 1/1",
        "supply":    1,
        "mint_date": "2021-10",
        "notes":     "Lot 52 of Natively Digital 1.2 (sale NFTN07), auction Oct 18–26 "
                     "2021 on Sotheby's Metaverse (first NFT sold there). "
                     "PRICE DISPUTED, ~$214k: PSA (@PSAcard) says $214,000 'at close'; "
                     "this repo previously said $214,200; a press aggregate cites "
                     "$255,278 for Aoki's 3 lots. NOT recoverable from Wayback (all 6 "
                     "lot-page snapshots are empty shells or have null price fields) — "
                     "cite as ~$214k, not a hard number. "
                     "Winner also received: 1/1 physical PSA-graded Mothman card + "
                     "100x Nightfall 1st Ed booster boxes. "
                     "Archived lot page extracted to data/evidence/sothebys_mothman_lot.md "
                     "(Wayback 20221007052622); corroboration in "
                     "data/evidence/third_party_mothman.json.",
        "include_in_loss_calc": False,   # 1/1 auction, not a public sale
    },

    # -----------------------------------------------------------------------
    # COIN TOKENS (Dutch auction)
    # -----------------------------------------------------------------------
    "coin_tokens": {
        "address":   "0x2d366be8fa4d15c289964dd4adf7be6cc5e896e8",
        "standard":  "erc721", 
        "name":      "MetaZoo Coin Tokens (MZGT)",
        "supply":    2305,         # sold/given of 5,000 total; 10 variants
        "mint_date": "2021-11-29",
        "notes":     "Dutch auction Nov 29–Dec 2 2021. "
                     "Whitelist price: 0.1 ETH. Public started at 5.0 ETH, "
                     "dropped every 15 mins (no lower than 0.3 ETH). "
                     "~408 ETH total raised (~$1.836M at ~$4,500/ETH). "
                     "Genesis holders got 2x allowlist; others 1x. "
                     "111 Blue Manta Ray given away Dec 14 via Twitch stream. "
                     "10 variants (rarest→common): Gold Mothman (100), "
                     "Double-Stamped Gold Mothman (100), Damaged Jersey Devil (100), "
                     "Blue Manta Ray (111 given away), Black Bat (169), "
                     "Silver Mothman error (200), Blank Black Bat error (200), "
                     "Bronze Salamander (275+1), Purple Jersey Devil (300), "
                     "Silver Party (750). "
                     "Tokens granted marketplace early access + VIP event access.",
        "include_in_loss_calc": True,
    },

    # -----------------------------------------------------------------------
    # TOURNAMENT PRIZE 1/1s & SHARED-STOREFRONT ENTRIES
    # -----------------------------------------------------------------------
    # Shared storefronts and per-token subsets whose economics belong to canonical
    # (whole-contract or distributor) keys.
    "tournament_prizes": {
        "address":   "0x495f947276749ce646f68ac8c248420045cb7b5e",  # OPENSTORE (shared)
        "standard":  "erc1155",
        "name":      "MetaZoo Tournament Prize NFTs (1/1s)",
        "supply":    None,         # 3 trophies (1st/2nd/3rd place)
        "mint_date": "2021-12",
        "notes":     "3 confirmed New Year's Tournament trophies (1st/2nd/3rd Place, Jan 2022). "
                     "Named 'MetaZoo Games New Years Tournament {1st,2nd,3rd} Place Trophy', "
                     "created by 0x3dd341… (Mintable store operator). Gifted; $0 primary revenue. "
                     "Fetched via fetch_shared with curated token_ids (F16 corrected).",
        "shared": True,                  # OPENSTORE storefront
        "include_in_loss_calc": False,   # gifted
        "distributor": "0x3dd341664b2ffeedf9be108d4fa926dedfa9a0d6",
        "creator_encoded": True,
        "token_ids": [
            "27964339865592756430076624915131963380151013737350423260877931219652127490049",
            "27964339865592756430076624915131963380151013737350423260877931220751639117825",
            "27964339865592756430076624915131963380151013737350423260877931221851150745601",
        ],
    },

    # -----------------------------------------------------------------------
    # VALENTINES (MZV)
    # -----------------------------------------------------------------------
    "valentines": {
        # on-chain name()='MetaZoo Valentines', symbol()='MZV', **ERC-1155** deployed by
        # MetaZoo deployer 0x77b94a55… on 2023-02-16. This contract ALSO holds the Wilderness
        # tokens (e.g. token #8 = "MetaZoo Wilderness Pinclub 2")
        "address":   "0xa986559aacf60a82fab3ef59940febea8027be0c",
        "standard":  "erc1155",
        "name":      "MetaZoo Valentines (MZV)",
        "supply":    6,           # token IDs 1–6 (F16); IDs 7–11 are Wilderness (same contract)
        "mint_date": "2022-02",
        # This whole-contract fetch (all 11 token IDs) is the canonical entry for 0xa986559a
        "valentines_token_ids": ["1", "2", "3", "4", "5", "6"],
        "notes":     "Ticker MZV confirmed via Etherscan wallet records. "
                     "ERC-1155. Tied to 2022 Valentine's Day physical chibi "
                     "mini set (Bunnyman 1/12, Squonk 10/12, Enfield Monster 5/12, "
                     "etc.). Likely free or very low cost mint. "
                     "Find contract via deployer wallet.",
        "include_in_loss_calc": True,
    },

    # -----------------------------------------------------------------------
    # BEASTIE PFPs (two separate series)
    # -----------------------------------------------------------------------
    "beasties_s1": {
        # Contract "MetaZooGamesBeasties" (token MZG), deployed by the MetaZoo: Deployer
        # EOA 0x77b9… ~2022-07-15 (matches mint_date). 
        "address":   "0x44a46fc706798e203c405667e70802e5b18a2867",
        "standard":  "erc721",
        "name":      "MetaZoo Games Beasties",   # OpenSea slug: metazoo-games-beasties; a.k.a. "PFP 1.0"
        "supply":    5000,
        "mint_date": "2022-07-15",
        "notes":     "The first PFP collection, 'MetaZoo Games Beasties' (a.k.a. PFP 1.0). "
                     "Art by Jett Yates. Blind sale — buyers didn't know which "
                     "Beastie until reveal July 22 2022 at 12pm EST. "
                     "Allow List mint: Jul 15 at 0.1 ETH (Token holders + "
                     "select A0K1VERSE members + VIPs). "
                     "Public mint: Jul 16 at 0.11 ETH. "
                     "Free mint: Jul 18 (gas only) for Token holders prior to that date. "
                     "Reveal: Jul 22 2022.",
        "include_in_loss_calc": True,
    },
    "beasties_s2": {
        "address":   None,        # PHANTOM — no separate contract exists 
        "standard":  "erc721",
        "name":      "MetaZoo Beastie PFPs — Series 2",
        "supply":    None,
        "mint_date": None,
        "notes":     "PHANTOM ENTRY (F14): a full deployer + OpenSea/Manifold sweep found NO "
                     "separate 'Beasties Series 2' contract. Only Beasties S1 (0x44a46fc7…) "
                     "exists; the actual 'second' PFP drop is pfp_2 (0xf279e4d18a…). "
                     "Retain-or-remove is a modeling decision; kept here as a documented dead end.",
        "include_in_loss_calc": False,   # no contract
    },

    # -----------------------------------------------------------------------
    # STEVE AOKI (AOKI) COLLECTION
    # -----------------------------------------------------------------------
    "aoki": {
        "address":   "0x01ba93514e5eb642ec63e95ef7787b0edd403add",
        "standard":  "erc721",
        "name":      "Steve Aoki (AOKI)",
        "supply":    None,         # ~1,100 minted; ~493 current holders
        "mint_date": "2022",
        "notes":     "Manifold ERC721Creator contract. "
                     "Includes MetaZoo Mothman #1017. "
                     "Current holder AK9NFT-Vault on OpenSea. "
                     "Floor ~0.028 ETH as of research date.",
        # Steve Aoki's OWN collection, not a MetaZoo drop: the only MetaZoo object
        # on it is the Mothman 1/1 (token #1017, tracked separately as
        # `mothman_1of1`).
        "third_party": True,
        "include_in_loss_calc": False,
    },

    # -----------------------------------------------------------------------
    # THE SANDBOX (MetaZoo/Aoki voxel characters)
    # -----------------------------------------------------------------------
    "sandbox": {
        "address":   "0xa342f5d851e866e18ff98f351f2c6637f4478db5",
        "standard":  "erc1155",
        "name":      "The Sandbox ASSETS — MetaZoo/Aoki Characters",
        "supply":    None,
        "mint_date": None,
        "notes":     "Shared Sandbox ASSETS contract (ERC-1155, mainnet). CONFIRMED MetaZoo x Steve "
                     "Aoki set of 6 (F17, owner-supplied OpenSea URLs), near-sequential token IDs "
                     "55464657…688755669011/012/014/016/017/036 = Sam Sinclair, Space Penguins, "
                     "Chupacabra, Mothman (supply 200), Loveland Frogman, White Thang. This vindicates "
                     "the ORIGINAL 'Mothman/Frogman/Space Penguins' claim — an interim 'unverified' "
                     "call was an error (only checked Aoki's WALLETS, not the contract by name; the "
                     "assets are held by BUYERS). Minter 0x7a9fe22691c811ea… is The Sandbox's SHARED "
                     "brand-minter (also mints Smurfs/Atari/REVV/Chinese Zodiac), creator-encoded in "
                     "token_id>>96 → NOT a MetaZoo filter. Royalty: NO EIP-2981; marketplaces enforce "
                     "~5%. Economics NEGLIGIBLE: only 2 of 6 ever traded (Chupacabra 0.008 ETH, Mothman "
                     "0.0045 ETH) ≈ 0.012 ETH total secondary. PRIMARY mint was a SAND sale on the "
                     "Sandbox marketplace (off our ETH pipeline). Real but immaterial to loss/flow.",
        "shared": True,                  # Sandbox ASSETS storefront
        "include_in_loss_calc": False,   # not distributed by a MetaZoo wallet
    },

    # -----------------------------------------------------------------------
    # PFP 2.0 (Manifold claim)
    # -----------------------------------------------------------------------
    "pfp_2": {
        "address":   "0xf279e4d18aa013143bb8242e0d65bcc62acbbb5a",
        "standard":  "erc721",   # confirmed ERC-721 via OpenSea
        "name":      "MetaZoo Games PFP 2.0",
        "supply":    None,        # unknown total; ranks seen up to at least #425
        "mint_date": None,        
        "notes":     "Minted via Manifold claim page: app.manifold.xyz/c/MZGPFP2 . "
                     "Manifold was MetaZoo's NFT dev/platform for effectively all "
                     "drops (see aoki entry: 'Manifold ERC721Creator contract'), so "
                     "collections may share Manifold creator-contract patterns — "
                     "a discovery lever alternative to the deployer wallet. "
                     "Get full token list + metadata + assets via tokenURI.",
        "include_in_loss_calc": True,
    },

    # -----------------------------------------------------------------------
    # WILDERNESS
    # -----------------------------------------------------------------------
    "wilderness": {
        # Wilderness tokens live INSIDE the Valentines ERC-1155 contract
        "address":   "0xa986559aacf60a82fab3ef59940febea8027be0c",  # == valentines contract
        "standard":  "erc1155",
        "name":      "MetaZoo Wilderness (Pinclub)",
        "supply":    5,           # token IDs 7–11 within the valentines contract
        "mint_date": None,
        "token_ids": ["7", "8", "9", "10", "11"],
        "notes":     "Wilderness pin-club NFTs (5 of them, token IDs 7–11) share the Valentines "
                     "contract 0xa986559a…; token #8 = 'MetaZoo Wilderness Pinclub 2'. Economics "
                     "are inside the `valentines` aggregate (negligible — ~0.4 ETH secondary "
                     "across ALL 11 tokens). Kept as a documented subset, not a separate fetch.",
        "include_in_loss_calc": False,   # shared contract with `valentines`
    },

    # Genesis 17 cryptids RE-ISSUED with updated artwork as ERC-1155 lazy-mints on the
    # OpenSea Shared Storefront (OPENSTORE), airdropped by the MetaZoo deployers
    "genesis_reissue_1155": {
        "address":   "0x495f947276749ce646f68ac8c248420045cb7b5e",  # OPENSTORE
        "standard":  "erc1155",
        "name":      "MetaZoo Genesis (re-issue, updated art)",
        "supply":    17,          # distinct cryptid token IDs distributed by MetaZoo
        "mint_date": None,
        "distributor":    "0x77b94a55684c95d59a8f56a234b6e555fc79997c",
        "creator_encoded": True,   # OpenSea storefront IDs encode creator in the top 160 bits
        "token_ids": [
            "54152608720201814221623250482272576218207376542497061489884864883794078859292",
            "54152608720201814221623250482272576218207376542497061489884864884893590487065",
            "54152608720201814221623250482272576218207376542497061489884864885993102114915",
            "54152608720201814221623250482272576218207376542497061489884864887092613742691",
            "54152608720201814221623250482272576218207376542497061489884864888192125370418",
            "54152608720201814221623250482272576218207376542497061489884864889291636998243",
            "54152608720201814221623250482272576218207376542497061489884864890391148625970",
            "54152608720201814221623250482272576218207376542497061489884864891490660253721",
            "54152608720201814221623250482272576218207376542497061489884864892590171881523",
            "54152608720201814221623250482272576218207376542497061489884864893689683509264",
            "54152608720201814221623250482272576218207376542497061489884864894789195137226",
            "54152608720201814221623250482272576218207376542497061489884864895888706764825",
            "54152608720201814221623250482272576218207376542497061489884864896988218392651",
            "54152608720201814221623250482272576218207376542497061489884864898087730020402",
            "54152608720201814221623250482272576218207376542497061489884864899187241648153",
            "54152608720201814221623250482272576218207376542497061489884864900286753275914",
            "54152608720201814221623250482272576218207376542497061489884864901386264903731",
        ],
        "notes":     "Re-issue of the Genesis 17 cryptids with updated artwork, lazy-minted on "
                     "the OpenSea Shared Storefront (OPENSTORE 0x495f9472…). On OpenSea these "
                     "surface under the 'metazoo-games-beasties' collection. Distinct from the "
                     "dedicated ERC-721 genesis_2021 (0xa0529c32…). Token-ID-filtered fetch via "
                     "scripts.fetch_shared (F16): 17 tokens, all creator==distributor 0x77b9, "
                     "airdropped (0 primary revenue). Fetch stores data/raw/genesis_reissue_1155_*.",
        "shared": True,                  # OPENSTORE storefront
        "include_in_loss_calc": True,
    },

    # -----------------------------------------------------------------------
    # AOKI-ADJACENT — Not MetaZoo-issued
    # -----------------------------------------------------------------------
    "hiroquest": {
        "address":   None,
        "standard":  "erc721",
        "name":      "HiROQUEST: Genesis (Aoki ecosystem, NOT MetaZoo-issued)",
        "supply":    None,
        "mint_date": "2022-09",
        "notes":     "Part of Aoki's A0K1VERSE/album ecosystem. "
                     "NOT a MetaZoo product. Connection: A0K1VERSE members got "
                     "allowlist access to Beastie PFP Series 1. "
                     "Include in Aoki financial web analysis but NOT in "
                     "MetaZoo loss calculations.",
        "include_in_loss_calc": False,
    },
}

# ---------------------------------------------------------------------------
# Wallets
# ---------------------------------------------------------------------------

# MetaZoo treasury / deployer wallet
METAZOO_DEPLOYER = "0xec843e7364ca9234271efc12e7626a7a9bdc5400"  # coin_tokens contract creator

# Known Aoki wallet addresses
# Find via: ENS lookup for steveaoki.eth, AOKI contract royalty recipient,
#           or media coverage where he's shared his address publicly
AOKI_WALLETS = [
    # Confirmed Aoki creator/royalty hub: minter of the AOKI
    # collection, EIP-2981 royalty recipient (10%), and the Sotheby's Mothman
    # consignor/seller.
    "0xa6d3a33a1c66083859765b9d6e407d095a908193",
    # Confirmed via Etherscan public name-tag "Steve Aoki" (@steveaoki).
    # Aoki's main NFT-trading wallet (heavy CryptoPunks/OpenSea).
    "0xe4bbcbff51e61d0d95fcc5016609ac8354b177c4",
]

# MetaZoo-controlled operational wallets (NOT Aoki). Etherscan-tagged.
# Kept as trace seeds on the MetaZoo/treasury side so hub↔these register as MetaZoo↔Aoki.
# NOTE: adding/removing a wallet here changes the flow-trace seed → re-run trace_flows.
METAZOO_WALLETS = [
    # Etherscan "MetaZoo: Deployer"; deployed MetaZooGamesBeasties (0x44a46fc7…).
    "0x77b94a55684c95d59a8f56a234b6e555fc79997c",
    # metazoodev.eth — 4th MetaZoo wallet (F14): deployed the MZOO ERC-20
    # (0xde41fa349c4e07dc93efe889f2d6c2fad96b1595, "MetaZoo"/"MZOO", 2023-03-16).
    "0x79109a93db158f16f4c8936217ce46f21ed5dc2b",
]

# The MetaZoo main deployer 0xec843e… (METAZOO_DEPLOYER) is added to the trace seed
# separately in trace_flows.main(); it need not be duplicated here.

# Aoki wallet CLUSTER — EOAs with large bidirectional ETH flow to the 0xa6d3 hub
# and shared NFT-trading behavior (CryptoPunks/OpenSea). Strong candidates but NOT
# independently proven Aoki-owned.
AOKI_HUB_EOA_CANDIDATES = [
    "0x50bb8c7c8b190fa43f085f95d1392339c935e875",  # 533 ETH pass-through (net 0); ← 200 from hub → all to 0x1b8ce… (untagged). UNPROVEN.
    # 0xe4bb… promoted to AOKI_WALLETS (Etherscan "Steve Aoki").
    # 0x77b9… moved to METAZOO_WALLETS (Etherscan "MetaZoo: Deployer").
]
# Next-hop consolidation / likely exchange-deposit endpoints:
#   0x1b8ce86b… (0x50bb sent all 534 ETH here) · 0x7be8076f… (0xe4bb sent 1469 ETH here)
# NOT Aoki wallets — contracts the hub interacted with:
#   0xb47e3cd837ddf8e4c57f05d70ab865de6e193bbb = CryptoPunks (hub SPENT ~159.9 ETH buying punks)
#   0x9521c555b6fb8d4249f699c08e3a611d3f65a4f9 = contract (~344B code, likely a Safe/proxy)

# ---------------------------------------------------------------------------
# Key Events (for timeline + tweet correlation)
# ---------------------------------------------------------------------------

TIMELINE_EVENTS = [
    # These are anchor points to correlate against Aoki tweet timestamps
    {"date": "2021-03-09", "event": "Squonk Baby NFT tweeted by @MetaZooGames on Mintable"},
    {"date": "2021-03-16", "event": "River Dino NFT + Genesis 2021 OpenSea mint"},
    {"date": "2021-10-14", "event": "Mothman 1/1 auction opens on Sotheby's Metaverse"},
    {"date": "2021-10-21", "event": "Mothman 1/1 sells for $214,200"},
    {"date": "2021-11-29", "event": "Coin Token whitelist sale opens (0.1 ETH)"},
    {"date": "2021-12-02", "event": "Coin Token public Dutch auction (5.0 ETH start)"},
    {"date": "2021-12-14", "event": "Blue Manta Ray giveaway Twitch stream"},
    {"date": "2021-12-19", "event": "Bronze Snowman 1/1 tournament prize announced"},
    {"date": "2022-02",    "event": "Valentine's Day NFT drop (MZV)"},
    {"date": "2022-07-15", "event": "Beastie PFP Series 1 allow list mint"},
    {"date": "2022-07-16", "event": "Beastie PFP Series 1 public mint"},
    {"date": "2022-07-18", "event": "Beastie PFP Series 1 free mint for Token holders"},
    {"date": "2022-07-22", "event": "Beastie PFP reveal"},
    {"date": "2022-09",    "event": "HiROQUEST Genesis NFTs (Aoki album drop)"},
    {"date": "2024-01-29", "event": "MetaZoo shuts down — Waddell Discord announcement"},
    {"date": "2024-05-20", "event": "MetaZoo Games LLC files Chapter 7 bankruptcy"},
    {"date": "2026-01",    "event": "Aoki/Kalish class action lawsuit filed"},
]

# ---------------------------------------------------------------------------
# Aoki Twitter Handles & Search Terms
# ---------------------------------------------------------------------------

AOKI_TWITTER = {
    "handle":       "steveaoki",
    "search_terms": [
        "metazoo", "MetaZoo", "beastie", "mothman", "cryptid",
        "nft drop", "mint", "web3", "A0K1VERSE", "hiroquest",
    ],
    # Date range of interest for the lawsuit (hype period)
    "search_start": "2021-01-01",
    "search_end":   "2023-01-01",
    # Archive sources for deleted tweets
    "archive_sources": [
        "https://web.archive.org",
        "https://polittwi.et",   
    ],
}

# MetaZoo official handles 
METAZOO_TWITTER = {
    "handle":      "MetaZooGames",
    "search_terms": ["nft", "mint", "aoki", "drop", "token", "beastie"],
    "search_start": "2021-01-01",
    "search_end":   "2024-01-29",
}

# ---------------------------------------------------------------------------
# Tweet record scope
# ---------------------------------------------------------------------------

# Influencers whose MetaZoo/NFT-promo tweets we pull (filtered search, live).
INFLUENCERS = ["steveaoki", "farokh", "nftwhalealert", "ivydoomkitty", "jeffreygwei"]

# MetaZoo's own / related accounts.
METAZOO_ACCOUNTS = ["metazooxyz", "metazoo_games", "metazoomarket"]

# The original @MetaZooGames is DELETED, recovered via Wayback.
METAZOO_DELETED_HANDLE = "MetaZooGames"

# Broad terms for search RECALL (filtered influencer search + Wayback deleted scan).
# Includes a0k1verse (Aoki's own club, MetaZoo-adjacent) to catch related tweets.
METAZOO_PROMO_TERMS = ["metazoo", "beastie", "mothman", "cryptid", "coin token",
                       "nightfall", "a0k1verse"]

# Tight, MetaZoo-SPECIFIC terms for the undisclosed-promo classifier PRECISION.
# Excludes a0k1verse/sandbox/hiroquest — those are Aoki's own projects, not MetaZoo,
# and counting them would overstate the MetaZoo promotion case.
METAZOO_CORE_TERMS = ["metazoo", "beastie", "mothman", "cryptid", "coin token", "nightfall"]

# Promo-window bounds for filtered searches.
PROMO_WINDOW = ("2021-01-01", "2024-06-01")

# ---------------------------------------------------------------------------
# Notable 1/1 sale
# ---------------------------------------------------------------------------

MOTHMAN_1OF1_DETAILS = {
    "platform":  "Sotheby's Metaverse",
    "sale_date": "2021-10-21",
    "sale_usd":  214200,
    "artists":   ["Steve Aoki", "Gal Yosef"],
    "notes":     "First NFT sold on Sotheby's Metaverse platform. "
                 "Winner also received physical 1/1 promo card + 100 Nightfall 1st Ed boxes.",
}

# ---------------------------------------------------------------------------
# Bankruptcy
# ---------------------------------------------------------------------------

BANKRUPTCY = {
    "case_number":   "1:24-bk-10874",
    "court":         "NY Southern Bankruptcy Court",
    "chapter":       7,
    "filed":         "2024-05-20",
    "trustee":       "Albert Togut",
    "attorney":      "Warren R. Graham, Pryor & Mandelup LLP",
    "ip_sold_for":   2_000_000,
    "buyer":         "MetaTwo Enterprises LLC",
    "new_developer": "GameQbator Labs (Redmond, WA)",
    "pacer_url":     "https://www.pacermonitor.com/public/case/53609535/MetaZoo_Games_LLC",
    "notes":         "Chapter 7 = liquidation (not restructuring). "
                     "Schedule F (unsecured creditors) has claimant names + amounts. "
                     "IP acquired by MetaTwo; relaunched 2025 with Richard Garfield.",
}

# ---------------------------------------------------------------------------
# Lawsuit
# ---------------------------------------------------------------------------

LAWSUIT = {
    "case":        "Berger v. Aoki & Kalish, No. 26-cv-20095 (S.D. Fla.)",
    "plaintiff":   "Evan Berger (individually + putative nationwide class)",
    "filed":       "2026-01",
    "defendants":  ["Steven Hiroyuki Aoki", "Matthew Kalish"],
    "claims":      "FDUTPA (Fla. Deceptive & Unfair Trade Practices Act) + negligent "
                   "misrepresentation; Count III withdrawn. Theory: undisclosed paid "
                   "promotion of MetaZoo products (physical + Coin NFTs) presented as organic; "
                   "Aoki additionally concealed his ownership stake in MetaZoo.",
    "allegation":  "Paid to promote MetaZoo NFTs without disclosing compensation; "
                   "presented as disinterested consumers while Aoki held an equity stake. "
                   "Aoki became equity partner in MetaZoo in 2021. "
                   "In 2022 Aoki stated he made more money from NFTs than 10 years of music advances.",
    # The specific pleaded payment (Amended Complaint ¶81), now cross-checked on-chain:
    "para81_payment": {
        "alleged":  "~90 ETH each to Aoki and Kalish (~$275k each at ~$3,100/ETH) shortly "
                    "after the Jan 8 2022 poker-game skit; Kalish 'by or on behalf of MetaZoo' "
                    "over two transactions.",
        "aoki_verified": {
            "tx":    "0xe8fe95242c9a8d90b63296b142aa328317d2fdc4f77c043e8cdcdf00234d78dd",
            "date":  "2022-01-11",  # 3 days after the poker game
            "eth":   89.7685,
            "from":  "0x77b94a55684c95d59a8f56a234b6e555fc79997c",  # MetaZoo Deployer #2
            "to":    "0xe4bbcbff51e61d0d95fcc5016609ac8354b177c4",  # Aoki main
            "note":  "≈$278k at $3,100/ETH — matches ¶81's Aoki leg precisely.",
        },
        "kalish_verified": None,   # NOT located on-chain; Kalish has no confirmed wallet
    },
    "damages":     "$5M+ class (CAFA); Berger individually >$150k. Treble damages possible.",
    "notes":       "Ongoing. Aoki's ¶81 ~90 ETH payment is CONFIRMED on-chain; the "
                   "Kalish parallel payment is alleged but not yet located. Whether the Aoki "
                   "transfer was promo consideration vs. a partner distribution is unproven.",
}

# ---------------------------------------------------------------------------
# ETH price snapshots (for historical USD conversion)
# ---------------------------------------------------------------------------

ETH_PRICES = {
    "2021-03-09": 1750,    # Squonk Baby NFT tweet
    "2021-03-16": 1820,    # Genesis 2021 mint
    "2021-10-14": 3600,    # Mothman auction opens
    "2021-10-21": 4000,    # Mothman auction closes
    "2021-11-15": 4300,
    # Coin-token Dutch auction window (Binance ETHUSDT daily close)
    # per-day pricing because the mint spanned 5 days of real ETH price moves.
    "2021-11-29": 4445,    # Token whitelist sale opens
    "2021-11-30": 4630,
    "2021-12-01": 4583,    # Token public Dutch auction
    "2021-12-02": 4511,
    "2021-12-03": 4216,
    "2022-02-14": 3000,    # Valentine's Day drop
    "2022-07-15": 1231,    # Beastie PFP mint (Binance close; ETH had crashed to ~$1.2k)
    "2022-07-16": 1231,
    "2022-07-22": 1326,    # MetaZoo x Aoki Sandbox assets minted (SAND ~$1.33 that day)
    "2022-09-01": 1550,    # HiROQUEST
    "2023-08-18": 1662,    # PFP 2.0 mint window (Binance close)
    "2023-08-25": 1654,
    "2024-01-29": 2300,    # MetaZoo shutdown
    "2024-05-20": 3100,    # Bankruptcy filing
    "2026-07-24": 1885,    # "today" — used to value current floor for at-purchase loss USD
}

# --- Mint price fallbacks (ETH) used when per-tx value attribution is ambiguous.

MINT_PRICES = {
    "coin_tokens": 0.1,      # whitelist 0.1 ETH; Dutch auction floor 0.3 ETH (see notes)
    "beasties_s1": 0.11,     # public mint; allowlist 0.1; free (gas-only) tier exists
}

# --- Etherscan V2 ---
ETHERSCAN_V2_API = "https://api.etherscan.io/v2/api"
ETHERSCAN_CHAIN_ID = 1

# --- Alchemy NFT API (v3) key is interpolated into the path by the client ---
ALCHEMY_NFT_BASE = "https://eth-mainnet.g.alchemy.com/nft/v3"

# Bunny CDN base for rehosted token/acquisition art (overridable for local dev).
MEDIA_CDN_BASE = os.environ.get("MEDIA_CDN_BASE", "https://gaichu.b-cdn.net/nftina")

# --- GetXAPI (verified 2026-07: base + Bearer auth + these paths; search param is `q`) ---
GETXAPI_API         = "https://api.getxapi.com"
GETXAPI_SEARCH      = "/twitter/tweet/advanced_search"

# ---------------------------------------------------------------------------
# Site collection registry
# ---------------------------------------------------------------------------
# The 10 collections the metazoonfts.com frontend renders, in display order.
# `source` decides how build_site_data.py sources each one's economics:
#   own         -> its own data/raw/<slug>_* files (analyze.py produced a collections.json entry)
#   subset      -> filter the PARENT's raw files to `token_ids` (e.g. Mothman #1017 inside `aoki`)
#   placeholder -> no on-chain data located; render an honest "unverified" page (no economics)
#   showcase    -> media-only (3D art); economics negligible/off-chain, no leaderboard
SITE_COLLECTIONS = [
    {"slug": "genesis_2021",         "name": "MetaZoo Genesis",              "source": "own"},
    {"slug": "genesis_reissue_1155", "name": "MetaZoo Genesis (re-issue)",   "source": "own"},
    {"slug": "coin_tokens",          "name": "MetaZoo Coin Tokens",          "source": "own"},
    {"slug": "beasties_s1",          "name": "MetaZoo Games Beasties",       "source": "own"},
    {"slug": "pfp_2",                "name": "MetaZoo Games PFP 2.0",        "source": "own"},
    {"slug": "valentines",           "name": "MetaZoo Valentines",           "source": "own"},
    {"slug": "wilderness",           "name": "MetaZoo Wilderness",           "source": "subset",
     "parent": "valentines", "token_ids": ["7", "8", "9", "10", "11"]},
    {"slug": "tournament_prizes",    "name": "MetaZoo Tournament Prizes",    "source": "own",
     "note": "Three gifted 1/1 New Year's Tournament trophies (1st/2nd/3rd place) on the "
             "OPENSTORE shared contract, minted by the MetaZoo/Mintable deployer 0x3dd341…. "
             "Fetched via fetch_shared; economics are minimal (gifted prizes)."},
    {"slug": "mothman_1of1",         "name": "MetaZoo Mothman 1/1",          "source": "subset",
     "parent": "aoki", "token_ids": ["1017"]},
    {"slug": "sandbox",              "name": "MetaZoo Sandbox Characters",   "source": "showcase",
     "note": "Six MetaZoo x Steve Aoki characters on The Sandbox (ERC-1155). Primary "
             "sold in SAND on the Sandbox marketplace (off the ETH pipeline); on-chain "
             "ETH secondary volume is negligible."},
]
for _c in SITE_COLLECTIONS:
    _c.setdefault("parent", None)
    _c.setdefault("token_ids", None)
    _c.setdefault("note", None)

TOKEN_FILTER_TRAITS = {
    "coin_tokens": "Type",     # 12 coin designs (e.g. "Mothman Gold", "MetaZoo Party Silver")
    "beasties_s1": "Base",     # the cryptid species (Bigfoot, Mothman, Hodag, …)
    "pfp_2": "Base",           # the PFP character/species (Yehasuri, …); values are filenames, ext-stripped
}

_SANDBOX_PREFIX = "55464657044963196816950587289035428064568320970692304673817341489"
SANDBOX_TOKEN_IDS = [_SANDBOX_PREFIX + tail for tail in
                     ["688755669011", "688755669012", "688755669014",
                      "688755669016", "688755669017", "688755669036"]]

SANDBOX_ASSET_SUPPLY = {
    _SANDBOX_PREFIX + "688755669011": 200,  # Sam Sinclair
    _SANDBOX_PREFIX + "688755669012": 200,  # Space Penguins
    _SANDBOX_PREFIX + "688755669014": 200,  # Chupacabra
    _SANDBOX_PREFIX + "688755669016": 200,  # Mothman
    _SANDBOX_PREFIX + "688755669017": 200,  # Loveland Frogman
    _SANDBOX_PREFIX + "688755669036": 50,   # White Thang
}
