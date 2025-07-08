import streamlit as st
import pandas as pd

from backtesting.data_loader import fetch_ohlcv
from backtesting.engine      import run_backtest
from backtesting.report      import show_report

from trading.strategy import (
    ma_crossover,
    rsi_strategy,
    rsi_reverse_strategy,
    reverse_rsi_with_filters,
    buy_and_hold_strategy,
)

STRATEGIES = {
    "MA Crossover":    ma_crossover,
    "RSI Classic":     rsi_strategy,
    "RSI Reverse":     rsi_reverse_strategy,
    "Buy & Hold":      buy_and_hold_strategy,
    "Refined Reverse RSI": reverse_rsi_with_filters,
}

def render_backtesting(exchange):
    st.title("🔍 Backtesting Module")
    if exchange is None:
        st.warning("Binance not initialized. Check API keys.")
        return

    # --- Inputs ---
    symbol       = st.text_input("Symbol", "BTC/USDC")
    timeframe    = st.selectbox("Timeframe", ["1h","4h","1d"], index=0)
    limit        = st.slider("Bars", 50, 5000, 200, step=50)
    initial_cash = st.number_input("Initial Capital (USDC)", 1000.0, step=100.0)

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

    # --- Strategy params ---
    params = {}
    if strat_name == "MA Crossover":
        params["short_window"] = st.number_input("Short MA Window", 5, 100, 20, step=1)
        params["long_window"]  = st.number_input("Long MA Window", 10, 200, 50, step=1)
    elif strat_name == "RSI Classic" or strat_name == "RSI Reverse":
        params["window"]      = st.number_input("RSI Window", 5, 50, 14, step=1)
        params["overbought"]  = st.slider("Overbought Level", 50, 100, 70, step=1)
        params["oversold"]    = st.slider("Oversold Level", 0, 50, 30, step=1)
    

    sl_pct = st.number_input(
        "Stop-Loss (%)", 0.0, 100.0, 2.0, step=0.1,
        help="e.g. 2% stop-loss"
    )
    stop_loss = sl_pct / 100.0


    # --- Run backtest ---
    if st.button("Run Backtest", key="bt_run"):
        with st.spinner("Fetching data…"):
            df = fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

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
