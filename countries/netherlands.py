# This file fetches all Dutch Euronext Amsterdam exchange ETF symbols

import re
import time

import requests
import yfinance as yf

# Spoofed browser User-Agent, to avoid being rejected by justETF
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Search page URL used to obtain the dynamic counter
SEARCH_PAGE_URL = "https://www.justetf.com/en/search.html?search=ETFS"

# Regex pattern to parse the dynamic counter out of the search page HTML
COUNTER_PATTERN = r"(\d+)-1\.0-container-tabsContentContainer-tabsContentRepeater-1-container-content-etfsTablePanel&search=ETFS&_wicket=1"

# Fixed payload for the POST request
POST_PAYLOAD = {
    "draw": 1,
    "start": 0,
    "length": -1,
    "lang": "en",
    "country": "NL",
    "universeType": "private",
    "defaultCurrency": "EUR",
}

# Keywords that must be excluded from the name (leveraged, short, inverse ETFs)
EXCLUDED_NAME_KEYWORDS = ("LEVERAGED", "SHORT", "INVERSE", "2X", "3X", "-2", "-3")

# Wait time in seconds between each yfinance symbol verification
VERIFY_DELAY_SECONDS = 0.3


def get_nl_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Dutch Euronext Amsterdam exchange (in the .AS suffix format used by yfinance)."""
    try:
        session = requests.Session()

        # Step 1: send a GET request to justETF to obtain the dynamic counter
        get_response = session.get(SEARCH_PAGE_URL, headers=HEADERS, timeout=30)
        get_response.raise_for_status()

        counter_match = re.search(COUNTER_PATTERN, get_response.text)
        if counter_match:
            counter = counter_match.group(1)
        else:
            counter = "0"
            print("Warning: could not parse justETF dynamic counter, falling back to default value 0")

        # Step 2: build the POST URL using the counter to fetch the full ETF list
        post_url = (
            f"https://www.justetf.com/en/search.html?{counter}"
            "-1.0-container-tabsContentContainer-tabsContentRepeater-1-container-content-etfsTablePanel"
            "&search=ETFS&_wicket=1"
        )

        post_response = session.post(post_url, headers=HEADERS, data=POST_PAYLOAD, timeout=30)
        post_response.raise_for_status()
        etf_list = post_response.json().get("data", [])

        # First filter by name and ticker, to reduce unnecessary yfinance verification calls later
        candidate_symbols = []
        for etf in etf_list:
            ticker = etf.get("ticker")
            name = etf.get("name")

            if not ticker or not name:
                continue

            name_upper = name.upper()

            # The name must contain "ETF" to be kept
            if "ETF" not in name_upper:
                continue

            # Exclude leveraged, short, and inverse ETFs
            if any(keyword in name_upper for keyword in EXCLUDED_NAME_KEYWORDS):
                continue

            candidate_symbols.append(f"{ticker}.AS")

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
        print(f"Error: exception while fetching Netherlands ETF symbol list ({e})")
        return []
