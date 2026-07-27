# First define data['return'], representing this ETF's return from yesterday's close to today's close over the past ten years
# Then, based on data['return'], define data['tomorrow_return'], representing the return from today's close to tomorrow's open
# Define ranges for the data['return'] values, in %, with breakpoints from range(-4, 4.2, 0.2); each range takes the form (-infinity, a), [b, c), [d, infinity)
# For each data['return'] range, calculate the proportion of corresponding data['tomorrow_return'] values that are positive, recorded as x%, and calculate the average of those positive values, y%
# Select the "data['return'] range" with the highest x value
# If this range has x>=80 and y>=0.5, the ETF passes the filter
# Finally, output the ETFs that pass the filter to "ETF_Trading_Model\data\good_universe.csv"

import math

import pandas as pd
import yfinance as yf

# Minimum number of historical rows required; below this is considered insufficient data
MIN_REQUIRED_ROWS = 500
# Threshold for the best bin's positive-return proportion (%)
X_THRESHOLD = 80
# Threshold for the best bin's average positive-return multiplier (in tomorrow_return's raw ratio; 1.005 means a gain of 0.5% or more)
Y_THRESHOLD = 1.005
# Minimum sample count threshold for the best bin
MIN_BIN_COUNT = 50


def passes_good_universe(symbol: str) -> bool:
    """Determine whether a single ETF passes the good_universe filter criteria."""
    try:
        hist = yf.Ticker(symbol).history(period="10y", auto_adjust=True)

        if hist is None or len(hist) < MIN_REQUIRED_ROWS:
            return False

        data = hist[["Open", "Close"]].copy()

        # Today's close relative to yesterday's close
        data["return"] = data["Close"] / data["Close"].shift(1)
        # Tomorrow's open relative to today's close
        data["tomorrow_return"] = data["Open"].shift(-1) / data["Close"]

        data = data.dropna(subset=["return", "tomorrow_return"])

        # Convert to percentage form, e.g. 1.02 becomes 2.0
        data["return"] = data["return"] * 100 - 100

        # Build 42 bins based on the breakpoints from range(-4, 4.2, 0.2):
        # (-inf, -4.0), [-4.0, -3.8), ..., [3.8, 4.0), [4.0, inf)
        breakpoints = [round(-4.0 + i * 0.2, 1) for i in range(41)]
        bin_edges = [-math.inf] + breakpoints + [math.inf]
        data["bin"] = pd.cut(data["return"], bins=bin_edges, right=False)

        best_x = -1.0
        best_count = -1
        best_y = 0.0

        for _bin_label, group in data.groupby("bin", observed=True):
            tomorrow_returns = group["tomorrow_return"]
            count = len(tomorrow_returns)
            if count < MIN_BIN_COUNT:
                continue

            # x% = the proportion within this bin where tomorrow's open is higher (tomorrow_return > 1.0)
            up_mask = tomorrow_returns > 1.0
            x = up_mask.mean() * 100

            # y = the average of the positive values; 0 if there are none
            up_values = tomorrow_returns[up_mask]
            y = up_values.mean() if not up_values.empty else 0.0

            # The bin with the highest x value is the best bin; ties are broken by the higher event count
            if x > best_x or (x == best_x and count > best_count):
                best_x = x
                best_count = count
                best_y = y

        return best_x >= X_THRESHOLD and best_y >= Y_THRESHOLD
    except Exception:
        return False
