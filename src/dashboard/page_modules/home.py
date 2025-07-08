import streamlit as st
import pandas as pd
import plotly.express as px


def render_home(exchange):
    """Home page: connect to Binance and show key metrics"""
    st.title("🤖 Dashboard Home")
    st.markdown("### Overview: Connection & Key Metrics")

    if exchange is None:
        st.warning("🔑 Binance not initialized. Check API keys in `.env`.")
        return

    try:
        st.success("✅ Connected to Binance")

        # Fetch balances and filter non-zero
        balances = exchange.fetch_balance()["total"]
        non_zero = {asset: amt for asset, amt in balances.items() if amt and amt > 0}

        # Compute values in USDC
        total_usdc = balances.get("USDC", 0.0)
        asset_values = {}
        for asset, amt in non_zero.items():
            if asset == "USDC":
                asset_values[asset] = amt
            else:
                try:
                    ticker = exchange.fetch_ticker(f"{asset}/USDC")
                    value = amt * ticker["last"]
                    asset_values[asset] = value
                    total_usdc += value
                except Exception:
                    asset_values[asset] = 0.0

        # Display individual metrics and total
        cols = st.columns(len(asset_values) + 1)
        for idx, (asset, value) in enumerate(asset_values.items()):
            display_amount = balances.get(asset, 0.0)
            cols[idx].metric(f"{asset} Balance", f"{display_amount:.4f}")
        cols[-1].metric("Total Value (USDC)", f"{total_usdc:.2f}")

        # Portfolio Allocation Donut Chart
        st.subheader("📊 Portfolio Allocation")
        df_alloc = pd.DataFrame.from_dict(asset_values, orient='index', columns=['value'])
        df_alloc = df_alloc.reset_index().rename(columns={'index':'asset'})
        fig = px.pie(
            df_alloc,
            names='asset',
            values='value',
            hole=0.4,
            title='Portfolio Allocation',
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

        # 24h P&L and Performance
        st.subheader("⏱️ 24h Performance Metrics")
        pnl_usd = 0.0
        prev_total = 0.0
        for asset, amt in non_zero.items():
            if asset == "USDC":
                prev_total += amt
                continue
            try:
                ticker = exchange.fetch_ticker(f"{asset}/USDC")
                prev_price = ticker.get('info', {}).get('open', ticker['last'])
                prev_value = amt * prev_price
                current_value = amt * ticker['last']
                pnl_usd += (current_value - prev_value)
                prev_total += prev_value
            except Exception:
                prev_total += amt * ticker.get('last', 0.0)
        change_abs = pnl_usd
        change_pct = (pnl_usd / prev_total * 100) if prev_total else 0.0
        st.metric("24h P&L (USDC)", f"{change_abs:.2f}", delta=f"{change_pct:.2f}%")

        # Open Orders & Quick Actions
        st.subheader("📝 Open Orders")
        exchange.options["warnOnFetchOpenOrdersWithoutSymbol"] = False
        orders = exchange.fetch_open_orders()
        if orders:
            df_orders = pd.DataFrame(orders)[['symbol','side','amount','price','timestamp']]
            df_orders['timestamp'] = pd.to_datetime(df_orders['timestamp'], unit='ms')
            st.dataframe(df_orders, use_container_width=True)
            if st.button("❌ Cancel All Orders", key="cancel_open_orders"):
                for o in orders:
                    exchange.cancel_order(o['id'], o['symbol'])
                st.success("All open orders canceled")
        else:
            st.info("No open orders")

        # Recent Trades Feed
        st.subheader("⚡ Recent Trades")
        try:
            trades = exchange.fetch_my_trades(limit=5)
            if trades:
                df_trades = pd.DataFrame(trades)[['timestamp','symbol','side','amount','price']]
                df_trades['timestamp'] = pd.to_datetime(df_trades['timestamp'], unit='ms')
                st.table(df_trades)
            else:
                st.info("No recent trades")
        except Exception:
            st.error("Failed to fetch recent trades")

    except Exception as e:
        st.error(f"❌ Failed to load Home page data: {e}")