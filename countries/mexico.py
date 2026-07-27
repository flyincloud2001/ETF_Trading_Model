# This file fetches all Mexican BMV local ETF symbols

import pandas as pd
import requests

# Official BMV TRAC page URL
BMV_TRAC_URL = "https://www.bmv.com.mx/en/markets/tracks"

# Spoofed browser User-Agent, to avoid being rejected
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Static fallback ticker list used when the official BMV site parsing fails
STATIC_FALLBACK_TICKERS = (
    "NAFTRACISHRS",
    "ILCTRACISHRS",
    "MEXTRAC09",
    "SMARTRC14",
    "DIABLOI10",
    "ANGEL10",
    "CHNTRAC11",
    "FIBRATC14",
    "DLRTRAC15",
    "PSOTRAC15",
    "QVGMEX18",
)

# Keywords that must be excluded from the name or code (inverse, leveraged ETFs; ANGEL10 is 2x leveraged)
EXCLUDED_KEYWORDS = (
    "INVERSE",
    "INVERSO",
    "DIABLO",
    "ANGEL",
    "LEVERAGED",
    "BEAR",
    "SHORT",
    "2X",
    "3X",
)


def _is_excluded(text) -> bool:
    """Determine whether the text contains a keyword that should be excluded, such as inverse or leveraged."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return False
    return any(keyword in str(text).upper() for keyword in EXCLUDED_KEYWORDS)


def _fetch_from_bmv() -> list[str]:
    """Step 1: parse the first column of every table on the official BMV TRAC page for codes."""
    response = requests.get(BMV_TRAC_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

    if not tables:
        raise ValueError("No tables found on BMV TRAC page")

    tickers = []
    for table in tables:
        if table.shape[1] < 1:
            continue

        # The first column of each table is usually the NAME column; BMV codes consist of multiple alphanumeric characters
        first_column = table.iloc[:, 0]

        for value in first_column:
            if pd.isna(value):
                continue

            # Strip whitespace and use the full string as the code
            ticker = "".join(str(value).split())
            if ticker:
                tickers.append(ticker)

    return tickers


def _apply_filter(tickers) -> list[str]:
    """Apply the excluded-keyword and empty-value filters, and append the .MX suffix."""
    symbols = []
    for ticker in tickers:
        if ticker is None or (isinstance(ticker, float) and pd.isna(ticker)):
            continue

        ticker = str(ticker).strip()
        if not ticker:
            continue

        if _is_excluded(ticker):
            continue

        symbols.append(f"{ticker}.MX")

    return symbols


def get_mx_etf_symbols() -> list[str]:
    """Return the list of all local ETF symbols on the Mexican BMV exchange (in the .MX suffix format used by yfinance)."""
    try:
        tickers = _fetch_from_bmv()
        symbols = _apply_filter(tickers)
        if symbols:
            return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Warning: could not fetch ETF list from BMV official page ({e}), falling back to static list")

    try:
        symbols = _apply_filter(STATIC_FALLBACK_TICKERS)
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not build Mexico ETF symbol list ({e})")
        return []
