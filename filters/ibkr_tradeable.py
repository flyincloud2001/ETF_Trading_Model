# This file confirms whether an ETF can actually be traded on IBKR (Interactive Brokers), to avoid selecting ETFs whose contracts cannot be found when actually placing an order

import time

from ib_insync import IB, Stock

# Wait time in seconds between each contract query, to avoid overloading TWS/Gateway
QUERY_INTERVAL_SECONDS = 0.1


def filter_ibkr_tradeable(
    symbols: list[str],
    host: str = "127.0.0.1",
    port: int = 7497,
    client_id: int = 99,
) -> list[str]:
    """Take a list of ETF symbols and return the subset that is actually tradeable on IBKR."""
    ib = IB()

    try:
        ib.connect(host, port, clientId=client_id)
    except Exception as e:
        # If the connection fails, don't exclude any ETF; just return the original list
        print(f"Warning: could not connect to IBKR ({e}), skipping IBKR tradeability check")
        return list(symbols)

    tradeable_symbols = []

    try:
        for symbol in symbols:
            # Build the corresponding contract based on the symbol's suffix
            if symbol.endswith(".L"):
                base_symbol = symbol[: -len(".L")]
                contract = Stock(base_symbol, "LSEETF", "GBP")
            elif symbol.endswith(".T"):
                base_symbol = symbol[: -len(".T")]
                contract = Stock(base_symbol, "TSEJ", "JPY")
            elif symbol.endswith(".AX"):
                base_symbol = symbol[: -len(".AX")]
                contract = Stock(base_symbol, "ASX", "AUD")
            elif symbol.endswith(".PA"):
                base_symbol = symbol[: -len(".PA")]
                contract = Stock(base_symbol, "SBF", "EUR")
            elif symbol.endswith(".AS"):
                base_symbol = symbol[: -len(".AS")]
                contract = Stock(base_symbol, "AEB", "EUR")
            elif symbol.endswith(".KS"):
                base_symbol = symbol[: -len(".KS")]
                contract = Stock(base_symbol, "KSE", "KRW")
            elif symbol.endswith(".SW"):
                base_symbol = symbol[: -len(".SW")]
                contract = Stock(base_symbol, "EBS", "CHF")
            elif symbol.endswith(".HK"):
                base_symbol = symbol[: -len(".HK")]
                contract = Stock(base_symbol, "SEHK", "HKD")
            elif symbol.endswith(".SI"):
                base_symbol = symbol[: -len(".SI")]
                contract = Stock(base_symbol, "SGX", "SGD")
            elif symbol.endswith(".NS"):
                base_symbol = symbol[: -len(".NS")]
                contract = Stock(base_symbol, "NSE", "INR")
            elif symbol.endswith(".TW"):
                base_symbol = symbol[: -len(".TW")]
                contract = Stock(base_symbol, "TSEJ", "TWD")
            elif symbol.endswith(".SA"):
                base_symbol = symbol[: -len(".SA")]
                contract = Stock(base_symbol, "BVMF", "BRL")
            elif symbol.endswith(".MX"):
                base_symbol = symbol[: -len(".MX")]
                contract = Stock(base_symbol, "MEXI", "MXN")
            elif symbol.endswith(".IS"):
                base_symbol = symbol[: -len(".IS")]
                contract = Stock(base_symbol, "BIST", "TRY")
            elif symbol.endswith(".SR"):
                base_symbol = symbol[: -len(".SR")]
                contract = Stock(base_symbol, "TADAWUL", "SAR")
            elif symbol.endswith(".JK"):
                base_symbol = symbol[: -len(".JK")]
                contract = Stock(base_symbol, "IDX", "IDR")
            elif symbol.endswith(".JO"):
                base_symbol = symbol[: -len(".JO")]
                contract = Stock(base_symbol, "JSE", "ZAR")
            elif symbol.endswith(".WA"):
                base_symbol = symbol[: -len(".WA")]
                contract = Stock(base_symbol, "WSE", "PLN")
            elif symbol.endswith(".SN"):
                base_symbol = symbol[: -len(".SN")]
                contract = Stock(base_symbol, "BCS", "CLP")
            elif symbol.endswith(".TA"):
                base_symbol = symbol[: -len(".TA")]
                contract = Stock(base_symbol, "TASE", "ILS")
            elif symbol.endswith(".VN"):
                base_symbol = symbol[: -len(".VN")]
                contract = Stock(base_symbol, "HOSE", "VND")
            elif symbol.endswith(".TO"):
                base_symbol = symbol[: -len(".TO")]
                contract = Stock(base_symbol, "SMART", "CAD", primaryExchange="TSE")
            elif symbol.endswith(".V"):
                base_symbol = symbol[: -len(".V")]
                contract = Stock(base_symbol, "SMART", "CAD", primaryExchange="VENTURE")
            else:
                contract = Stock(symbol, "SMART", "USD")

            details = ib.reqContractDetails(contract)

            if details:
                tradeable_symbols.append(symbol)

            time.sleep(QUERY_INTERVAL_SECONDS)
    finally:
        ib.disconnect()

    return tradeable_symbols
