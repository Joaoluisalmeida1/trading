import pandas as pd

def run_backtest(
    price_df: pd.DataFrame,
    signals: pd.Series,
    initial_cash: float = 1000.0,
    commission_rate: float = 0.001,   # default 10 bps
    stop_loss: float = 0.0            # e.g. 0.02 for 2%
) -> (pd.DataFrame, pd.DataFrame):
    """
    Simulates a long-only strategy with commission and optional stop-loss.
    - stop_loss: fraction below entry price to trigger an exit (e.g. 0.02 = 2%).
    """
    # Clean & clamp signals
    s = signals.copy().fillna(0).apply(lambda x: int(x) if x in (-1,0,1) else 0)

    cash = initial_cash
    position = 0.0
    entry_price = None
    last_signal = 0

    equity_list = []
    trades = []

    for idx, row in price_df.iterrows():
        price_open  = float(row.get("open", 0.0)  or 0.0)
        price_low   = float(row.get("low", 0.0)   or 0.0)
        price_close = float(row.get("close", 0.0) or 0.0)
        signal      = s.loc[idx]

        # — Stop-loss check —
        if position > 0 and stop_loss > 0 and entry_price is not None:
            stop_price = entry_price * (1 - stop_loss)
            # if the low of this bar breaches the stop, exit here
            if price_low <= stop_price:
                gross = position * stop_price
                commission_amt = gross * commission_rate
                cash = gross * (1 - commission_rate)
                trades.append({
                    "timestamp":  idx,
                    "side":       "SELL (SL)",
                    "price":      stop_price,
                    "amount":     position,
                    "commission": commission_amt
                })
                position = 0.0
                last_signal = 0
                # record equity at close after forced exit
                equity_list.append(cash)
                continue  # skip the rest of this bar

        # — Entry (signal-based) —
        if last_signal <= 0 and signal == 1 and price_open > 0:
            entry_price = price_open
            position = cash * (1 - commission_rate) / price_open
            commission_amt = cash * commission_rate
            trades.append({
                "timestamp":  idx,
                "side":       "BUY",
                "price":      price_open,
                "amount":     position,
                "commission": commission_amt
            })
            cash = 0.0

        # — Exit (signal-based) —
        elif last_signal == 1 and signal <= 0 and position > 0 and price_open > 0:
            gross = position * price_open
            commission_amt = gross * commission_rate
            cash = gross * (1 - commission_rate)
            trades.append({
                "timestamp":  idx,
                "side":       "SELL",
                "price":      price_open,
                "amount":     position,
                "commission": commission_amt
            })
            position = 0.0

        last_signal = signal
        equity = cash + position * price_close
        equity_list.append(equity)

    # Build output DataFrames
    equity_df = pd.DataFrame({"equity": equity_list}, index=price_df.index)
    equity_df["returns"]  = equity_df["equity"].pct_change().fillna(0.0)
    equity_df["peak"]     = equity_df["equity"].cummax()
    equity_df["drawdown"] = equity_df["equity"] / equity_df["peak"] - 1.0
    trades_df = pd.DataFrame(trades)

    return equity_df, trades_df
