# This file fetches all Turkish Borsa Istanbul exchange ETF symbols

import time

import pandas as pd
import requests
import yfinance as yf

# Official TEFAS API URL
TEFAS_API_URL = "https://www.tefas.gov.tr/api/funds/fonGnlBlgSiraliGetir"

# Query parameter; fontip=BYF represents the Exchange Traded Funds category
TEFAS_API_PARAMS = {"fontip": "BYF"}

# Spoofed browser headers, to avoid being rejected
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.tefas.gov.tr/",
}

# Keywords that must be excluded from the name (leveraged, inverse ETFs). The Turkish keywords must be kept as-is to match Turkish fund names
EXCLUDED_NAME_KEYWORDS = (
    "KALDIR",
    "TERS",
    "INVERSE",
    "LEVERAGED",
    "BEAR",
    "SHORT",
    "2X",
    "3X",
)

# Wait time in seconds between each yfinance symbol verification
VERIFY_DELAY_SECONDS = 0.3


def _name_is_excluded(name) -> bool:
    """Determine whether the name contains a keyword that should be excluded, such as leveraged or inverse."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return False
    return any(keyword in str(name).upper() for keyword in EXCLUDED_NAME_KEYWORDS)


def get_tr_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Turkish Borsa Istanbul exchange (in the .IS suffix format used by yfinance)."""
    try:
        response = requests.get(TEFAS_API_URL, headers=HEADERS, params=TEFAS_API_PARAMS, timeout=30)
        response.raise_for_status()
        records = response.json().get("data", [])

        # First filter by fund code and name, to reduce unnecessary yfinance verification calls later
        candidate_symbols = []
        for record in records:
            code = record.get("FONKODU")

            if code is None or str(code).strip() == "":
                continue

            code = str(code).strip()

            if _name_is_excluded(record.get("FONUNVAN")):
                continue

            candidate_symbols.append(f"{code}.IS")

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
        print(f"Error: could not fetch Turkey ETF symbol list from TEFAS API ({e})")
        return []
