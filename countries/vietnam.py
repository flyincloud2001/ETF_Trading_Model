# This file fetches all Vietnamese HOSE exchange ETF symbols

import time

import pandas as pd
import requests
import yfinance as yf

# stockanalysis.com page URL listing Vietnamese ETFs
STOCKANALYSIS_URL = "https://stockanalysis.com/list/vietnam-etfs/"

# Static fallback ticker list used when stockanalysis.com parsing fails
STATIC_FALLBACK_TICKERS = (
    "E1VFVN30",
    "FUEVFVND",
    "FUESSVFL",
    "FUESSV30",
    "FUEVN100",
    "FUEDCMID",
    "FUEIP100",
    "FUESSV50",
    "DCDS",
    "VFMVSF",
)

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


def _fetch_codes_from_stockanalysis() -> list[str]:
    """Step 1: parse the Vietnamese ETF list from stockanalysis.com and extract candidate codes."""
    response = requests.get(STOCKANALYSIS_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

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


def _verify_and_build_symbols(codes) -> list[str]:
    """Append the .VN suffix to each code and verify each one individually as a valid ETF via yfinance."""
    symbols = []
    for code in codes:
        if code is None or (isinstance(code, float) and pd.isna(code)):
            continue

        code = str(code).strip()
        if not code:
            continue

        symbol = f"{code}.VN"

        try:
            hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
            if hist is not None and not hist.empty:
                symbols.append(symbol)
        except Exception:
            pass

        time.sleep(VERIFY_DELAY_SECONDS)

    return symbols


def get_vn_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Vietnamese HOSE exchange (in the .VN suffix format used by yfinance)."""
    try:
        codes = _fetch_codes_from_stockanalysis()
        symbols = _verify_and_build_symbols(codes)

        if symbols:
            return list(dict.fromkeys(symbols))

        print("Warning: no ETF codes found on stockanalysis.com, falling back to static list")
    except Exception as e:
        print(f"Warning: could not fetch ETF list from stockanalysis.com ({e}), falling back to static list")

    try:
        symbols = _verify_and_build_symbols(STATIC_FALLBACK_TICKERS)
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not fetch Vietnam ETF symbol list ({e})")
        return []
