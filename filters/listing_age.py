# Filter for ETFs that have been listed for at least 15 years

from datetime import datetime, timezone

import yfinance as yf

# Minimum listing age threshold, in years
MIN_LISTING_YEARS = 15
# Average number of days per year (accounting for leap years)
DAYS_PER_YEAR = 365.25


def passes_listing_age(symbol: str) -> bool:
    """Determine whether a single ETF has been listed for at least 15 years."""
    try:
        hist = yf.Ticker(symbol).history(period="max", auto_adjust=True)

        if hist is None or hist.empty:
            return False

        # Treat the date of the earliest historical row as the listing date
        listing_date = hist.index[0]
        if listing_date.tzinfo is not None:
            now = datetime.now(timezone.utc).astimezone(listing_date.tzinfo)
        else:
            now = datetime.now()

        years_listed = (now - listing_date).days / DAYS_PER_YEAR

        return years_listed >= MIN_LISTING_YEARS
    except Exception:
        return False
