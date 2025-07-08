import os
from datetime import datetime

import streamlit as st
import pandas as pd
import ccxt
from dotenv import load_dotenv

load_dotenv()


def get_exchange(name: str = "binance"):
    """Instantiate an exchange from ccxt using optional API keys."""
    exchange_class = getattr(ccxt, name)
    params = {}
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    if api_key and api_secret:
        params.update({"apiKey": api_key, "secret": api_secret})
    return exchange_class(params)


@st.cache_data(show_spinner=False)
def load_ohlcv(exchange_name: str, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
    """Fetch OHLCV data and return as DataFrame."""
    exchange = get_exchange(exchange_name)
    data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def main() -> None:
    st.title("Trading Dashboard")

    with st.sidebar:
        st.header("Configura\u00e7\u00f5es")
        exchange_name = st.selectbox("Exchange", ["binance"], index=0)
        symbol = st.text_input("Par (ex: BTC/USDT)", "BTC/USDT")
        timeframe = st.selectbox(
            "Timeframe",
            ["1m", "5m", "15m", "1h", "4h", "1d"],
            index=5,
        )
        limit = st.slider("N\u00famero de candles", 10, 500, 100)
        load_button = st.button("Carregar dados")

    if load_button:
        try:
            df = load_ohlcv(exchange_name, symbol, timeframe, limit)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Erro ao obter dados: {exc}")
            return

        st.subheader(f"{symbol} - {timeframe}")
        st.line_chart(data=df, x="timestamp", y="close")
        st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()
