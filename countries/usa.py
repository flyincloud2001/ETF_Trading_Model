# This file fetches all US-listed ETF symbols from the official NASDAQ listings

import requests

# Official NASDAQ listing URLs
NASDAQ_LISTED_URL = "http://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "http://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

# Symbol column name for each listing (nasdaqlisted uses "Symbol", otherlisted uses "ACT Symbol")
SYMBOL_COLUMN_NAMES = {
    NASDAQ_LISTED_URL: "Symbol",
    OTHER_LISTED_URL: "ACT Symbol",
}


def _fetch_etf_symbols(url: str) -> list[str]:
    """Fetch the list of ETF symbols from a single official NASDAQ listing URL."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    lines = response.text.splitlines()
    # The first line is the header row, and the last two lines are file info; exclude both
    header = lines[0].split("|")
    data_lines = lines[1:-2]

    symbol_index = header.index(SYMBOL_COLUMN_NAMES[url])
    etf_index = header.index("ETF")

    symbols = []
    for line in data_lines:
        fields = line.split("|")
        if len(fields) <= max(symbol_index, etf_index):
            continue

        # Only keep rows where the ETF field value is "Y"
        if fields[etf_index] != "Y":
            continue

        symbol = fields[symbol_index]
        # Exclude symbols containing "." or "$" (preferred shares, warrants, etc.)
        if "." in symbol or "$" in symbol:
            continue

        symbols.append(symbol)

    return symbols


def get_us_etf_symbols() -> list[str]:
    """Return the list of all US-listed ETF symbols."""
    all_symbols = []

    for url in (NASDAQ_LISTED_URL, OTHER_LISTED_URL):
        try:
            all_symbols.extend(_fetch_etf_symbols(url))
        except Exception as e:
            print(f"Warning: could not fetch ETF list from {url} ({e})")

    # Merge both sources and remove duplicates while preserving original order
    return list(dict.fromkeys(all_symbols))
