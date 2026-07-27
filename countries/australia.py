# This file fetches all Australian ASX exchange ETF symbols

import io

import pandas as pd
import requests

# Official ASX listed securities CSV URL
ASX_LISTED_COMPANIES_URL = "https://www.asx.com.au/asx/research/ASXListedCompanies.csv"

# Spoofed browser User-Agent, to avoid being rejected
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Keywords that must be excluded from the name (hedge fund, managed fund, leveraged, short, inverse ETFs)
EXCLUDED_NAME_KEYWORDS = (
    "HEDGE FUND",
    "MANAGED FUND",
    "LEVERAGED",
    "BEAR",
    "SHORT",
    "INVERSE",
    "2X",
    "3X",
)


def get_au_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Australian ASX exchange (in the .AX suffix format used by yfinance)."""
    try:
        response = requests.get(ASX_LISTED_COMPANIES_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()

        # The first two lines of this CSV are descriptive text; the real header row is the third line, so skip the first two lines
        df = pd.read_csv(io.StringIO(response.text), skiprows=2)
    except Exception as e:
        print(f"Error: could not download or parse ASX listed securities list ({e})")
        return []

    symbols = []
    for _, row in df.iterrows():
        name = row.get("Company name")
        code = row.get("ASX code")

        if pd.isna(name) or pd.isna(code):
            continue

        name_upper = str(name).upper()
        code = str(code).strip()

        if not code:
            continue

        # The name must contain "ETF" to be kept
        if "ETF" not in name_upper:
            continue

        # Exclude hedge funds, managed funds, leveraged, short, and inverse ETFs
        if any(keyword in name_upper for keyword in EXCLUDED_NAME_KEYWORDS):
            continue

        symbols.append(f"{code}.AX")

    # Remove duplicates while preserving original order
    return list(dict.fromkeys(symbols))
