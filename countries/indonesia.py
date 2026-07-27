# This file fetches all Indonesian IDX exchange ETF symbols

import time

import pandas as pd
import requests
import yfinance as yf

# IDX internal API URL
IDX_API_URL = "https://www.idx.co.id/umbraco/Surface/ETFData/GetEtfListAll"

# IDX ETF list page URL (fallback when the internal API fails)
IDX_ETF_PAGE_URL = "https://www.idx.co.id/en/market-data/exchanged-traded-fund-etf-data/exchange-traded-fund-etf-list"

# Full spoofed browser headers, to avoid being rejected
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.idx.co.id/",
}

# Keywords that must be excluded from the name (leveraged, inverse ETFs)
EXCLUDED_NAME_KEYWORDS = ("INVERSE", "LEVERAGED", "BEAR", "SHORT", "2X", "3X")

# Column name keywords that may indicate a code column
CODE_COLUMN_KEYWORDS = ("CODE", "STOCKCODE", "ETFCODE", "SYMBOL", "KODE")
# Column name keywords that may indicate a name column
NAME_COLUMN_KEYWORDS = ("NAME", "NAMA")

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


def _extract_from_records(records) -> list[str]:
    """Dynamically locate the code and name columns in the JSON data (list of dicts) and extract candidate codes."""
    if not records:
        return []

    sample_keys = list(records[0].keys())
    code_column = _find_column(sample_keys, CODE_COLUMN_KEYWORDS)

    if code_column is None:
        # If the code column cannot be found, print all column names for debugging
        print(f"Error: could not find code column in IDX API response, available columns: {sample_keys}")
        return []

    name_column = _find_column(sample_keys, NAME_COLUMN_KEYWORDS)

    codes = []
    for record in records:
        code = record.get(code_column)

        if code is None or str(code).strip() == "":
            continue

        if name_column is not None and _name_is_excluded(record.get(name_column)):
            continue

        codes.append(str(code).strip())

    return codes


def _extract_from_tables(tables) -> list[str]:
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


def _fetch_from_idx_api() -> list[str]:
    """Step 1: call the IDX internal API to get the ETF list."""
    response = requests.get(IDX_API_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    try:
        payload = response.json()
        records = payload.get("data", payload) if isinstance(payload, dict) else payload
        return _extract_from_records(records)
    except ValueError:
        # The response is not JSON, so fall back to parsing with pandas.read_html()
        tables = pd.read_html(response.text)
        return _extract_from_tables(tables)


def _fetch_from_idx_page() -> list[str]:
    """Step 2: when the IDX internal API fails, fall back to the IDX ETF list page."""
    response = requests.get(IDX_ETF_PAGE_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)
    return _extract_from_tables(tables)


def _verify_and_build_symbols(codes) -> list[str]:
    """Append the .JK suffix to each code and verify each one individually as a valid ETF via yfinance."""
    symbols = []
    for code in codes:
        symbol = f"{code}.JK"

        try:
            hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
            if hist is not None and not hist.empty:
                symbols.append(symbol)
        except Exception:
            pass

        time.sleep(VERIFY_DELAY_SECONDS)

    return symbols


def get_id_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Indonesian IDX exchange (in the .JK suffix format used by yfinance)."""
    try:
        codes = _fetch_from_idx_api()

        if not codes:
            codes = _fetch_from_idx_page()

        symbols = _verify_and_build_symbols(codes)
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not fetch Indonesia ETF symbol list ({e})")
        return []
