# This file fetches all Japanese TSE exchange ETF symbols

import io

import pdfplumber
import requests

# Official JPX ETF list PDF URL
JPX_ETF_PDF_URL = (
    "https://www.jpx.co.jp/english/equities/products/etfs/tvdivq000001j45s-att/b5b4pj000002nyru.pdf"
)

# Spoofed browser User-Agent, to avoid being rejected
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get_jp_etf_symbols() -> list[str]:
    """Return the list of all ETF symbols on the Japanese TSE exchange (in the .T suffix format used by yfinance)."""
    try:
        response = requests.get(JPX_ETF_PDF_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Error: could not download JPX ETF list PDF ({e})")
        return []

    codes = []

    try:
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    if not table:
                        continue

                    header = table[0]
                    if "Code" not in header:
                        continue

                    code_index = header.index("Code")

                    for row in table[1:]:
                        if code_index >= len(row):
                            continue

                        code = row[code_index]
                        if code is None:
                            continue

                        code = code.strip()

                        # Exclude empty strings, strings containing whitespace, and the table header row itself ("Code")
                        if not code or " " in code or code == "Code":
                            continue

                        codes.append(code)
    except Exception as e:
        print(f"Error: could not parse JPX ETF list PDF ({e})")
        return []

    symbols = [f"{code}.T" for code in codes]

    # Remove duplicates while preserving original order
    return list(dict.fromkeys(symbols))
