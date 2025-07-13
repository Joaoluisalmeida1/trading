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

    This version now correctly includes the 'rsi' column in the returned DataFrame.
    """
    df = df.copy()
    
    # Calculate RSI
    delta = df["close"].diff()
    up   = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up   = up.rolling(window, min_periods=1).mean()
    ma_down = down.rolling(window, min_periods=1).mean()
    rsi = 100 - (100 / (1 + ma_up / ma_down))

    # --- THE FIX IS HERE ---
    # Add the calculated RSI series as a new column to the DataFrame.
    df["rsi"] = rsi

    # Default flat signal
    df["signal"] = 0

    # Reverse logic for signals
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

def volatility_breakout_strategy(
    df: pd.DataFrame,
    bb_window: int = 20,
    bb_dev: float = 2.0,
    squeeze_window: int = 100,
    volume_window: int = 20,
    volume_multiplier: float = 1.5,
    atr_window: int = 14,
) -> pd.DataFrame:
    """
    Volatility Breakout (Bollinger Squeeze & Break):
      • Detects BB squeeze: band width lowest over last `squeeze_window` bars
      • Enters LONG when candle closes above upper BB AND volume > multiplier×avg(volume)
      • Exits when price closes back inside the upper BB
      • (ATR is calculated here for optional stop‐loss use downstream)
    """
    df = df.copy()

    # 1) Bollinger Bands
    df["sma_bb"] = df["close"].rolling(bb_window, min_periods=1).mean()
    df["std_bb"] = df["close"].rolling(bb_window, min_periods=1).std()
    df["upper_bb"] = df["sma_bb"] + bb_dev * df["std_bb"]
    df["lower_bb"] = df["sma_bb"] - bb_dev * df["std_bb"]
    df["bb_width"] = df["upper_bb"] - df["lower_bb"]

    # 2) Squeeze detection: width is the lowest in the last `squeeze_window` bars
    df["squeeze"] = df["bb_width"] == df["bb_width"].rolling(squeeze_window, min_periods=1).min()

    # 3) Volume filter
    df["vol_ma"] = df["volume"].rolling(volume_window, min_periods=1).mean()
    df["vol_ok"] = df["volume"] > (df["vol_ma"] * volume_multiplier)

    # 4) ATR for downstream stops (optional)
    high_low    = df["high"] - df["low"]
    high_close  = (df["high"] - df["close"].shift(1)).abs()
    low_close   = (df["low"]  - df["close"].shift(1)).abs()
    df["tr"]    = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"]   = df["tr"].rolling(atr_window, min_periods=1).mean()

    # 5) Generate signals
    df["signal"] = 0

    # BUY when there's a squeeze, breakout above upper BB, and volume confirmation
    buy_cond = (
        df["squeeze"] &
        (df["close"] > df["upper_bb"]) &
        df["vol_ok"]
    )
    df.loc[buy_cond, "signal"] = 1

    # SELL when price closes back inside the upper BB
    sell_cond = df["close"] < df["upper_bb"]
    df.loc[sell_cond, "signal"] = -1

    return df

def pullback_trend_strategy(
    df: pd.DataFrame,
    fast_ema: int = 20,
    slow_ema: int = 50,
    rsi_window: int = 14,
    rsi_lower: int = 40,
    rsi_upper: int = 50,
) -> pd.DataFrame:
    """
    Trend-Following with Pullback (EMA + RSI):
    
    Long entry when ALL of:
      1. Uptrend: fast EMA > slow EMA, and both rising
      2. Pullback: price touches or drops below fast EMA
      3. RSI reset: RSI in [rsi_lower, rsi_upper] and turning up
      4. Bullish candle: close > open (simple confirmation)
    
    Exit when:
      - Price closes below fast EMA, OR
      - Fast EMA crosses below slow EMA (trend break)
    
    Returns df with a new integer 'signal' column: +1 buy, -1 sell, 0 flat.
    """
    df = df.copy()

    # 1) EMAs & slopes
    df["ema_fast"] = df["close"].ewm(span=fast_ema, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=slow_ema, adjust=False).mean()
    df["ema_fast_slope"] = df["ema_fast"] > df["ema_fast"].shift(1)
    df["ema_slow_slope"] = df["ema_slow"] > df["ema_slow"].shift(1)

    # 2) RSI
    delta = df["close"].diff()
    up   = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up   = up.rolling(rsi_window, min_periods=1).mean()
    ma_down = down.rolling(rsi_window, min_periods=1).mean()
    df["rsi"] = 100 - (100 / (1 + ma_up / ma_down))

    # 3) Conditions
    # a) Trend up
    trend_up = (
        (df["ema_fast"] > df["ema_slow"]) &
        df["ema_fast_slope"] &
        df["ema_slow_slope"]
    )

    # b) Pullback to fast EMA
    pullback = df["low"] <= df["ema_fast"]

    # c) RSI reset & turning up
    rsi_ok      = df["rsi"].between(rsi_lower, rsi_upper)
    rsi_turn_up = df["rsi"] > df["rsi"].shift(1)

    # d) Simple bullish candle
    bullish_candle = df["close"] > df["open"]

    buy_cond = trend_up & pullback & rsi_ok & rsi_turn_up & bullish_candle

    # Exit: break of fast EMA or trend reversal
    exit_cond = (
        (df["close"] < df["ema_fast"]) |
        (df["ema_fast"] < df["ema_slow"])
    )

    # 4) Build signals
    df["signal"] = 0
    df.loc[buy_cond,  "signal"] = 1
    df.loc[exit_cond, "signal"] = -1

    # (optional) drop intermediate cols if desired
    # df.drop(columns=["ema_fast_slope","ema_slow_slope","rsi"], inplace=True)

    return df


ALL_STRATEGIES = {
    "Reverse RSI": rsi_reverse_strategy,
    "Refined Reverse RSI": reverse_rsi_with_filters,
    # ... add any other strategies
}

def get_strategy_function(name: str):
    return ALL_STRATEGIES.get(name)