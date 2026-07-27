# This file filters ETFs for a single country each time it runs (the comments below use Canada as an example)
# When this script runs, it filters ETFs using the five files "ibkr_tradeable.py, listing_age.py, low_volatility.py, remove_correlated_etfs.py, min_volume.py" in "ETF_Trading_Model\filters", and "canada.py" in "ETF_Trading_Model\countries", then appends the results to "ETF_Trading_Model\data\universe.csv"
# After building good_universe.csv, this script continues filtering the ETFs in good_universe.csv using "good_universe_filter.py" in "ETF_Trading_Model\filters", and appends the results to "ETF_Trading_Model\data\good_universe.csv"
# The country to filter can be set manually; the code includes a comment marking "countries I can change"
# Each time this script runs (each time a country is filtered), universe.csv and good_universe.csv are updated, not replaced
# This file, out_sampling.py, is not used for now

import os
import time

import pandas as pd

from countries.usa import get_us_etf_symbols
from countries.canada import get_ca_etf_symbols
from countries.uk import get_uk_etf_symbols
from countries.germany import get_de_etf_symbols
from countries.japan import get_jp_etf_symbols
from countries.australia import get_au_etf_symbols
from countries.france import get_fr_etf_symbols
from countries.netherlands import get_nl_etf_symbols
from countries.south_korea import get_kr_etf_symbols
from countries.switzerland import get_ch_etf_symbols
from countries.hong_kong import get_hk_etf_symbols
from countries.singapore import get_sg_etf_symbols
from countries.india import get_in_etf_symbols
from countries.taiwan import get_tw_etf_symbols
from countries.brazil import get_br_etf_symbols
from countries.mexico import get_mx_etf_symbols
from countries.turkey import get_tr_etf_symbols
from countries.saudi_arabia import get_sa_etf_symbols
from countries.indonesia import get_id_etf_symbols
from countries.south_africa import get_za_etf_symbols
from countries.poland import get_pl_etf_symbols
from countries.chile import get_cl_etf_symbols
from countries.israel import get_il_etf_symbols
from countries.vietnam import get_vn_etf_symbols
from filters.listing_age import passes_listing_age
from filters.min_volume import passes_min_volume
from filters.low_volatility import filter_low_volatility
from filters.remove_correlated_etfs import remove_correlated_etfs
from filters.ibkr_tradeable import filter_ibkr_tradeable
from filters.good_universe_filter import passes_good_universe

# ========== Parameter settings ==========
# Countries I can change: edit manually before each run; currently supports "United States", "Canada", "United Kingdom", "Germany", "Japan", "Australia", "France", "Netherlands", "South Korea", "Switzerland", "Hong Kong", "Singapore", "India", "Taiwan", "Brazil", "Mexico", "Turkey", "Saudi Arabia", "Indonesia", "South Africa", "Poland", "Chile", "Israel", "Vietnam"
COUNTRY = "Vietnam"

UNIVERSE_PATH = "data/universe.csv"
GOOD_UNIVERSE_PATH = "data/good_universe.csv"
REQUEST_DELAY = 0.3

# Supported countries and their corresponding symbol-fetching functions
COUNTRY_SYMBOL_FETCHERS = {
    "United States": get_us_etf_symbols,
    "Canada": get_ca_etf_symbols,
    "United Kingdom": get_uk_etf_symbols,
    "Germany": get_de_etf_symbols,
    "Japan": get_jp_etf_symbols,
    "Australia": get_au_etf_symbols,
    "France": get_fr_etf_symbols,
    "Netherlands": get_nl_etf_symbols,
    "South Korea": get_kr_etf_symbols,
    "Switzerland": get_ch_etf_symbols,
    "Hong Kong": get_hk_etf_symbols,
    "Singapore": get_sg_etf_symbols,
    "India": get_in_etf_symbols,
    "Taiwan": get_tw_etf_symbols,
    "Brazil": get_br_etf_symbols,
    "Mexico": get_mx_etf_symbols,
    "Turkey": get_tr_etf_symbols,
    "Saudi Arabia": get_sa_etf_symbols,
    "Indonesia": get_id_etf_symbols,
    "South Africa": get_za_etf_symbols,
    "Poland": get_pl_etf_symbols,
    "Chile": get_cl_etf_symbols,
    "Israel": get_il_etf_symbols,
    "Vietnam": get_vn_etf_symbols,
}


