# This file fetches all Saudi Arabian Saudi Exchange (Tadawul) ETF symbols

import time

import yfinance as yf

# Saudi ETF code scan range (consecutive 4-digit numbers, starting from 9400)
SCAN_RANGE_START = 9400
SCAN_RANGE_END = 9450

# Fallback list of known Saudi ETF codes, added directly without verification
KNOWN_FALLBACK_CODES = [
    "9400",
    "9401",
    "9402",
    "9403",
    "9404",
    "9405",
    "9406",
    "9407",
    "9408",
    "9409",
    "9410",
    "9411",
    "9412",
]

# Wait time in seconds between each yfinance symbol verification
VERIFY_DELAY_SECONDS = 0.3

# Keywords that must be excluded from the name (leveraged, inverse ETFs)
EXCLUDED_NAME_KEYWORDS = ("INVERSE", "LEVERAGED", "BEAR", "SHORT", "2X", "3X")


def _scan_range() -> list[str]:
    """Scan the code range from 9400 to 9450, verifying each code as a valid ETF via yfinance."""
    symbols = []
    for code in range(SCAN_RANGE_START, SCAN_RANGE_END + 1):
        symbol = f"{code}.SR"
        try:
            hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
            if hist is not None and not hist.empty:
                symbols.append(symbol)
        except Exception:
            pass

        time.sleep(VERIFY_DELAY_SECONDS)

    return symbols


def _name_is_excluded(symbol: str) -> bool:
    """Best-effort lookup of the ETF name to determine whether it contains an excluded keyword such as leveraged or inverse; treated as not excluded if the lookup fails."""
    try:
        info = yf.Ticker(symbol).info
        name = info.get("longName") or info.get("shortName") or ""
    except Exception:
        return False

    if not name:
        return False

    return any(keyword in name.upper() for keyword in EXCLUDED_NAME_KEYWORDS)


def get_sa_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Saudi Arabian Saudi Exchange (in the .SR suffix format used by yfinance)."""
    scanned_symbols = []
    try:
        scanned_symbols = _scan_range()
    except Exception as e:
        print(f"Warning: exception while scanning Tadawul ETF code range ({e})")

    fallback_symbols = [f"{code}.SR" for code in KNOWN_FALLBACK_CODES]

    # Since there are few ETFs, yfinance existence verification itself is the primary filter;
    # name-keyword exclusion is a best-effort secondary filter, and a code is not excluded if the lookup fails
    combined_symbols = list(dict.fromkeys(scanned_symbols + fallback_symbols))

    symbols = []
    for symbol in combined_symbols:
        if not symbol:
            continue

        if _name_is_excluded(symbol):
            continue

        symbols.append(symbol)

    return list(dict.fromkeys(symbols))
