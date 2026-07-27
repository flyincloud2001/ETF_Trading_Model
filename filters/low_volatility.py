# This file defines the low-volatility standard for a given country's ETFs
# The low-volatility standard is: use the annualized standard deviation of close-to-close daily returns over the past 10 years as the ranking basis, then select the ETFs in the top 20% of that ranking

import math

import yfinance as yf

# Minimum number of close-price rows required for the calculation; below this is considered insufficient data
MIN_REQUIRED_ROWS = 500
# Number of trading days used for annualizing volatility
TRADING_DAYS_PER_YEAR = 252
# Proportion used to select the top 20% by rank
TOP_PERCENTAGE = 0.9


def get_annualized_volatility(symbol: str) -> float | None:
    """Calculate a single ETF's annualized volatility, for use in external ranking."""
    try:
        hist = yf.Ticker(symbol).history(period="10y", auto_adjust=True)

        if hist is None or len(hist) < MIN_REQUIRED_ROWS:
            return None

        # Close-to-close daily returns
        daily_returns = hist["Close"].pct_change()

        # Annualized volatility = standard deviation of daily returns x sqrt(252)
        annualized_volatility = daily_returns.std() * math.sqrt(TRADING_DAYS_PER_YEAR)

        return float(annualized_volatility)
    except Exception:
        return None


def filter_low_volatility(symbols: list[str]) -> list[str]:
    """Take a list of ETF symbols and return the subset ranked in the top 20% by annualized volatility."""
    # Calculate the annualized volatility for each symbol, filtering out any symbol that failed to fetch or has insufficient data
    volatilities = []
    for symbol in symbols:
        volatility = get_annualized_volatility(symbol)
        if volatility is not None:
            volatilities.append((symbol, volatility))

    if not volatilities:
        return []

    # Sort by annualized volatility from low to high
    volatilities.sort(key=lambda item: item[1])

    # Take the top 20%
    top_count = math.ceil(len(volatilities) * TOP_PERCENTAGE)

    return [symbol for symbol, _volatility in volatilities[:top_count]]