def _load_existing_csv(path: str, columns: list[str]) -> pd.DataFrame:
    """Read the existing CSV; if it doesn't exist or is empty, return an empty DataFrame with only the specified columns."""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return pd.read_csv(path)
    return pd.DataFrame(columns=columns)


def main():
    if COUNTRY not in COUNTRY_SYMBOL_FETCHERS:
        print(f"Error: unsupported country '{COUNTRY}', please check the COUNTRY setting")
        return

    print(f"===== Starting filter for country: {COUNTRY} =====")

    # Step 1: get the raw ETF symbol list for this country based on COUNTRY
    symbols = COUNTRY_SYMBOL_FETCHERS[COUNTRY]()
    print(f"Retrieved raw ETF symbol list, {len(symbols)} total")

    # Step 2a: listed for more than 15 years
    remaining = []
    for symbol in symbols:
        if passes_listing_age(symbol):
            remaining.append(symbol)
        time.sleep(REQUEST_DELAY)
    print(f"{len(remaining)} remaining after 'listed over 15 years' filter")

    # Step 2b: minimum trading volume
    next_remaining = []
    for symbol in remaining:
        if passes_min_volume(symbol):
            next_remaining.append(symbol)
        time.sleep(REQUEST_DELAY)
    remaining = next_remaining
    print(f"{len(remaining)} remaining after 'minimum volume' filter")

    # Step 2c: low volatility (passed in as a batch)
    remaining = filter_low_volatility(remaining)
    print(f"{len(remaining)} remaining after 'low volatility' filter")

    # Step 2d: remove ETFs with correlated price movement (passed in as a batch)
    remaining = remove_correlated_etfs(remaining)
    print(f"{len(remaining)} remaining after 'removing correlated ETFs'")

    # Step 2e: IBKR tradeability (passed in as a batch)
    remaining = filter_ibkr_tradeable(remaining)
    print(f"{len(remaining)} remaining after 'IBKR tradeable' filter")

    # TODO: the out-of-sample validation step in out_sampling.py is skipped for now; add it here in the future

    # Step 3: symbols that pass all filters are treated as this country's universe
    universe_df = pd.DataFrame({"symbol": remaining, "country": COUNTRY})

    # Step 4: read the existing universe.csv, remove old rows for this country, then append the new results
    existing_universe_df = _load_existing_csv(UNIVERSE_PATH, ["symbol", "country"])
    existing_universe_df = existing_universe_df[existing_universe_df["country"] != COUNTRY]
    updated_universe_df = pd.concat([existing_universe_df, universe_df], ignore_index=True)
    updated_universe_df.to_csv(UNIVERSE_PATH, index=False)
    print(f"universe.csv updated: {COUNTRY} added {len(universe_df)}, total {len(updated_universe_df)}")

    # Step 5: run the good_universe filter on each symbol that passed the universe filter
    good_universe_symbols = []
    for symbol in remaining:
        if passes_good_universe(symbol):
            good_universe_symbols.append(symbol)
        time.sleep(REQUEST_DELAY)
    print(f"{len(good_universe_symbols)} remaining after 'good_universe' filter")

    # Step 6: read the existing good_universe.csv, remove old rows for this country, then append the new results
    good_universe_df = pd.DataFrame({"symbol": good_universe_symbols, "country": COUNTRY})
    existing_good_universe_df = _load_existing_csv(GOOD_UNIVERSE_PATH, ["symbol", "country"])
    existing_good_universe_df = existing_good_universe_df[existing_good_universe_df["country"] != COUNTRY]
    updated_good_universe_df = pd.concat([existing_good_universe_df, good_universe_df], ignore_index=True)
    updated_good_universe_df.to_csv(GOOD_UNIVERSE_PATH, index=False)
    print(f"good_universe.csv updated: {COUNTRY} added {len(good_universe_df)}, total {len(updated_good_universe_df)}")

    print(f"===== {COUNTRY} filtering pipeline complete =====")


if __name__ == "__main__":
    main()
