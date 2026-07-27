# This file fetches all Singapore SGX exchange ETF symbols

import time

import pandas as pd
import requests
import yfinance as yf

# Wikipedia page URL listing Singapore SGX ETFs
SGX_ETF_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_Singapore_exchange-traded_funds"

# Spoofed browser User-Agent, to avoid being rejected
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Keywords that must be excluded from the name (inverse, short, leveraged ETFs)
EXCLUDED_NAME_KEYWORDS = ("INVERSE", "BEAR", "SHORT", "LEVERAGED", "2X", "3X")

# Column name keywords that may indicate a ticker code column
TICKER_COLUMN_KEYWORDS = ("SYMBOL", "TICKER", "CODE", "SGX")

# Wait time in seconds between each yfinance symbol verification
VERIFY_DELAY_SECONDS = 0.3


def get_sg_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Singapore SGX exchange (in the .SI suffix format used by yfinance)."""
    try:
        response = requests.get(SGX_ETF_WIKI_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()

        tables = pd.read_html(response.text)

        candidate_symbols = []
        for table in tables:
            # Print all found table column names for debugging
            print(f"Found table columns: {list(table.columns)}")

            ticker_column = next(
                (
                    col
                    for col in table.columns
                    if any(keyword in str(col).upper() for keyword in TICKER_COLUMN_KEYWORDS)
                ),
                None,
            )

            if ticker_column is None:
                continue

            # Try to locate the name column, to filter out inverse, short, and leveraged ETFs
            name_column = next((col for col in table.columns if "NAME" in str(col).upper()), None)

            for _, row in table.iterrows():
                ticker = row.get(ticker_column)

                if pd.isna(ticker):
                    continue

                ticker = str(ticker).strip().upper()

                if not ticker:
                    continue

                if name_column is not None:
                    name = row.get(name_column)
                    if not pd.isna(name) and any(
                        keyword in str(name).upper() for keyword in EXCLUDED_NAME_KEYWORDS
                    ):
                        continue

                candidate_symbols.append(f"{ticker}.SI")

        # Verify each ticker individually with yfinance; skip any ticker that fails verification or returns empty data
        symbols = []
        for symbol in candidate_symbols:
            try:
                hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
                if hist is not None and not hist.empty:
                    symbols.append(symbol)
            except Exception:
                pass

            time.sleep(VERIFY_DELAY_SECONDS)

        # Remove duplicates while preserving original order
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: exception while fetching Singapore ETF symbols ({e})")
        return []
