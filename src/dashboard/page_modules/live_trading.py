import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from trading.trader import Trader
from api.api_client import BinanceClient
from streamlit_lightweight_charts import renderLightweightCharts
from streamlit_autorefresh import st_autorefresh

def render_live_trading(exchange):
    st.title("Live Trading Dashboard")
    # --- Auto-refresh the page every 30 seconds ---
    st_autorefresh(interval=30000, key="data_refresher")
    if exchange is None:
        st.warning("🔑 Exchange not initialized. Please check your setup.")
        return

    # --- Initialize clients and session state for confirmation ---
    if 'trader' not in st.session_state:
        try:
            client = BinanceClient(
                api_key=st.secrets["binance"]["api_key"],
                secret_key=st.secrets["binance"]["secret_key"]
            )
            st.session_state.trader = Trader(client)
        except Exception as e:
            st.error(f"Failed to initialize Binance Client: {e}")
            return

    if 'confirming_order' not in st.session_state:
        st.session_state.confirming_order = None

    trader = st.session_state.trader

    # --- Fetch all live data at once ---
    usdc_balance = trader.get_usdc_balance()
    total_equity = trader.get_total_equity()
    open_positions_df = trader.get_open_positions()
    open_orders_df = trader.get_open_orders() # Now fetches real data

    # -- PANEL 1: SITUATIONAL AWARENESS (Unchanged) --
    st.header("1. Situational Awareness")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="💰 Available Buying Power", value=f"${usdc_balance:,.2f}")
    with col2:
        st.metric(label="📈 Total Equity", value=f"${total_equity:,.2f}")
    st.divider()    # ... (code for this panel is the same)

    # --- PANEL 2: COMMAND CENTER ---
    st.header("2. Command Center")

    # --- User Inputs for the Order ---
    symbol = st.text_input("Symbol", value="BTC/USDC", key="lt_symbol")
    live_price = trader.get_live_price(symbol)
    st.info(f"Live Price for {symbol}: **${live_price:,.2f}**")

    order_type = st.selectbox("Order Type", ["Market", "Limit"])

    col1, col2, col3 = st.columns(3)
    with col1:
        usdc_amount = st.number_input("Amount (USDC)", min_value=10.0, value=50.0, step=10.0, help="Minimum order size is typically $10.")
    with col2:
        asset_amount = usdc_amount / live_price if live_price > 0 else 0
        st.metric(label=f"≈ Amount ({symbol.split('/')[0]})", value=f"{asset_amount:.6f}")
    with col3:
        limit_price = None
        if order_type == "Limit":
            limit_price = st.number_input("Limit Price", min_value=0.0, value=live_price, step=1.0)

    # --- Staging Buttons (Sets intent in session_state) ---
    buy_button, sell_button = st.columns(2)
    if buy_button.button("Place BUY Order", use_container_width=True):
        st.session_state.confirming_order = {
            "side": "buy", "symbol": symbol, "order_type": order_type,
            "asset_amount": asset_amount, "usdc_amount": usdc_amount, "limit_price": limit_price
        }
        st.rerun()

    if sell_button.button("Place SELL Order", use_container_width=True):
        st.session_state.confirming_order = {
            "side": "sell", "symbol": symbol, "order_type": order_type,
            "asset_amount": asset_amount, "usdc_amount": usdc_amount, "limit_price": limit_price
        }
        st.rerun()

    # --- Confirmation Dialog (Appears only when an order is staged) ---
    if st.session_state.confirming_order:
        details = st.session_state.confirming_order
        side = details['side'].upper()
        
        with st.expander(f"⚠️ Confirm Your {side} Order", expanded=True):
            st.write(f"**Symbol:** {details['symbol']}")
            st.write(f"**Type:** {details['order_type']}")
            st.write(f"**Amount:** ≈ {details['asset_amount']:.6f} {details['symbol'].split('/')[0]}")

            if side == "BUY":
                st.write(f"**Estimated Cost:** ≈ ${details['usdc_amount']:,.2f}")
            else:
                st.write(f"**Estimated Proceeds:** ≈ ${details['usdc_amount']:,.2f}")

            if details['order_type'] == "Limit":
                st.write(f"**Limit Price:** ${details['limit_price']:,.2f}")

            confirm_col, cancel_col = st.columns(2)
            
            # --- Final Execution Buttons ---
            if confirm_col.button(f"CONFIRM {side}", use_container_width=True):
                if side == "BUY":
                    order_result = trader.buy(symbol=details['symbol'], amount=details['asset_amount'], price=details['limit_price'], order_type=details['order_type'].lower())
                else:
                    order_result = trader.sell(symbol=details['symbol'], amount=details['asset_amount'], price=details['limit_price'], order_type=details['order_type'].lower())
                
                if 'error' in order_result:
                    st.error(f"Order failed: {order_result['error']}")
                else:
                    st.success(f"{side} order placed successfully!")
                    st.json(order_result)

                st.session_state.confirming_order = None
                st.rerun()

            if cancel_col.button("Cancel", use_container_width=True):
                st.session_state.confirming_order = None
                st.rerun()

    st.divider()


        # --- PANEL 3: THE LEDGER ---
    st.header("3. The Ledger")

    positions_col, orders_col = st.columns([3, 2])

    with positions_col:
        st.subheader("📊 Open Positions (Live P&L)")
        if not open_positions_df.empty:
            # Create the header for the interactive table
            h_cols = st.columns((2, 2, 2, 2, 1))
            h_cols[0].write("**Symbol**")
            h_cols[1].write("**Amount**")
            h_cols[2].write("**Entry Price**")
            h_cols[3].write("**P&L ($)**")
            h_cols[4].write("**Action**")
            st.markdown("---")

            # Create an interactive row for each open position
            for index, row in open_positions_df.iterrows():
                cols = st.columns((2, 2, 2, 2, 1))
                cols[0].write(row['Symbol'])
                cols[1].write(f"{row['Amount']:.6f}")
                cols[2].write(f"${row['Entry Price']:,.2f}")
                
                # Color P&L based on positive or negative value
                pnl_value = row['P&L ($)']
                pnl_color = "green" if pnl_value >= 0 else "red"
                cols[3].markdown(f"<p style='color:{pnl_color};'>${pnl_value:,.2f}</p>", unsafe_allow_html=True)
                
                # Interactive "Close" button for each position
                if cols[4].button("Close", key=f"close_{row['Symbol']}", use_container_width=True):
                    trader.close_position(row["Symbol"], row["Amount"])
                    st.success(f"Market SELL order placed to close {row['Symbol']} position.")
                    st.rerun()
        else:
            st.info("No open positions.")

    with orders_col:
        st.subheader("⏳ Open Orders")
        if not open_orders_df.empty:
            # Create the header for the open orders list
            h_cols = st.columns((2, 1, 1, 1))
            h_cols[0].write("**Symbol/Side**")
            h_cols[1].write("**Price**")
            h_cols[2].write("**Amount**")
            h_cols[3].write("**Action**")
            st.markdown("---")
            
            # Create an interactive row for each open order
            for index, row in open_orders_df.iterrows():
                cols = st.columns((2, 1, 1, 1))
                cols[0].write(f"{row['symbol']} {row['side']}")
                cols[1].write(f"@{row['price']:,.2f}")
                cols[2].write(f"{row['amount']:.4f}")
                
                # Interactive "Cancel" button for each order
                if cols[3].button("Cancel", key=f"cancel_{row['Order ID']}", use_container_width=True):
                    trader.cancel_order(row['Order ID'], row['symbol'])
                    st.success(f"Cancel request sent for order {row['Order ID']}.")
                    st.rerun()
        else:
            st.info("No open orders.")

        # --- PANEL 4: MARKET DEPTH ---
        st.header("4. Market Depth")
        all_symbols = [symbol] + open_positions_df['Symbol'].tolist() if not open_positions_df.empty else [symbol]
        depth_symbol = st.selectbox("Select Symbol for Depth Chart", list(set(all_symbols)))
        bids, asks = trader.get_order_book(depth_symbol)

        if not bids.empty and not asks.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=bids['Amount'], y=bids['Price'], orientation='h', name='Bids', marker_color='green'))
            fig.add_trace(go.Bar(x=asks['Amount'], y=asks['Price'], orientation='h', name='Asks', marker_color='red'))
            fig.update_layout(title_text=f'Order Book Depth for {depth_symbol}', yaxis_autorange='reversed')
            st.plotly_chart(fig, use_container_width=True)