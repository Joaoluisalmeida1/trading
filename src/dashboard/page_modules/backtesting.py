import streamlit as st
import pandas as pd
import datetime  # Import the datetime module

from backtesting.data_loader import fetch_ohlcv
from backtesting.engine      import run_backtest
from backtesting.report      import show_report

from trading.strategy import (
    ma_crossover,
    rsi_strategy,
    rsi_reverse_strategy,
    reverse_rsi_with_filters,
    buy_and_hold_strategy,
    volatility_breakout_strategy,
    pullback_trend_strategy
)

STRATEGIES = {
    "MA Crossover":    ma_crossover,
    "RSI Classic":     rsi_strategy,
    "RSI Reverse":     rsi_reverse_strategy,
    "Buy & Hold":      buy_and_hold_strategy,
    "Refined Reverse RSI": reverse_rsi_with_filters,
    "Volatility Breakout Strategy": volatility_breakout_strategy,
    "Pullback Trend": pullback_trend_strategy,
}

def render_backtesting(exchange):
    st.title("🔍 Backtesting Module")
    if exchange is None:
        st.warning("Binance not initialized. Check API keys.")
        return

    # --- Inputs ---
    symbol       = st.text_input("Symbol", "BTC/USDC")
    timeframe    = st.selectbox("Timeframe", ["5m","1h","4h","1d"], index=0)
    initial_cash = st.number_input("Initial Capital (USDC)", 1000.0, step=100.0)

    # --- NEW: Date range selection ---
    # Replaces the 'limit' slider with a date range picker.
    today = datetime.date.today()
    default_start_date = today - datetime.timedelta(days=365)
    
    date_range = st.date_input(
        "Select Backtest Date Range",
        value=(default_start_date, today),  # Creates a range selector
        min_value=datetime.date(2017, 1, 1), # Set a reasonable minimum date
        max_value=today,
        format="YYYY/MM/DD",
    )

    # --- Commission ---
    commission_bps = st.number_input(
        "Commission (basis points)", min_value=0.0, max_value=100.0,
        value=10.0, step=1.0,
        help="0.1% = 10 bps"
    )
    commission_rate = commission_bps / 10000.0

    # --- Strategy selector ---
    strat_name = st.selectbox("Strategy", list(STRATEGIES.keys()))
    strat_fn   = STRATEGIES[strat_name]

    # --- Strategy params (Unchanged) ---
    params = {}
    if strat_name == "MA Crossover":
        params["short_window"] = st.number_input("Short MA Window", 5, 100, 20, step=1)
        params["long_window"]  = st.number_input("Long MA Window", 10, 200, 50, step=1)
    elif strat_name == "RSI Classic" or strat_name == "RSI Reverse":
        params["window"]      = st.number_input("RSI Window", 5, 50, 14, step=1)
        params["overbought"]  = st.slider("Overbought Level", 50, 100, 70, step=1)
        params["oversold"]    = st.slider("Oversold Level", 0, 50, 30, step=1)
    elif strat_name == "Volatility Breakout Strategy":
        params = {
            "bb_window": st.number_input("BB Period", 5, 50, 20, step=1),
            "bb_dev": st.number_input("BB Std Dev Multiplier", 0.5, 3.0, 1.5, step=0.1),
            "squeeze_window": st.number_input("Squeeze Window", 5, 200, 20, step=5),
            "volume_window": st.number_input("Volume MA Window", 5, 100, 20, step=5),
            "volume_multiplier": st.number_input("Volume Multiplier", 0.5, 3.0, 1.0, step=0.1),
            "atr_window": st.number_input("ATR Period", 5, 50, 14, step=1),
        }

    sl_pct = st.number_input(
        "Stop-Loss (%)", 0.0, 100.0, 2.0, step=0.1,
        help="e.g. 2% stop-loss"
    )
    stop_loss = sl_pct / 100.0

    # --- Run backtest ---
    if st.button("Run Backtest", key="bt_run"):
        # Ensure a valid date range is selected
        if len(date_range) != 2:
            st.error("Please select a valid date range (start and end date).")
            return

        start_date, end_date = date_range

        # Convert start_date to a 'since' timestamp in milliseconds for the API
        since_timestamp = int(datetime.datetime.combine(start_date, datetime.time.min).timestamp() * 1000)

        with st.spinner("Fetching data…"):
            # UPDATED: Call fetch_ohlcv with the 'since' timestamp.
            # This assumes your fetch_ohlcv function is modified to accept 'since'
            # instead of 'limit'. It should fetch all data from that start time to now.
            df = fetch_ohlcv(symbol, timeframe=timeframe, since=since_timestamp)

        if df.empty:
            st.error("Could not fetch data for the selected range.")
            return
            
        # Filter the dataframe to ensure it's within the selected end_date
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max).replace(tzinfo=df.index.tz)
        df = df[df.index <= end_datetime]

        with st.spinner("Generating signals…"):
            sig_df = strat_fn(df, **params)

        with st.spinner("Simulating trades…"):
            equity_df, trades_df = run_backtest(
                df,
                sig_df["signal"],
                initial_cash=initial_cash,
                commission_rate=commission_rate,
                stop_loss=stop_loss
            )

        show_report(equity_df, trades_df, price_df=df)

