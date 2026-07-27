# This file fetches all UK LSE exchange ETF symbols

import re

import requests

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
    "country": "GB",
    "universeType": "private",
    "defaultCurrency": "GBP",
}

# Keywords that must be excluded from the name (leveraged, short, inverse ETFs)
EXCLUDED_NAME_KEYWORDS = ("LEVERAGED", "SHORT", "INVERSE", "2X", "3X", "-2", "-3")


def get_uk_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the UK LSE exchange (in the .L suffix format used by yfinance)."""
    session = requests.Session()

    # Step 1: send a GET request to justETF to obtain the dynamic counter
    try:
        get_response = session.get(SEARCH_PAGE_URL, headers=HEADERS, timeout=30)
        get_response.raise_for_status()
    except Exception as e:
        print(f"Error: could not fetch justETF search page ({e})")
        return []

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

    try:
        post_response = session.post(post_url, headers=HEADERS, data=POST_PAYLOAD, timeout=30)
        post_response.raise_for_status()
        etf_list = post_response.json().get("data", [])
    except Exception as e:
        print(f"Error: could not fetch justETF ETF list ({e})")
        return []

    symbols = []
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

        symbols.append(f"{ticker}.L")

    # Remove duplicates while preserving original order
    return list(dict.fromkeys(symbols))
