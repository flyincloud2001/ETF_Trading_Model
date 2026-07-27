# This file fetches all Polish GPW exchange ETF symbols

import pandas as pd
import requests

# Official GPW ETF full-view page URL
GPW_ETF_LIST_URL = "https://www.gpw.pl/etfs-full-view"

# Spoofed browser User-Agent, to avoid being rejected
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Static fallback ticker list used when the official GPW site parsing fails
STATIC_FALLBACK_TICKERS = (
    "ETFBCASH",
    "ETFBDIVPL",
    "ETFBM40TR",
    "ETFBNDXPL",
    "ETFBS80TR",
    "ETFBSPXPL",
    "ETFBTBSP",
    "ETFBTCPL",
    "ETFBW20ST",
    "ETFBW20TR",
    "ETFDAX",
    "ETFNATO",
    "ETFSP500",
)

# Code value for the Polish-language subtotal row, which must be excluded
SUBTOTAL_ROW_VALUE = "RAZEM"

# Suffixes that must be excluded from the end of a code (2x short, 3x leveraged, 2x leveraged)
EXCLUDED_SUFFIXES = ("2ST", "3LV", "2LV")

# Codes containing these keywords must also be excluded (inverse, short ETFs)
EXCLUDED_KEYWORDS = ("INVERSE", "SHORT")


def _is_excluded(code: str) -> bool:
    """Determine whether a code is a leveraged, inverse, or short ETF that should be excluded."""
    if code.endswith(EXCLUDED_SUFFIXES):
        return True
    return any(keyword in code for keyword in EXCLUDED_KEYWORDS)


def _apply_filter(tickers) -> list[str]:
    """Apply cleanup, exclude the subtotal row, exclude leveraged/inverse keywords, and append the .WA suffix."""
    symbols = []
    for ticker in tickers:
        if ticker is None or (isinstance(ticker, float) and pd.isna(ticker)):
            continue

        code = str(ticker).strip().upper()

        if not code or code == SUBTOTAL_ROW_VALUE:
            continue

        if _is_excluded(code):
            continue

        symbols.append(f"{code}.WA")

    return symbols


def _fetch_from_gpw() -> list[str]:
    """Parse all codes from the "Instrument" column on the official GPW ETF full-view page."""
    response = requests.get(GPW_ETF_LIST_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

    tickers = []
    for table in tables:
        columns = [str(col) for col in table.columns]

        if not any("Instrument" in col for col in columns):
            continue

        # Print the found table column names for debugging
        print(f"Found table columns: {columns}")

        instrument_column = next(col for col in table.columns if "Instrument" in str(col))
        tickers.extend(table[instrument_column].tolist())

    return tickers


def get_pl_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Polish GPW exchange (in the .WA suffix format used by yfinance)."""
    try:
        tickers = _fetch_from_gpw()
        symbols = _apply_filter(tickers)

        if symbols:
            return list(dict.fromkeys(symbols))

        print("Warning: no ETF codes found on GPW page, falling back to static list")
        return list(dict.fromkeys(_apply_filter(STATIC_FALLBACK_TICKERS)))
    except Exception as e:
        print(f"Error: could not fetch Poland ETF symbol list from GPW ({e}), falling back to static list")
        return list(dict.fromkeys(_apply_filter(STATIC_FALLBACK_TICKERS)))
