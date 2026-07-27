# This file turns the ETFs in "ETF_Trading_Model\data\ranked_good_universe.csv" into a Streamlit interface

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import os
import time
import glob

from trading_logic.timezone_utils import get_now_in_eastern, is_market_open, is_premarket

# ========== Parameter settings ==========
DATA_DIR = "data"
TOP_N_DAILY = 20
REQUEST_DELAY = 0.2
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1.5
RANKED_PATH = "data/ranked_good_universe.csv"

st.set_page_config(page_title="ETF Rebound Selection Model", layout="wide")


def _format_bin_range(lower: float, upper: float) -> str:
    """Format the bin boundaries into a display-friendly string; infinite boundaries are shown as the infinity symbol (∞)."""
    lower_str = "-∞" if np.isinf(lower) else f"{lower:.1f}"
    upper_str = "∞" if np.isinf(upper) else f"{upper:.1f}"
    return f"[{lower_str}, {upper_str})"


def _fetch_yesterday_status(row):
    """
    Fetch the most recent 10 days of data for one ETF, compute yesterday's close-vs-open
    percentage return, and calculate the distance from this ETF's best-bin midpoint.
    Returns (dict, None) on success, or (None, error reason string) on failure.
    """
    symbol = row["symbol"]

    # Retry up to MAX_RETRIES times when fetching data fails, waiting a bit longer between each retry
    hist = None
    last_error = "Unknown error"
    for attempt in range(MAX_RETRIES):
        try:
            hist = yf.Ticker(symbol).history(period="10d", auto_adjust=True)
            if not hist.empty:
                break
            last_error = "Returned data is empty"
        except Exception as e:
            hist = None
            last_error = f"{type(e).__name__}: {e}"

        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))

    if hist is None or hist.empty:
        return None, last_error

    # Sometimes, at this point before the US market opens, Yahoo hasn't finished processing
    # the latest day's data yet, so Open and Close will be NaN.
    # Filter out these rows with missing values first; what remains is genuinely usable complete trading-day data
    valid_hist = hist.dropna(subset=["Open", "Close"])

    if len(valid_hist) < 1:
        return None, "Recent data is all missing; Yahoo data may not be updated yet, try again later"

    # hist.index is timestamped in Eastern Time, so we can't compare it against local system time.
    # Use the timezone info carried by valid_hist.index[-1] itself to work out what "now" is in Eastern Time
    now_in_market_tz = pd.Timestamp.now(tz=valid_hist.index[-1].tz)
    last_valid_date = valid_hist.index[-1].date()
    today_date_in_market_tz = now_in_market_tz.date()

    # Comparing dates alone isn't enough; if it's already past the 4pm Eastern market close, that day's data is actually complete
    market_close_time = now_in_market_tz.replace(hour=16, minute=0, second=0, microsecond=0)
    last_row_still_in_progress = (
        last_valid_date == today_date_in_market_tz and now_in_market_tz < market_close_time
    )

    if last_row_still_in_progress:
        if len(valid_hist) < 2:
            return None, "Only today's data is available; yesterday's data is not yet complete"
        yesterday_row = valid_hist.iloc[-2]
    else:
        yesterday_row = valid_hist.iloc[-1]

    yesterday_open = yesterday_row["Open"]
    yesterday_close = yesterday_row["Close"]
    yesterday_date = yesterday_row.name.strftime("%Y-%m-%d")

    if yesterday_open == 0 or pd.isna(yesterday_open) or pd.isna(yesterday_close):
        return None, "Yesterday's open or close price is 0 or missing"

    # Yesterday's close-vs-open return, converted to percentage form (e.g. 1.02 becomes 2.0)
    yesterday_return = yesterday_close / yesterday_open
    yesterday_return_pct = yesterday_return * 100 - 100

    # x and y are taken directly from ranked_good_universe.csv, representing this ETF's historical best-bin statistics
    x = row["x"]
    y = row["y"]

    # The midpoint of this ETF's best bin; when the first or last bin boundary is infinite, fall back to using the finite end as the reference point
    bin_lower = row["best_bin_lower"]
    bin_upper = row["best_bin_upper"]
    if np.isinf(bin_lower):
        best_bin_mid = bin_upper
    elif np.isinf(bin_upper):
        best_bin_mid = bin_lower
    else:
        best_bin_mid = (bin_lower + bin_upper) / 2

    distance = abs(yesterday_return_pct - best_bin_mid)

    return {
        "symbol": symbol,
        "country": row["country"],
        "original_rank": row["rank"],
        "yesterday_date": yesterday_date,
        "yesterday_return_pct": round(float(yesterday_return_pct), 4),
        "x": x,
        "y": y,
        "best_bin_lower": bin_lower,
        "best_bin_upper": bin_upper,
        "distance": round(float(distance), 4),
    }, None


def _run_daily_analysis(ranked_df: pd.DataFrame, log_placeholder, progress_bar) -> pd.DataFrame:
    """Call _fetch_yesterday_status for every ETF in ranked_df, updating the progress bar and text log along the way."""
    records = []
    total = len(ranked_df)
    logs = []

    for i, (_, row) in enumerate(ranked_df.iterrows()):
        result, error_reason = _fetch_yesterday_status(row)

        if result is not None:
            records.append(result)
        else:
            logs.append(f"{row['symbol']} data fetch failed, skipped, reason: {error_reason}")

        time.sleep(REQUEST_DELAY)

        if i % 10 == 0 or i == total - 1:
            progress_bar.progress(min((i + 1) / total, 1.0))
            logs.append(f"Processed {i + 1}/{total} ETFs")
            log_placeholder.text("\n".join(logs[-10:]))

    return pd.DataFrame(records)


