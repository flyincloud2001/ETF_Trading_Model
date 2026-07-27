# This file fetches all Brazilian B3 exchange ETF symbols

import base64
import json

import pandas as pd
import requests

# Basic query parameters for the official B3 internal API
B3_API_PARAMS = {"language": "pt-br", "pageNumber": 1, "pageSize": 500, "typeFund": "ETF"}

# B3 fallback page URL (used when the official API fails)
B3_FALLBACK_URL = "https://sistemaswebb3-listados.b3.com.br/fundsListedPage/ETF"

# Spoofed browser User-Agent, to avoid being rejected
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Keywords that must be excluded from the name (leveraged, inverse ETFs). The Portuguese keywords must be kept as-is to match Portuguese fund names
EXCLUDED_NAME_KEYWORDS = (
    "ALAVANCADO",
    "INVERSO",
    "INVERSE",
    "LEVERAGED",
    "BEAR",
    "SHORT",
    "2X",
    "3X",
)

# Column name keywords that may indicate a ticker code column (used for fallback table parsing)
TICKER_COLUMN_KEYWORDS = ("TICKER", "CODE", "CODIGO", "SYMBOL")
# Column name keywords that may indicate a fund name column
NAME_COLUMN_KEYWORDS = ("NAME", "NOME")


def _name_is_excluded(name) -> bool:
    """Determine whether the name contains a keyword that should be excluded, such as leveraged or inverse."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return False
    name_upper = str(name).upper()
    return any(keyword in name_upper for keyword in EXCLUDED_NAME_KEYWORDS)


def _fetch_from_b3_api() -> list[str]:
    """Call the official B3 internal API to get the ETF list and parse out the symbols."""
    encoded = base64.b64encode(json.dumps(B3_API_PARAMS).encode()).decode()
    url = f"https://sistemaswebb3-listados.b3.com.br/fundsProxy/fundsCall/GetListedFundsSummaryByTypeFunds/{encoded}"

    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    payload = response.json()

    results = payload.get("results", [])

    symbols = []
    for result in results:
        ticker = result.get("fundTicker")

        if ticker is None or str(ticker).strip() == "":
            continue

        ticker = str(ticker).strip()

        # Dynamically locate the name column, to filter out leveraged and inverse ETFs
        name_key = next(
            (key for key in result.keys() if any(keyword in key.upper() for keyword in NAME_COLUMN_KEYWORDS)),
            None,
        )
        if name_key is not None and _name_is_excluded(result.get(name_key)):
            continue

        symbols.append(f"{ticker}.SA")

    return symbols


def _fetch_from_fallback_page() -> list[str]:
    """When the official B3 API fails, fall back to parsing the tables on the fallback page."""
    response = requests.get(B3_FALLBACK_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

    symbols = []
    for table in tables:
        columns = [str(col) for col in table.columns]
        ticker_column = next(
            (col for col in columns if any(keyword in col.upper() for keyword in TICKER_COLUMN_KEYWORDS)),
            None,
        )

        if ticker_column is None:
            continue

        name_column = next(
            (col for col in columns if any(keyword in col.upper() for keyword in NAME_COLUMN_KEYWORDS)),
            None,
        )

        for _, row in table.iterrows():
            ticker = row.get(ticker_column)

            if pd.isna(ticker):
                continue

            ticker = str(ticker).strip()
            if not ticker:
                continue

            if name_column is not None and _name_is_excluded(row.get(name_column)):
                continue

            symbols.append(f"{ticker}.SA")

    return symbols


def get_br_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Brazilian B3 exchange (in the .SA suffix format used by yfinance)."""
    try:
        symbols = _fetch_from_b3_api()
        if symbols:
            return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Warning: could not fetch ETF list from B3 official API ({e}), falling back to listed page")

    try:
        symbols = _fetch_from_fallback_page()
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not fetch Brazil ETF symbol list from either source ({e})")
        return []
