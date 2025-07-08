import streamlit as st
from trading.trader import Trader
from api.api_client import BinanceClient


def render_live_trading(exchange):
    st.title("🚀 Live Trading Module")

    if exchange is None:
        st.warning("🔑 Binance not initialized. Check API keys.")
        return

    client = BinanceClient()
    trader = Trader(client)

    symbol = st.text_input("Symbol", value="BTC/USDC", key="lt-symbol")
    amount = st.number_input("Amount", value=0.0, key="lt-amount")

    col1, col2 = st.columns(2)
    if col1.button("BUY Market", key="lt-buy"):
        order = trader.buy(symbol, amount, order_type="market")
        st.json(order)
    if col2.button("SELL Market", key="lt-sell"):
        order = trader.sell(symbol, amount, order_type="market")
        st.json(order)