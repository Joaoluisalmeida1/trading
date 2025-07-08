import os
import pandas as pd
import ccxt
from dotenv import load_dotenv, find_dotenv

# Load API keys
load_dotenv(find_dotenv())
API_KEY    = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# Ensure data cache folder exists
CACHE_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "data")
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_ohlcv(symbol: str, timeframe: str = "1h", since: int = None, limit: int = 500) -> pd.DataFrame:
    """
    Fetches OHLCV data for `symbol` from Binance (via CCXT), caches it to CSV,
    and returns a pandas.DataFrame indexed by timestamp.
    """
    filename = f"{symbol.replace('/', '_')}_{timeframe}_{limit}.csv"
    path = os.path.join(CACHE_DIR, filename)

    # Always fetch fresh data (but still cache for inspection)
    exchange = ccxt.binance({
        "apiKey": API_KEY,
        "secret": API_SECRET,
        "enableRateLimit": True,
    })
    data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)

    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df.to_csv(path)

    return df
