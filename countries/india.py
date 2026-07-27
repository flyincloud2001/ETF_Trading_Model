# This file fetches all Indian NSE exchange ETF symbols

import io
import re

import pandas as pd
import requests

# Official NSE ETF list CSV URL
NSE_ETF_CSV_URL = "https://nsearchives.nseindia.com/content/equities/ETF_SECURITY_L.csv"

# Wikipedia page URL listing Indian ETFs (fallback when the official NSE source fails)
WIKI_ETF_URL = "https://en.wikipedia.org/wiki/List_of_Indian_exchange-traded_funds"

# Full spoofed browser headers, to avoid being rejected by the official NSE website
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.nseindia.com/",
}

# Keywords that must be excluded from the name (leveraged, inverse ETFs)
EXCLUDED_NAME_KEYWORDS = ("LEVERAGED", "INVERSE", "BEAR", "SHORT", "2X", "3X")

# Column name keywords that may indicate a ticker code column (used for the Wikipedia fallback)
TICKER_COLUMN_KEYWORDS = ("NSE", "SYMBOL", "TICKER")


def _apply_name_filter(df: pd.DataFrame, symbol_column: str) -> list[str]:
    """Dynamically locate the name column, exclude leveraged/inverse ETFs, and return the list of valid raw symbols."""
    name_column = next((col for col in df.columns if "NAME" in str(col).upper()), None)

    symbols = []
    for _, row in df.iterrows():
        symbol = row.get(symbol_column)

        if pd.isna(symbol):
            continue

        symbol = str(symbol).strip()
        if not symbol:
            continue

        if name_column is not None:
            name = row.get(name_column)
            if not pd.isna(name) and any(
                keyword in str(name).upper() for keyword in EXCLUDED_NAME_KEYWORDS
            ):
                continue

        symbols.append(symbol)

    return symbols


def _fetch_from_nse() -> list[str]:
    """Step 1: try to download the ETF list CSV from the official NSE source."""
    response = requests.get(NSE_ETF_CSV_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    df = pd.read_csv(io.StringIO(response.text))

    if "SYMBOL" not in df.columns:
        raise ValueError("NSE ETF CSV does not contain a SYMBOL column")

    symbols = _apply_name_filter(df, "SYMBOL")
    return [f"{symbol}.NS" for symbol in symbols]


def _fetch_from_wikipedia() -> list[str]:
    """Step 2: fall back to Wikipedia when the official NSE source fails."""
    response = requests.get(WIKI_ETF_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

    symbols = []
    for table in tables:
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

        raw_symbols = _apply_name_filter(table, ticker_column)

        for raw_symbol in raw_symbols:
            # Extract the actual code from formats like "NSE: LIQUIDBEES"; otherwise use the raw field value directly
            match = re.search(r"([A-Z0-9\-&]+)\s*$", raw_symbol.upper())
            ticker = match.group(1) if match else raw_symbol.upper()
            symbols.append(f"{ticker}.NS")

    return symbols


def get_in_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Indian NSE exchange (in the .NS suffix format used by yfinance)."""
    try:
        symbols = _fetch_from_nse()
        if symbols:
            return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Warning: could not fetch ETF list from NSE official source ({e}), falling back to Wikipedia")

    try:
        symbols = _fetch_from_wikipedia()
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not fetch India ETF symbol list from either source ({e})")
        return []
