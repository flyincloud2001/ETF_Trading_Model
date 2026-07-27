# This file can only be run after "build_universe_and_good_universe.py" has been executed
# This file produces its output using "how_to_rank.py" located at "ETF_Trading_Model\trading_logic"
# The output file path is "ETF_Trading_Model\data\ranked_good_universe.csv"

import time

import numpy as np
import pandas as pd
import yfinance as yf

from trading_logic.how_to_rank import rank_good_universe

# ========== Parameter settings ==========
GOOD_UNIVERSE_PATH = "data/good_universe.csv"
RANKED_OUTPUT_PATH = "data/ranked_good_universe.csv"
REQUEST_DELAY = 0.3
PROGRESS_INTERVAL = 20

# Minimum required number of historical data rows for "insufficient data" (consistent with filters/good_universe_filter.py)
MIN_REQUIRED_ROWS = 500


def _compute_best_bin(symbol: str):
    """
    Re-fetch 10 years of data for a single ETF and find the bin with the highest x value among the 42 bins.
    Returns (x, y, best_bin_lower, best_bin_upper); returns None when data is insufficient.
    """
    hist = yf.Ticker(symbol).history(period="10y", auto_adjust=True)

    if hist is None or len(hist) < MIN_REQUIRED_ROWS:
        return None

    data = hist[["Open", "Close"]].copy()

    # Today's close-vs-yesterday's-close return
    data["return"] = data["Close"] / data["Close"].shift(1)
    # Tomorrow's open-vs-today's-close return
    data["tomorrow_return"] = data["Open"].shift(-1) / data["Close"]

    data = data.dropna(subset=["return", "tomorrow_return"])

    # Convert to percentage form, e.g. 1.02 becomes 2.0
    data["return"] = data["return"] * 100 - 100

    # The exact same 42-bin definition as filters/good_universe_filter.py:
    # (-inf, -4.0), [-4.0, -3.8), ..., [3.8, 4.0), [4.0, inf)
    breakpoints = [round(-4.0 + i * 0.2, 1) for i in range(41)]
    bin_edges = [-np.inf] + breakpoints + [np.inf]
    data["bin"] = pd.cut(data["return"], bins=bin_edges, right=False)

    best_x = -1.0
    best_count = -1
    best_y = 0.0
    best_bin = None

    for bin_label, group in data.groupby("bin", observed=True):
        tomorrow_returns = group["tomorrow_return"]
        count = len(tomorrow_returns)

        # x% = the proportion in this bin where tomorrow's open rose (tomorrow_return > 1.0)
        up_mask = tomorrow_returns > 1.0
        x = up_mask.mean() * 100

        # y = the average of the up-move values, or 0 if there are no up-move values
        up_values = tomorrow_returns[up_mask]
        y = up_values.mean() if not up_values.empty else 0.0

        # The bin with the highest x value is the best bin; ties are broken by the higher event count
        if x > best_x or (x == best_x and count > best_count):
            best_x = x
            best_count = count
            best_y = y
            best_bin = bin_label

    if best_bin is None:
        return None

    return best_x, best_y, best_bin.left, best_bin.right


def main():
    good_universe_df = pd.read_csv(GOOD_UNIVERSE_PATH)
    total = len(good_universe_df)
    print(f"Loaded good_universe.csv, {total} ETFs total")

    records = []

    for i, (_, row) in enumerate(good_universe_df.iterrows()):
        symbol = row["symbol"]
        country = row["country"]

        try:
            result = _compute_best_bin(symbol)
        except Exception as e:
            print(f"Warning: exception while computing x, y for {symbol} ({e}), skipped")
            result = None

        if result is None:
            print(f"Warning: insufficient history or computation failed for {symbol}, skipped")
        else:
            x, y, bin_lower, bin_upper = result
            records.append({
                "symbol": symbol,
                "country": country,
                "x": x,
                "y": y,
                "best_bin_lower": bin_lower,
                "best_bin_upper": bin_upper,
            })

        time.sleep(REQUEST_DELAY)

        if (i + 1) % PROGRESS_INTERVAL == 0 or (i + 1) == total:
            print(f"Processed {i + 1}/{total} ETFs")

    df = pd.DataFrame(records)
    ranked_df = rank_good_universe(df)
    ranked_df.to_csv(RANKED_OUTPUT_PATH, index=False)

    print(f"Done! ranked_good_universe.csv written to {RANKED_OUTPUT_PATH}, {len(ranked_df)} ETFs total")


if __name__ == "__main__":
    main()
