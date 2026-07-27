# This file reads the ETF list from the existing universe.csv,
# runs the good_universe filter directly, and outputs good_universe.csv,
# without needing to re-run the earlier listing_age, min_volume, low_volatility, etc. filter steps

import os
import time

import pandas as pd

from filters.good_universe_filter import passes_good_universe

# ========== Parameter settings block ==========
# Country I can change
COUNTRY = "United States"

UNIVERSE_PATH = "data/universe.csv"
GOOD_UNIVERSE_PATH = "data/good_universe.csv"
REQUEST_DELAY = 0.3


def _load_existing_csv(path: str, columns: list[str]) -> pd.DataFrame:
    """Read the existing csv; if it doesn't exist or is empty, return an empty DataFrame with only the specified columns."""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return pd.read_csv(path)
    return pd.DataFrame(columns=columns)


def main():
    # Read that country's symbol list from universe.csv
    universe_df = pd.read_csv(UNIVERSE_PATH)
    remaining = universe_df[universe_df["country"] == COUNTRY]["symbol"].tolist()
    print(f"===== Starting good_universe filter for country: {COUNTRY} =====")
    print(f"Loaded {len(remaining)} symbols from universe.csv")

    # Step 5: run the good_universe filter on each symbol
    good_universe_symbols = []
    for symbol in remaining:
        if passes_good_universe(symbol):
            good_universe_symbols.append(symbol)
        time.sleep(REQUEST_DELAY)
    print(f"{len(good_universe_symbols)} remaining after 'good_universe' filter")

    # Step 6: read the existing good_universe.csv, remove old data for the same country, then append the new results
    good_universe_df = pd.DataFrame({"symbol": good_universe_symbols, "country": COUNTRY})
    existing_good_universe_df = _load_existing_csv(GOOD_UNIVERSE_PATH, ["symbol", "country"])
    existing_good_universe_df = existing_good_universe_df[existing_good_universe_df["country"] != COUNTRY]
    updated_good_universe_df = pd.concat([existing_good_universe_df, good_universe_df], ignore_index=True)
    updated_good_universe_df.to_csv(GOOD_UNIVERSE_PATH, index=False)
    print(f"good_universe.csv updated: {COUNTRY} added {len(good_universe_df)}, total {len(updated_good_universe_df)}")

    print(f"===== {COUNTRY} good_universe filter complete =====")


if __name__ == "__main__":
    main()