# Define a reasonable minimum trading volume to filter for suitable ETFs

import yfinance as yf

# Average daily dollar-volume threshold (USD for US stocks, CAD for Canadian stocks)
MIN_AVG_DOLLAR_VOLUME = 5_000_000
# Minimum number of trading-day rows required to fetch data; below this is considered insufficient data
MIN_REQUIRED_ROWS = 20
# Number of trading days used to calculate the average daily dollar volume
LOOKBACK_DAYS = 60


def passes_min_volume(symbol: str) -> bool:
    """Determine whether a single ETF meets the minimum trading volume threshold."""
    try:
        hist = yf.Ticker(symbol).history(period="3mo", auto_adjust=True)

        if hist is None or len(hist) < MIN_REQUIRED_ROWS:
            return False

        # Only take the most recent 60 trading days
        hist = hist.tail(LOOKBACK_DAYS)

        # Daily dollar volume = volume x close price
        dollar_volume = hist["Volume"] * hist["Close"]
        avg_dollar_volume = dollar_volume.mean()

        return avg_dollar_volume >= MIN_AVG_DOLLAR_VOLUME
    except Exception:
        return False
