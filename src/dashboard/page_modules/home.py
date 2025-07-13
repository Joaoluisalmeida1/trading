import streamlit as st
import pandas as pd
import plotly.express as px
from trading.trader import Trader # Assuming your Trader class is accessible
from streamlit_autorefresh import st_autorefresh

def render_home(exchange):
    """
    Renders the main dashboard homepage, showing a comprehensive overview
    of the trading account's status and performance.
    """
    st.title("🤖 Dashboard Home")

    # --- Auto-refresh the page every 60 seconds ---
    st_autorefresh(interval=60000, key="home_refresher")

    # Use the Trader class for all data fetching to ensure consistency
    if 'trader' not in st.session_state:
        st.warning("Trader not initialized. Please visit the Live Trading page first.")
        return
        
    trader = st.session_state.trader
    st.success("✅ Connected to Binance")

    # --- 1. Key Performance Indicators (KPIs) ---
    st.header("Key Metrics")

    # Fetch all data points at once
    total_equity = trader.get_total_equity()
    usdc_balance = trader.get_usdc_balance()
    pnl_24h_usd, pnl_24h_pct = trader.get_24h_performance()

    kpi_cols = st.columns(3)
    kpi_cols[0].metric(label="📈 Total Account Equity", value=f"${total_equity:,.2f}")
    kpi_cols[1].metric(label="💰 Available Buying Power", value=f"${usdc_balance:,.2f}")
    kpi_cols[2].metric(label="⏱️ 24h P&L", value=f"${pnl_24h_usd:,.2f}", delta=f"{pnl_24h_pct:.2f}%")
    st.divider()

    # --- 2. Portfolio Allocation ---
    st.header("Portfolio Breakdown")

    open_positions_df = trader.get_open_positions()
    
    # Add USDC balance to the DataFrame for the pie chart
    portfolio_df = open_positions_df.copy()
    if 'Value (USDC)' in portfolio_df.columns:
        usdc_row = pd.DataFrame([{'Symbol': 'USDC', 'Value (USDC)': usdc_balance}])
        chart_df = pd.concat([portfolio_df[['Symbol', 'Value (USDC)']], usdc_row], ignore_index=True)
    else:
        chart_df = pd.DataFrame([{'Symbol': 'USDC', 'Value (USDC)': usdc_balance}])

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("📊 Allocation Chart")
        fig = px.pie(
            chart_df,
            names='Symbol',
            values='Value (USDC)',
            hole=0.4,
            title='Portfolio Allocation by Value',
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📋 Asset Details")
        st.dataframe(open_positions_df, use_container_width=True)

    st.divider()

    # --- 3. The Ledger (Consistent with Live Trading Page) ---
    st.header("Account Activity")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("⏳ Open Orders")
        open_orders_df = trader.get_open_orders()
        if not open_orders_df.empty:
            st.dataframe(open_orders_df, use_container_width=True)
            if st.button("❌ Cancel All Open Orders", key="cancel_all"):
                for index, order in open_orders_df.iterrows():
                    trader.cancel_order(order['Order ID'], order['symbol'])
                st.success("All open orders have been cancelled.")
                st.rerun()
        else:
            st.info("No open orders.")

    with col2:
        st.subheader("⚡ Recent Trades")
        recent_trades_df = trader.get_recent_trades(limit=10)
        
        if not recent_trades_df.empty:
            st.dataframe(recent_trades_df, use_container_width=True)
        else:
            st.info("No recent trades found.")
