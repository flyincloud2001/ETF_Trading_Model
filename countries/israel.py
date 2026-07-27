# This file fetches all Israeli TASE exchange ETF symbols

import re
import time

import pandas as pd
import requests
import yfinance as yf

# Official TASE ETF page URL
TASE_ETF_PAGE_URL = "https://market.tase.co.il/en/market_data/etfs"

# justETF fallback search page URL and dynamic counter regex pattern (same logic as countries/uk.py)
JUSTETF_SEARCH_PAGE_URL = "https://www.justetf.com/en/search.html?search=ETFS"
JUSTETF_COUNTER_PATTERN = r"(\d+)-1\.0-container-tabsContentContainer-tabsContentRepeater-1-container-content-etfsTablePanel&search=ETFS&_wicket=1"

# Fixed payload for the justETF POST request, with country set to IL and defaultCurrency set to ILS
JUSTETF_POST_PAYLOAD = {
    "draw": 1,
    "start": 0,
    "length": -1,
    "lang": "en",
    "country": "IL",
    "universeType": "private",
    "defaultCurrency": "ILS",
}

# Full spoofed browser headers, to avoid being rejected
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://market.tase.co.il/",
}

# Keywords that must be excluded from the name (leveraged, inverse ETFs). The Hebrew keywords must be kept as-is to match Hebrew names
EXCLUDED_NAME_KEYWORDS = (
    "INVERSE",
    "LEVERAGED",
    "BEAR",
    "SHORT",
    "2X",
    "3X",
    "ממונף",
    "הפוך",
)

# Column name keywords that may indicate an ETF code column
CODE_COLUMN_KEYWORDS = ("NUMBER", "CODE", "SYMBOL", "ISIN")
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


def _fetch_codes_from_tase() -> list[str]:
    """Step 1: parse the codes from the official TASE ETF page."""
    response = requests.get(TASE_ETF_PAGE_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

    codes = []
    for table in tables:
        columns = [str(col) for col in table.columns]
        # Print all found table column names for debugging
        print(f"Found table columns: {columns}")

        code_column = _find_column(columns, CODE_COLUMN_KEYWORDS)
        if code_column is None:
            continue

        name_column = _find_column(columns, NAME_COLUMN_KEYWORDS)

        for _, row in table.iterrows():
            code = row.get(code_column)

            if pd.isna(code):
                continue

            # Israeli ETF codes are purely numeric; strip the decimal point and whitespace
            code = str(code).strip().split(".")[0]
            if not code:
                continue

            if name_column is not None and _name_is_excluded(row.get(name_column)):
                continue

            codes.append(code)

    return codes


def _fetch_codes_from_justetf() -> list[str]:
    """Step 2: when the TASE source fails, fall back to justETF (same logic as countries/uk.py)."""
    session = requests.Session()

    get_response = session.get(JUSTETF_SEARCH_PAGE_URL, headers=HEADERS, timeout=30)
    get_response.raise_for_status()

    counter_match = re.search(JUSTETF_COUNTER_PATTERN, get_response.text)
    if counter_match:
        counter = counter_match.group(1)
    else:
        counter = "0"
        print("Warning: could not parse justETF dynamic counter, falling back to default value 0")

    post_url = (
        f"https://www.justetf.com/en/search.html?{counter}"
        "-1.0-container-tabsContentContainer-tabsContentRepeater-1-container-content-etfsTablePanel"
        "&search=ETFS&_wicket=1"
    )

    post_response = session.post(post_url, headers=HEADERS, data=JUSTETF_POST_PAYLOAD, timeout=30)
    post_response.raise_for_status()
    etf_list = post_response.json().get("data", [])

    codes = []
    for etf in etf_list:
        ticker = etf.get("ticker")
        name = etf.get("name")

        if not ticker or not name:
            continue

        # The name must contain "ETF" to be kept
        if "ETF" not in name.upper():
            continue

        if _name_is_excluded(name):
            continue

        codes.append(ticker)

    return codes


def _verify_and_build_symbols(codes) -> list[str]:
    """Append the .TA suffix to each code and verify each one individually as a valid ETF via yfinance."""
    symbols = []
    for code in codes:
        symbol = f"{code}.TA"

        try:
            hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
            if hist is not None and not hist.empty:
                symbols.append(symbol)
        except Exception:
            pass

        time.sleep(VERIFY_DELAY_SECONDS)

    return symbols


def get_il_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Israeli TASE exchange (in the .TA suffix format used by yfinance)."""
    codes = []
    try:
        codes = _fetch_codes_from_tase()
    except Exception as e:
        print(f"Warning: could not fetch ETF list from TASE ({e}), falling back to justETF")

    if not codes:
        try:
            codes = _fetch_codes_from_justetf()
        except Exception as e:
            print(f"Error: could not fetch Israel ETF symbol list from either source ({e})")
            return []

    try:
        symbols = _verify_and_build_symbols(codes)
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not verify Israel ETF symbols via yfinance ({e})")
        return []
