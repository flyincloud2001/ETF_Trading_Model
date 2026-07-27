# This file fetches all Hong Kong HKEX exchange ETF symbols

import io

import pandas as pd
import requests

# Official HKEX ETF list CSV URL
HKEX_ETF_LIST_URL = "https://www.hkex.com.hk/eng/etfrc/ListOfAllETF/ETFList.csv"

# Spoofed browser User-Agent, to avoid being rejected
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Keywords that must be excluded from the name (inverse, short, leveraged, bull, leveraged-inverse ETFs)
EXCLUDED_NAME_KEYWORDS = (
    "INVERSE",
    "BEAR",
    "SHORT",
    "LEVERAGED",
    "BULL",
    "2X",
    "3X",
    "-2",
    "-3",
    "L&I",
)


def get_hk_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Hong Kong HKEX exchange (in the .HK suffix format used by yfinance)."""
    try:
        response = requests.get(HKEX_ETF_LIST_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()

        # This CSV's encoding is inconsistent; try utf-8-sig first, then fall back to latin-1
        try:
            df = pd.read_csv(io.BytesIO(response.content), encoding="utf-8-sig")
        except Exception:
            df = pd.read_csv(io.BytesIO(response.content), encoding="latin-1")

        # Print all column names for debugging
        print(f"HKEX ETF list column names: {list(df.columns)}")

        # Dynamically locate the ticker code column and name column
        code_column = next((col for col in df.columns if "code" in col.lower()), None)
        name_column = next((col for col in df.columns if "name" in col.lower()), None)

        if code_column is None or name_column is None:
            print(f"Error: could not find code or name column, columns are {list(df.columns)}")
            return []
    except Exception as e:
        print(f"Error: could not download or parse HKEX ETF list ({e})")
        return []

    symbols = []
    for _, row in df.iterrows():
        code = row.get(code_column)
        name = row.get(name_column)

        if pd.isna(code) or pd.isna(name):
            continue

        name_upper = str(name).upper()

        # Exclude inverse, short, and leveraged ETFs
        if any(keyword in name_upper for keyword in EXCLUDED_NAME_KEYWORDS):
            continue

        # Zero-pad the ticker code to 4 digits, then append the .HK suffix
        code_str = str(code).strip().split(".")[0].zfill(4)
        symbols.append(f"{code_str}.HK")

    # Remove duplicates while preserving original order
    return list(dict.fromkeys(symbols))
