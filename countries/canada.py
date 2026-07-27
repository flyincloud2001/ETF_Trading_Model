# This file fetches all Canadian (TSX, TSXV) exchange ETF symbols

import string
import time

import pandas as pd
import requests

# Spoofed browser User-Agent, to avoid being rejected by eoddata.com
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Exchange codes and their corresponding ticker suffixes
EXCHANGE_SUFFIXES = {
    "TSX": ".TO",
    "TSXV": ".V",
}

# Excluded code types: bonds, preferred shares, warrants
EXCLUDED_CODE_SUBSTRINGS = (".DB", ".PR", ".WT", ".RT")

# Wait time in seconds between page fetches
PAGE_INTERVAL_SECONDS = 0.2


def _build_url(exchange: str, letter: str) -> str:
    """Build the eoddata.com stock list page URL from the exchange and letter."""
    if letter == "A":
        return f"https://www.eoddata.com/stocklist/{exchange}.htm"
    return f"https://www.eoddata.com/stocklist/{exchange}/{letter}.htm"


def _fetch_page_symbols(exchange: str, letter: str) -> list[str]:
    """Fetch the ETF symbols from a single exchange/letter page."""
    url = _build_url(exchange, letter)
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

    symbols = []
    for table in tables:
        # Find the table that has both a "Code" and a "Name" column
        if "Code" not in table.columns or "Name" not in table.columns:
            continue

        for _, row in table.iterrows():
            code = str(row["Code"])
            name = str(row["Name"])

            # Exclude codes with bond, preferred share, or warrant suffixes
            if any(substring in code for substring in EXCLUDED_CODE_SUBSTRINGS):
                continue

            # The uppercased name must contain "ETF" to be kept
            if "ETF" not in name.upper():
                continue

            symbols.append(code + EXCHANGE_SUFFIXES[exchange])

    return symbols


def get_ca_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on TSX and TSXV."""
    all_symbols = []

    for exchange in EXCHANGE_SUFFIXES:
        for letter in string.ascii_uppercase:
            try:
                all_symbols.extend(_fetch_page_symbols(exchange, letter))
            except Exception as e:
                print(f"Warning: could not fetch {exchange} stock list for letter {letter} ({e})")

            time.sleep(PAGE_INTERVAL_SECONDS)

    # Merge results from both exchanges and remove duplicates while preserving original order
    return list(dict.fromkeys(all_symbols))
