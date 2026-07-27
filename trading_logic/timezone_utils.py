# Timezone handling (US Eastern time vs. Taiwan time)

import pandas as pd

# Start and end times of the regular trading session (US Eastern time)
MARKET_OPEN_TIME = pd.Timestamp("09:30").time()
MARKET_CLOSE_TIME = pd.Timestamp("16:00").time()

# Start time of the premarket session (US Eastern time)
PREMARKET_OPEN_TIME = pd.Timestamp("04:00").time()


def get_now_in_eastern() -> pd.Timestamp:
    """Return the current time in US Eastern time."""
    return pd.Timestamp.now(tz="America/New_York")


def is_market_open() -> bool:
    """Determine whether the current US Eastern time falls within regular trading hours (Monday to Friday, 09:30-16:00)."""
    now = get_now_in_eastern()

    if now.weekday() > 4:
        return False

    return MARKET_OPEN_TIME <= now.time() < MARKET_CLOSE_TIME


def is_premarket() -> bool:
    """Determine whether the current US Eastern time falls within the premarket session (Monday to Friday, 04:00-09:30)."""
    now = get_now_in_eastern()

    if now.weekday() > 4:
        return False

    return PREMARKET_OPEN_TIME <= now.time() < MARKET_OPEN_TIME
