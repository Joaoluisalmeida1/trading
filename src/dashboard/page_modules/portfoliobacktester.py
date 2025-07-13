import streamlit as st
import pandas as pd
import datetime

# --- Assume these are in your project structure ---
from backtesting.data_loader import fetch_ohlcv
from backtesting.portfolio_engine import run_portfolio_backtest # Using the new engine
from backtesting.report_portfolio import show_portfolio_report
from trading.strategy import (
    rsi_reverse_strategy,
    reverse_rsi_with_filters,
    # Add other strategies you want to test at a portfolio level
)

# --- Simplified strategy list for portfolio testing ---
PORTFOLIO_STRATEGIES = {
    "RSI Reverse":     rsi_reverse_strategy,
    "Refined Reverse RSI": reverse_rsi_with_filters,
}

def render_portfolio_backtesting(exchange):
    st.title("📈 Portfolio Backtester")
    st.markdown("""
    Test a single strategy across multiple trading pairs with a shared pool of capital.
    """)

    if exchange is None:
        st.warning("Binance not initialized. Check API keys.")
        return

    # --- Portfolio Inputs ---
    symbols_input = st.text_area(
        "Symbols (comma-separated)", "BTC/USDC, ETH/USDC, SOL/USDC"
    )
    symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]

    timeframe = st.selectbox("Timeframe", ["1h", "4h", "1d"], index=1)
    initial_cash = st.number_input("Initial Capital (USDC)", 1000.0, step=100.0)

    # --- NEW: Position Sizing Input ---
    allocation_pct = st.slider(
        "Allocation per Trade (%)", 
        min_value=1, max_value=100, value=25, step=1,
        help="Percentage of total equity to allocate to each new position."
    )
    allocation = allocation_pct / 100.0

    # --- Date Range and Commission ---
    today = datetime.date.today()
    default_start_date = today - datetime.timedelta(days=365)
    date_range = st.date_input(
        "Select Backtest Date Range",
        value=(default_start_date, today),
        min_value=datetime.date(2017, 1, 1),
        max_value=today,
        format="YYYY/MM/DD",
    )
    commission_bps = st.number_input(
        "Commission (basis points)", value=10.0, step=1.0
    )
    commission_rate = commission_bps / 10000.0
    
    # --- Strategy Selection ---
    strat_name = st.selectbox("Strategy", list(PORTFOLIO_STRATEGIES.keys()))
    strat_fn = PORTFOLIO_STRATEGIES[strat_name]

    params = {} # Simplified params for this example
    if "RSI" in strat_name:
        params["window"] = st.number_input("RSI Window", 5, 50, 14, step=1)
        params["overbought"] = st.slider("Overbought", 50, 100, 70)
        params["oversold"] = st.slider("Oversold", 0, 50, 30)
    
    sl_pct = st.number_input("Stop-Loss (%)", 0.0, 100.0, 5.0, step=0.1)
    stop_loss = sl_pct / 100.0

    # --- Run Portfolio Backtest ---
    if st.button("Run Portfolio Backtest", key="pbt_run"):
        if not symbols:
            st.error("Please enter at least one symbol.")
            return
        if len(date_range) != 2:
            st.error("Please select a valid date range.")
            return

        start_date, end_date = date_range
        since = int(datetime.datetime.combine(start_date, datetime.time.min).timestamp() * 1000)
        
        price_data = {}
        signal_data = {}

        # --- Data Fetching and Signal Generation ---
        with st.spinner(f"Fetching data and generating signals for {len(symbols)} pairs..."):
            for symbol in symbols:
                df = fetch_ohlcv(exchange, symbol, timeframe=timeframe, since=since)
                
                if not df.empty:
                    end_dt = datetime.datetime.combine(end_date, datetime.time.max).replace(tzinfo=df.index.tz)
                    df = df[df.index <= end_dt]
                    price_data[symbol] = df
                    signal_data[symbol] = strat_fn(df, **params)["signal"]

        if not price_data:
            st.error("Could not fetch data for any of the specified symbols.")
            return
            
        # --- Simulation ---
        with st.spinner("Simulating portfolio trades..."):
            equity_df, trades_df = run_portfolio_backtest(
                price_data=price_data,
                signal_data=signal_data,
                initial_cash=initial_cash,
                allocation=allocation,
                commission_rate=commission_rate,
                stop_loss=stop_loss
            )

        st.success("Backtest complete!")
        # You might need to adapt your show_report function slightly for portfolio results
        st.session_state['portfolio_results'] = {
            "equity_df": equity_df,
            "trades_df": trades_df,
            "price_data": price_data
        }
    # --- FIX #2: Display the report if results exist in session state ---
    # This block now runs independently of the button click. It will run
    # on the initial run (after the button is clicked) and on every
    # subsequent rerun caused by the filter widgets.
    if 'portfolio_results' in st.session_state:
        results = st.session_state['portfolio_results']
        st.success("Backtest complete! You can now filter the results below.")
        
        show_portfolio_report(
            equity_df=results["equity_df"],
            trades_df=results["trades_df"],
            price_data=results["price_data"]
        )
