# This file fetches all South African JSE exchange ETF symbols

import io
import re
import time

import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

# JSE ETF list page URL
JSE_ETF_LIST_PAGE_URL = "https://www.jse.co.za/files/etf-list"

# Fallback XLSX URL used when the page link cannot be found
FALLBACK_XLSX_URL = "https://www.jse.co.za/sites/default/files/media/documents/ETFList/ETF%20List%20v.53.xlsx"

# justETF fallback search page URL and dynamic counter regex pattern (same logic as countries/uk.py)
JUSTETF_SEARCH_PAGE_URL = "https://www.justetf.com/en/search.html?search=ETFS"
JUSTETF_COUNTER_PATTERN = r"(\d+)-1\.0-container-tabsContentContainer-tabsContentRepeater-1-container-content-etfsTablePanel&search=ETFS&_wicket=1"

# Fixed payload for the justETF POST request, with country set to ZA and defaultCurrency set to ZAR
JUSTETF_POST_PAYLOAD = {
    "draw": 1,
    "start": 0,
    "length": -1,
    "lang": "en",
    "country": "ZA",
    "universeType": "private",
    "defaultCurrency": "ZAR",
}

# Spoofed browser User-Agent, to avoid being rejected
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Keywords that must be excluded from the name (leveraged, inverse ETFs)
EXCLUDED_NAME_KEYWORDS = ("INVERSE", "LEVERAGED", "BEAR", "SHORT", "2X", "3X")

# Column name keywords that may indicate a ticker code column
CODE_COLUMN_KEYWORDS = ("CODE", "TICKER", "SYMBOL", "JSE")
# Column name keywords that may indicate a name column
NAME_COLUMN_KEYWORDS = ("NAME", "FUND", "ETF")

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


def _find_xlsx_url() -> str:
    """Locate the latest XLSX download link on the JSE ETF list page; return the fallback URL if not found."""
    try:
        response = requests.get(JSE_ETF_LIST_PAGE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "ETFList" in href or href.lower().endswith(".xlsx"):
                if href.startswith("http"):
                    return href
                return f"https://www.jse.co.za{href}"
    except Exception:
        pass

    return FALLBACK_XLSX_URL


def _fetch_codes_from_jse() -> list[str]:
    """Step 1: download the JSE ETF list XLSX and parse out the codes."""
    xlsx_url = _find_xlsx_url()

    response = requests.get(xlsx_url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    df = pd.read_excel(io.BytesIO(response.content))

    # Print all column names for debugging
    print(f"JSE ETF list column names: {list(df.columns)}")

    code_column = _find_column(df.columns, CODE_COLUMN_KEYWORDS)
    if code_column is None:
        raise ValueError(f"Could not find code column, available columns: {list(df.columns)}")

    name_column = _find_column(df.columns, NAME_COLUMN_KEYWORDS)

    codes = []
    for _, row in df.iterrows():
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


def _fetch_codes_from_justetf() -> list[str]:
    """Step 2: when the JSE source fails, fall back to justETF (same logic as countries/uk.py)."""
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
    """Append the .JO suffix to each code and verify each one individually as a valid ETF via yfinance."""
    symbols = []
    for code in codes:
        symbol = f"{code}.JO"

        try:
            hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
            if hist is not None and not hist.empty:
                symbols.append(symbol)
        except Exception:
            pass

        time.sleep(VERIFY_DELAY_SECONDS)

    return symbols


def get_za_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the South African JSE exchange (in the .JO suffix format used by yfinance)."""
    codes = []
    try:
        codes = _fetch_codes_from_jse()
    except Exception as e:
        print(f"Warning: could not fetch ETF list from JSE ({e}), falling back to justETF")

    if not codes:
        try:
            codes = _fetch_codes_from_justetf()
        except Exception as e:
            print(f"Error: could not fetch South Africa ETF symbol list from either source ({e})")
            return []

    try:
        symbols = _verify_and_build_symbols(codes)
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not verify South Africa ETF symbols via yfinance ({e})")
        return []
