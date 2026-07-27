# This file fetches all Taiwan TWSE exchange ETF symbols

import pandas as pd
import requests

# Official TWSE OpenAPI: fund basic information summary
TWSE_API_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap47_L"

# Wikipedia fallback page URLs (tried in order when the official TWSE API fails)
WIKI_FALLBACK_URLS = (
    "https://en.wikipedia.org/wiki/List_of_Taiwan_exchange-traded_funds",
    "https://zh.wikipedia.org/wiki/臺灣指數股票型基金列表",
)

# Spoofed browser User-Agent, to avoid being rejected
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Keywords that must be excluded from the name (leveraged, inverse ETFs). The Chinese keywords must be kept as-is, since they are used to match Chinese fund names
EXCLUDED_NAME_KEYWORDS = (
    "槓桿",
    "反向",
    "放空",
    "BEAR",
    "INVERSE",
    "LEVERAGED",
    "2X",
    "3X",
    "2倍",
    "3倍",
)

# Column name keywords that may indicate the fund code, name, or listing date columns
CODE_COLUMN_KEYWORDS = ("基金代號", "代號", "CODE", "SYMBOL", "TICKER")
NAME_COLUMN_KEYWORDS = ("基金中文名稱", "基金名稱", "名稱", "NAME")
LISTING_DATE_COLUMN_KEYWORDS = ("上市日期", "上市", "LISTING DATE", "DATE")


def _find_column(keys, keywords):
    """Dynamically locate the matching column name from the keywords; return None if not found."""
    for key in keys:
        key_upper = str(key).upper()
        if any(keyword.upper() in key_upper for keyword in keywords):
            return key
    return None


def _name_is_excluded(name) -> bool:
    """Determine whether the name contains a keyword that should be excluded, such as leveraged or inverse."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return False
    name_str = str(name).upper()
    return any(keyword.upper() in name_str for keyword in EXCLUDED_NAME_KEYWORDS)


def _fetch_from_twse_api() -> list[str]:
    """Call the official TWSE OpenAPI to get the fund basic information summary and parse out the ETF symbols."""
    response = requests.get(TWSE_API_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    records = response.json()

    if not records:
        raise ValueError("TWSE API returned an empty list")

    sample_keys = list(records[0].keys())
    code_column = _find_column(sample_keys, CODE_COLUMN_KEYWORDS)

    if code_column is None:
        # If the code column cannot be found, print all column names for debugging
        print(f"Error: could not find fund code column, available columns: {sample_keys}")
        raise ValueError("Fund code column not found in TWSE API response")

    name_column = _find_column(sample_keys, NAME_COLUMN_KEYWORDS)
    # The listing date column is currently only used to confirm the table structure, and is not yet used for filtering
    _listing_date_column = _find_column(sample_keys, LISTING_DATE_COLUMN_KEYWORDS)

    symbols = []
    for record in records:
        code = record.get(code_column)

        if code is None or str(code).strip() == "":
            continue

        code = str(code).strip()

        if name_column is not None and _name_is_excluded(record.get(name_column)):
            continue

        symbols.append(f"{code}.TW")

    return symbols


def _fetch_from_wikipedia() -> list[str]:
    """When the official TWSE API fails, try the Wikipedia fallback pages in order."""
    for url in WIKI_FALLBACK_URLS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            tables = pd.read_html(response.text)
        except Exception:
            continue

        symbols = []
        for table in tables:
            columns = [str(col) for col in table.columns]
            code_column = _find_column(columns, CODE_COLUMN_KEYWORDS)

            if code_column is None:
                continue

            name_column = _find_column(columns, NAME_COLUMN_KEYWORDS)

            for _, row in table.iterrows():
                code = row.get(code_column)

                if pd.isna(code):
                    continue

                code = str(code).strip()
                if not code:
                    continue

                if name_column is not None and _name_is_excluded(row.get(name_column)):
                    continue

                symbols.append(f"{code}.TW")

        if symbols:
            return symbols

    return []


def get_tw_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Taiwan TWSE exchange (in the .TW suffix format used by yfinance)."""
    try:
        symbols = _fetch_from_twse_api()
        if symbols:
            return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Warning: could not fetch ETF list from TWSE official API ({e}), falling back to Wikipedia")

    try:
        symbols = _fetch_from_wikipedia()
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not fetch Taiwan ETF symbol list from either source ({e})")
        return []
