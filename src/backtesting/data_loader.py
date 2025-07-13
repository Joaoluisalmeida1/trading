import os
import pandas as pd
import ccxt
import time
from datetime import datetime

def fetch_ohlcv(exchange, symbol: str, timeframe: str = "1h", since: int = None, limit: int = 1000) -> pd.DataFrame:
    """
    Fetches the latest OHLCV data directly from the exchange. This version is
    optimized for a live bot and always fetches fresh data, bypassing any file cache.
    """
    print(f"Fetching fresh {timeframe} data for {symbol} from exchange...")
    
    all_candles = []
    try:
        # A single, direct fetch from the exchange is sufficient for a live bot's needs.
        candles = exchange.fetch_ohlcv(symbol, timeframe, since, limit)
        if candles:
            all_candles.extend(candles)

    except Exception as e:
        print(f"An error occurred while fetching data for {symbol}: {e}")
        return pd.DataFrame() # Return an empty DataFrame on error
            
    if not all_candles:
        return pd.DataFrame()

    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    # This is a critical data cleaning step that remains.
    # It prevents errors from any incomplete candles the exchange might return.
    df.dropna(inplace=True)

    print(f"👍 Successfully fetched and cleaned {len(df)} fresh candles for {symbol}.")

    return df
