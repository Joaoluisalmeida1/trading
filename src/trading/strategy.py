import numpy as np
import pandas as pd

def ma_crossover(df: pd.DataFrame, short_window: int = 20, long_window: int = 50) -> pd.DataFrame:
    df = df.copy()
    df["ma_short"] = df["close"].rolling(short_window, min_periods=1).mean()
    df["ma_long"]  = df["close"].rolling(long_window,  min_periods=1).mean()
    raw = np.where(df["ma_short"] > df["ma_long"], 1, 0)
    df["signal"] = pd.Series(raw, index=df.index).diff().fillna(0).astype(int).clip(-1,1)
    return df

def rsi_strategy(df: pd.DataFrame, window: int = 14, overbought: int = 70, oversold: int = 30) -> pd.DataFrame:
    df = df.copy()
    delta = df["close"].diff()
    up, down = delta.clip(lower=0), -delta.clip(upper=0)
    ma_up   = up.rolling(window, min_periods=1).mean()
    ma_down = down.rolling(window, min_periods=1).mean()
    rsi = 100 - (100 / (1 + ma_up / ma_down))
    df["signal"] = 0
    df.loc[rsi >  overbought, "signal"] = -1
    df.loc[rsi <  oversold,   "signal"] =  1
    return df

def rsi_reverse_strategy(
    df: pd.DataFrame,
    window: int = 14,
    overbought: int = 70,
    oversold: int = 30
) -> pd.DataFrame:
    """
    Reverse-RSI:
      - BUY  when RSI > overbought
      - SELL when RSI < oversold
      - FLAT otherwise

    Returns the DataFrame with a new 'signal' column (-1, 0, +1).
    """
    df = df.copy()
    # calculate RSI
    delta = df["close"].diff()
    up   = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up   = up.rolling(window, min_periods=1).mean()
    ma_down = down.rolling(window, min_periods=1).mean()
    rsi = 100 - (100 / (1 + ma_up / ma_down))

    # default flat
    df["signal"] = 0

    # reverse logic
    df.loc[rsi > overbought, "signal"] = 1   # BUY when 'overbought'
    df.loc[rsi < oversold,   "signal"] = -1  # SELL when 'oversold'

    return df

def buy_and_hold_strategy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Buys at the first available bar and holds to the end.
    Signal = 1 on every row ensures one entry at start and no exits.
    """
    df = df.copy()
    df["signal"] = 1
    return df

def reverse_rsi_with_filters(
    df: pd.DataFrame,
    window: int = 14,
    overbought: int = 70,
    oversold: int = 30,
    volume_window: int = 20,
    volume_multiplier: float = 1.5,
    long_ma_window: int = 200,
    structure_window: int = 1
) -> pd.DataFrame:
    """
    Reverse-RSI strategy with additional conviction filters:
      • BUY when RSI > overbought AND
        – volume > volume_multiplier×MA(volume, volume_window)
        – price > SMA(close, long_ma_window)
        – market showing uptrend over last `structure_window` bars
      • SELL when RSI < oversold AND
        – volume > volume_multiplier×MA(volume, volume_window)
        – price < SMA(close, long_ma_window)
        – market showing downtrend over last `structure_window` bars
      • FLAT otherwise

    Returns the DataFrame with a new integer 'signal' column.
    """
    df = df.copy()

    # 1) Compute RSI
    delta = df["close"].diff()
    up   =  delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up   = up.rolling(window, min_periods=1).mean()
    ma_down = down.rolling(window, min_periods=1).mean()
    rsi = 100 - (100 / (1 + ma_up / ma_down))
    df["rsi"] = rsi

    # 2) Volume filter: rolling average & threshold
    df["vol_ma"] = df["volume"].rolling(volume_window, min_periods=1).mean()
    df["vol_ok"] = df["volume"] > (df["vol_ma"] * volume_multiplier)

    # 3) Long-term trend: SMA of close
    df["sma_long"] = df["close"].rolling(long_ma_window, min_periods=1).mean()

    # 4) Market-structure filter: higher-highs/higher-lows vs previous
    #    For bar i, compare with bar i-structure_window
    prev = df.shift(structure_window)
    df["uptrend"]   = (df["high"] > prev["high"]) & (df["low"] > prev["low"])
    df["downtrend"] = (df["high"] < prev["high"]) & (df["low"] < prev["low"])

    # 5) Build signals
    df["signal"] = 0

    # BUY condition
    buy_cond = (
        (rsi > overbought) &
        df["vol_ok"] &
        (df["close"] > df["sma_long"]) &
        df["uptrend"]
    )
    df.loc[buy_cond, "signal"] = 1

    # SELL condition
    sell_cond = (
        (rsi < oversold) &
        df["vol_ok"] &
        (df["close"] < df["sma_long"]) &
        df["downtrend"]
    )
    df.loc[sell_cond, "signal"] = -1

    # Clean up intermediate columns if you like; comment out to keep for debugging:
    # df.drop(columns=["rsi","vol_ma","vol_ok","sma_long","uptrend","downtrend"], inplace=True)

    return df