def _plot_daily_results(top_df: pd.DataFrame):
    """Plot a bar chart of yesterday's return for today's candidate ETFs, labeling each bar with that ETF's best-bin range."""
    fig, ax = plt.subplots(figsize=(14, 5))
    x_pos = np.arange(len(top_df))

    bars = ax.bar(x_pos, top_df["yesterday_return_pct"])

    for bar, (_, row) in zip(bars, top_df.iterrows()):
        bin_range_label = _format_bin_range(row["best_bin_lower"], row["best_bin_upper"])
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            bin_range_label,
            ha="center",
            va="bottom" if height >= 0 else "top",
            fontsize=8,
            rotation=90,
        )

    ax.set_xticks(x_pos)
    ax.set_xticklabels(top_df["symbol"], rotation=45)
    ax.set_xlabel("ETF Symbol")
    ax.set_ylabel("Yesterday's Return (%)")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title(f"Today's Top {len(top_df)} ETFs: Yesterday's Return vs Best Bin Range")

    return fig


def main():
    st.title("ETF Rebound Selection Model")
    st.caption("Manually triggered; not scheduled automatically")

    ranked_df = pd.read_csv(RANKED_PATH)

    tab1, tab2 = st.tabs(["Candidate ETF Overview", "Daily Analysis"])

    # ---- Tab 1: Candidate ETF Overview ----
    with tab1:
        st.subheader(f"Candidate ETF Pool — {len(ranked_df)} total")
        st.caption(f"Loaded from {RANKED_PATH}")

        countries = sorted(ranked_df["country"].dropna().unique())

        for country in countries:
            country_df = ranked_df[ranked_df["country"] == country].sort_values("rank")
            with st.expander(f"{country} ({len(country_df)})"):
                st.dataframe(
                    country_df[["rank", "symbol", "country", "x", "y"]].rename(
                        columns={
                            "rank": "Rank",
                            "symbol": "Symbol",
                            "country": "Country",
                            "x": "Up Ratio %",
                            "y": "Avg Up Move",
                        }
                    ),
                    use_container_width=True,
                )

    # ---- Tab 2: Daily Analysis ----
    with tab2:
        st.subheader("Run Daily Analysis")

        now_eastern = get_now_in_eastern()
        if is_market_open():
            market_status = "Open"
        elif is_premarket():
            market_status = "Pre-market"
        else:
            market_status = "After-hours (or non-trading day)"

        st.write(f"Current Eastern Time: {now_eastern.strftime('%Y-%m-%d %H:%M:%S')} ({market_status})")
        st.write(
            f"Clicking the button will fetch the latest data for all candidate ETFs "
            f"and find the top {TOP_N_DAILY} that fell yesterday and are closest to their best bin midpoint"
        )

        if st.button("Start Analysis"):
            progress_bar = st.progress(0.0)
            log_placeholder = st.empty()

            with st.spinner("Fetching latest data and calculating..."):
                result_df = _run_daily_analysis(ranked_df, log_placeholder, progress_bar)

            st.success(f"Analysis complete — successfully retrieved data for {len(result_df)} ETFs")

            # Save the full results to a file whose name includes the date, so each day's run leaves a record
            os.makedirs(DATA_DIR, exist_ok=True)
            snapshot_date = get_now_in_eastern().strftime("%Y-%m-%d")
            snapshot_path = os.path.join(DATA_DIR, f"snapshot_{snapshot_date}.csv")
            result_df.to_csv(snapshot_path, index=False)
            st.write(f"Full results saved to {snapshot_path}")

            # Keep only ETFs that fell yesterday (yesterday_return_pct less than 0)
            down_only_df = result_df[result_df["yesterday_return_pct"] < 0].copy()

            # Sort by distance ascending, take the top TOP_N_DAILY, then re-sort by original rank and mark today's rank
            top_df = down_only_df.sort_values("distance").head(TOP_N_DAILY).copy()
            top_df = top_df.sort_values("original_rank").reset_index(drop=True)
            top_df["today_rank"] = top_df.index + 1

            st.subheader(f"Today's Top {len(top_df)} (sorted by original rank)")
            st.dataframe(
                top_df[
                    [
                        "today_rank",
                        "original_rank",
                        "symbol",
                        "country",
                        "yesterday_return_pct",
                        "x",
                        "distance",
                        "y",
                    ]
                ].rename(
                    columns={
                        "today_rank": "Today's Rank",
                        "original_rank": "Original Rank",
                        "symbol": "Symbol",
                        "country": "Country",
                        "yesterday_return_pct": "Yesterday's Return %",
                        "x": "X Value",
                        "distance": "Distance",
                        "y": "Y Value",
                    }
                ),
                use_container_width=True,
            )

            st.subheader("Yesterday's Return vs Best Bin Range Chart")
            fig = _plot_daily_results(top_df)
            st.pyplot(fig)

            st.subheader(f"Full Status for All {len(result_df)} ETFs Yesterday")
            st.dataframe(result_df.sort_values("distance"), use_container_width=True)


if __name__ == "__main__":
    main()
