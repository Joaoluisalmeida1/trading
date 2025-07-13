# In page_modules/pnl_analysis.py

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

def calculate_pnl(trades_df):
    """
    Processes a raw trades DataFrame to calculate PNL on a position-by-position basis
    using a First-In, First-Out (FIFO) accounting method.
    """
    if trades_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    positions = {}
    closed_trades = []

    for index, trade in trades_df.iterrows():
        symbol = trade['symbol']
        side = trade['side']
        amount = trade['amount']
        price = trade['price']

        if symbol not in positions:
            positions[symbol] = {'buys': [], 'total_cost': 0, 'total_amount': 0}

        if side == 'buy':
            positions[symbol]['buys'].append({'amount': amount, 'price': price})
            positions[symbol]['total_cost'] += amount * price
            positions[symbol]['total_amount'] += amount
        
        elif side == 'sell':
            sell_amount = amount
            sell_price = price
            realized_pnl = 0
            
            # Match sells against the oldest buys (FIFO)
            while sell_amount > 0 and positions[symbol]['buys']:
                buy_tr = positions[symbol]['buys'][0]
                
                match_amount = min(sell_amount, buy_tr['amount'])
                cost_of_matched_buy = match_amount * buy_tr['price']
                proceeds_from_sell = match_amount * sell_price
                
                realized_pnl += (proceeds_from_sell - cost_of_matched_buy)
                
                sell_amount -= match_amount
                buy_tr['amount'] -= match_amount
                
                # If a buy is fully used, remove it
                if buy_tr['amount'] < 1e-9:
                    positions[symbol]['buys'].pop(0)

            closed_trades.append({
                'timestamp': trade['timestamp'],
                'symbol': symbol,
                'pnl': realized_pnl
            })

    if not closed_trades:
        return pd.DataFrame(), pd.DataFrame()

    pnl_df = pd.DataFrame(closed_trades)
    pnl_df['cumulative_pnl'] = pnl_df['pnl'].cumsum()
    
    return pnl_df, trades_df


def render_pnl_analysis(exchange):
    st.title("💰 PNL Analysis Center")

    if 'trader' not in st.session_state:
        st.warning("Trader not initialized. Please visit the Live Trading page first.")
        return

    trader = st.session_state.trader

    # --- Date Range Selection ---
    st.header("1. Select Analysis Period")
    today = datetime.now()
    col1, col2 = st.columns(2)
    start_date = col1.date_input("Start Date", today - timedelta(days=30))
    end_date = col2.date_input("End Date", today)

    if st.button("📈 Run PNL Analysis", use_container_width=True):
        with st.spinner("Fetching and analyzing all historical trades... This may take a few minutes."):
            # 1. Fetch all trades within the date range
            all_trades = trader.fetch_all_trades_since(start_date)
            
            # Filter trades to be within the end_date as well
            if not all_trades.empty:
                all_trades = all_trades[all_trades['timestamp'].dt.date <= end_date]

            # 2. Calculate PNL
            pnl_df, trades_df = calculate_pnl(all_trades)

            st.session_state.pnl_df = pnl_df
            st.session_state.trades_df = trades_df

    # --- Display Results ---
    if 'pnl_df' in st.session_state and not st.session_state.pnl_df.empty:
        pnl_df = st.session_state.pnl_df
        
        st.header("2. Overall Performance")
        total_pnl = pnl_df['pnl'].sum()
        st.metric("Total Realized P&L", f"${total_pnl:,.2f}")

        # --- Cumulative PNL Chart ---
        st.subheader("Cumulative P&L Over Time")
        fig = px.line(pnl_df, x='timestamp', y='cumulative_pnl', title="Portfolio Realized P&L Curve")
        fig.update_layout(xaxis_title="Date", yaxis_title="Cumulative P&L (USDC)")
        st.plotly_chart(fig, use_container_width=True)

        # --- PNL by Time Period ---
        st.subheader("P&L Breakdown by Period")
        pnl_by_day = pnl_df.set_index('timestamp').resample('D')['pnl'].sum()
        pnl_by_week = pnl_df.set_index('timestamp').resample('W-MON')['pnl'].sum()
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("Daily P&L")
            st.dataframe(pnl_by_day)
        with col2:
            st.write("Weekly P&L")
            st.dataframe(pnl_by_week)

        # --- Detailed Trade Log ---
        st.header("3. Detailed Trade Log")
        st.dataframe(st.session_state.trades_df)
    
    elif 'pnl_df' in st.session_state and st.session_state.pnl_df.empty:
        st.info("No closed trades found in the selected date range.")
