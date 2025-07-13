import streamlit as st
from streamlit_autorefresh import st_autorefresh
from trading.strategy_bot import StrategyBot
import pandas as pd
import datetime

def render_autotrader(exchange):
    st.title("⚙️ AutoTrader Dashboard")

    # Use auto-refresh to run the bot check every minute
    st_autorefresh(interval=60 * 1000, key="autotrader_refresh")

    if 'trader' not in st.session_state:
        st.warning("Trader not initialized. Please visit the Live Trading page first.")
        return

    if 'bot_logs' not in st.session_state:
        st.session_state.bot_logs = []
    if 'bot_running' not in st.session_state:
        st.session_state.bot_running = False
    if 'last_check_time' not in st.session_state:
        st.session_state.last_check_time = "Never"
    # --- Bot Configuration Panel ---
    st.header("1. Bot Configuration")
    with st.form(key="bot_config_form"):
        strategy_name = st.selectbox("Select Strategy", ["Reverse RSI", "Refined Reverse RSI"])
        timeframe = st.selectbox("Select Timeframe", ["4h", "1d"])
        symbols_input = st.text_area("Symbols to Trade (comma-separated)", "BTC/USDC, ETH/USDC, SOL/USDC, ADA/USDT, DOGE/USDT, SHIB/USDT, XRP/USDT, PEPE/USDT, NEIRO/USDT, LTC/USDT, UNI/USDT,  WLD/USDT, TRUMP/USDT")
        allocation_usd = st.number_input("Allocation per Trade (USDC)", min_value=10.0, value=100.0)
        
        # --- NEW: Add the Stop-Loss setting ---
        stop_loss_pct = st.number_input("Stop Loss (%)", min_value=1.0, max_value=50.0, value=8.0, step=0.5)
        
        submitted = st.form_submit_button("Save Configuration")
        if submitted:
            st.session_state.bot_config = {
                "strategy_name": strategy_name,
                "timeframe": timeframe,
                "symbols": [s.strip().upper() for s in symbols_input.split(',')],
                "allocation_usd": allocation_usd,
                "stop_loss_pct": stop_loss_pct, # Save the new setting
                "strategy_params": { # Default optimized params
                    "window": 7, "overbought": 80, "oversold": 20 
                },
                "rsi_window": 7 
            }
            st.success("Configuration saved!")

    if 'bot_config' not in st.session_state:
        st.info("Please configure and save the bot settings to begin.")
        return

    # --- Bot Control and Status Panel ---
    st.header("2. Bot Control")
    
    # Initialize the bot in session state if it doesn't exist
    if 'bot' not in st.session_state:
        st.session_state.bot = StrategyBot(st.session_state.bot_config, st.session_state.trader)

    col1, col2, col3 = st.columns(3)
    if col1.button("▶️ START BOT", use_container_width=True):
        st.session_state.bot_running = True
        st.success("Bot has been started.")

    if col2.button("⏹️ STOP BOT", use_container_width=True):
        st.session_state.bot_running = False
        st.error("Bot has been stopped.")

    if col3.button("Run Check Now  manualmente", use_container_width=True):
        if st.session_state.bot_running:
            st.info("Manual check triggered...")
            # The logic below will handle the execution
        else:
            st.warning("Bot is stopped. Cannot run a manual check.")


    # --- Live Status and Execution Logic ---
    if st.session_state.get("bot_running", False):
        st.success("✅ Bot is RUNNING")
        
        # This is where the bot does its work on each page refresh
        try:
            new_logs = st.session_state.bot.run_check()
            st.session_state.bot_logs.extend(new_logs)
            st.session_state.bot_logs = st.session_state.bot_logs[-50:]
            # Record the successful check time
            st.session_state.last_check_time = datetime.datetime.now().strftime("%H:%M:%S")
        except Exception as e:
            st.error(f"An error occurred during bot execution: {e}")
            st.session_state.bot_running = False # Stop the bot on fatal error
    else:
        st.error("❌ Bot is STOPPED")
   
    st.info(f"Last successful check at: **{st.session_state.last_check_time}**")
    st.divider()

        # --- NEW: Bot Log and Data Inspector ---
    st.header("3. Live Bot Monitor")
    log_col, data_col = st.columns([1, 1])

    with log_col:
        st.subheader("📜 Live Log")
        log_container = st.container(height=300)
        # Display logs in reverse chronological order for easy viewing
        for log in reversed(st.session_state.bot_logs):
            if "ERROR" in log:
                log_container.error(log)
            elif "signal" in log:
                log_container.success(log)
            else:
                log_container.write(log)

    with data_col:
        st.subheader("🕵️ Data Inspector")
        st.write("Last fetched DataFrame:")
        # Display the last raw dataframe the bot tried to process
        if st.session_state.get('bot') and hasattr(st.session_state.bot, 'last_fetched_df') and st.session_state.bot.last_fetched_df is not None:
            st.dataframe(st.session_state.bot.last_fetched_df.tail(), use_container_width=True)
        else:
            st.info("No data fetched yet.")


    # --- Display current positions managed by the bot ---
    st.header("4. Bot Portfolio")
    open_positions_df = st.session_state.trader.get_open_positions()
    total_equity = st.session_state.trader.get_total_equity()

    # --- NEW: Calculation for Performance Metrics ---
    if not open_positions_df.empty:
        # Calculate the total cost basis of all open positions
        invested_capital = (open_positions_df['Amount'] * open_positions_df['Entry Price']).sum()
        # Sum the unrealized P&L from all positions
        total_pnl_usd = open_positions_df['P&L ($)'].sum()

        # 1. P&L as a percentage of the capital that is actually invested
        pnl_on_invested_pct = (total_pnl_usd / invested_capital) * 100 if invested_capital > 0 else 0
        
        # 2. P&L as a percentage of the entire account's equity
        pnl_on_total_equity_pct = (total_pnl_usd / total_equity) * 100 if total_equity > 0 else 0

        # --- Display the new metrics ---
        kpi_cols = st.columns(2)
        kpi_cols[0].metric(
            label="Return on Invested Capital",
            value=f"{pnl_on_invested_pct:.2f}%",
            help="The combined P&L of your open positions as a percentage of the capital used to open them."
        )
        kpi_cols[1].metric(
            label="Return on Total Equity",
            value=f"{pnl_on_total_equity_pct:.2f}%",
            help="The combined P&L of your open positions as a percentage of your total account value."
        )
        st.markdown("---")


    if not open_positions_df.empty:
        st.subheader("Live Position Details")
        st.dataframe(open_positions_df, use_container_width=True)
    else:
        st.info("Bot has no open positions.")