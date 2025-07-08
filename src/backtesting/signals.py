import pandas as pd
from trading.strategy import generate_signals

def get_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Wraps your `generate_signals` function. Expects a DataFrame with OHLCV and
    returns a DataFrame that has at least a 'signal' column with values -1, 0, or 1.
    """
    signals_df = generate_signals(df.copy())
    if "signal" not in signals_df.columns:
        raise ValueError("Your generate_signals() must return a 'signal' column.")
    return signals_df[["signal"]]
