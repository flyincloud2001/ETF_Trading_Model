# This file fetches all South Korean KRX exchange ETF symbols

import pandas as pd
from pykrx import stock

# Keywords that must be excluded from the name (leveraged, inverse ETFs; in Korean)
EXCLUDED_NAME_KEYWORDS = ("레버리지", "인버스", "2X", "3X")


def get_kr_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the South Korean KRX exchange (in the .KS suffix format used by yfinance)."""
    try:
        today = pd.Timestamp.today().strftime("%Y%m%d")

        # Get the list of all ETF ticker codes (6-digit numeric codes)
        tickers = stock.get_etf_ticker_list(today)

        symbols = []
        for ticker in tickers:
            # Fetch each ETF's name individually, to filter out leveraged and inverse ETFs
            name = stock.get_market_ticker_name(ticker)

            if not name:
                continue

            if any(keyword in name for keyword in EXCLUDED_NAME_KEYWORDS):
                continue

            symbols.append(f"{ticker}.KS")

        # Remove duplicates while preserving original order
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: exception while fetching South Korea ETF symbol list ({e})")
        return []
