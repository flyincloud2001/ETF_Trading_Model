# This file fetches all Chilean Bolsa de Santiago exchange ETF symbols

import time

import pandas as pd
import requests
import yfinance as yf

# stockanalysis.com page URL listing Chilean ETFs
STOCKANALYSIS_URL = "https://stockanalysis.com/list/chilean-etfs/"

# Wikipedia fallback page URL (used when stockanalysis.com fails)
WIKI_FALLBACK_URL = "https://en.wikipedia.org/wiki/List_of_Chilean_exchange-traded_funds"

# Spoofed browser User-Agent, to avoid being rejected
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Keywords that must be excluded from the name (leveraged, inverse ETFs)
EXCLUDED_NAME_KEYWORDS = ("INVERSE", "LEVERAGED", "BEAR", "SHORT", "2X", "3X")

# Column name keywords that may indicate a code column
CODE_COLUMN_KEYWORDS = ("SYMBOL", "TICKER", "CODE")
# Column name keywords that may indicate a name column
NAME_COLUMN_KEYWORDS = ("NAME",)

# Wait time in seconds between each yfinance symbol verification
VERIFY_DELAY_SECONDS = 0.3


def _find_column(keys, keywords):
    """Dynamically locate the matching column name from the keywords; return None if not found."""
    for key in keys:
        key_upper = str(key).upper()
        if any(keyword in key_upper for keyword in keywords):
            return key
    return None


def _name_is_excluded(name) -> bool:
    """Determine whether the name contains a keyword that should be excluded, such as leveraged or inverse."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return False
    return any(keyword in str(name).upper() for keyword in EXCLUDED_NAME_KEYWORDS)


def _extract_codes_from_tables(tables) -> list[str]:
    """Dynamically locate the code and name columns in the HTML tables and extract candidate codes."""
    codes = []
    for table in tables:
        columns = [str(col) for col in table.columns]
        # Print the found table column names for debugging
        print(f"Found table columns: {columns}")

        code_column = _find_column(columns, CODE_COLUMN_KEYWORDS)
        if code_column is None:
            continue

        name_column = _find_column(columns, NAME_COLUMN_KEYWORDS)

        for _, row in table.iterrows():
            code = row.get(code_column)

            if pd.isna(code):
                continue

            code = str(code).strip()
            if not code:
                continue

            if name_column is not None and _name_is_excluded(row.get(name_column)):
                continue

            codes.append(code)

    return codes


def _fetch_from_stockanalysis() -> list[str]:
    """Step 1: parse the Chilean ETF list from stockanalysis.com."""
    response = requests.get(STOCKANALYSIS_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)
    return _extract_codes_from_tables(tables)


def _fetch_from_wikipedia() -> list[str]:
    """Step 2: when stockanalysis.com fails, fall back to Wikipedia."""
    response = requests.get(WIKI_FALLBACK_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)
    return _extract_codes_from_tables(tables)


def _verify_and_build_symbols(codes) -> list[str]:
    """Append the .SN suffix to each code and verify each one individually as a valid ETF via yfinance."""
    symbols = []
    for code in codes:
        symbol = f"{code}.SN"

        try:
            hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
            if hist is not None and not hist.empty:
                symbols.append(symbol)
        except Exception:
            pass

        time.sleep(VERIFY_DELAY_SECONDS)

    return symbols


def get_cl_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Chilean Bolsa de Santiago exchange (in the .SN suffix format used by yfinance)."""
    try:
        codes = _fetch_from_stockanalysis()

        if not codes:
            codes = _fetch_from_wikipedia()

        symbols = _verify_and_build_symbols(codes)
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not fetch Chile ETF symbol list ({e})")
        return []
