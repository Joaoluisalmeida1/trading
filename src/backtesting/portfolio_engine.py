import pandas as pd

def run_portfolio_backtest(
    price_data: dict,
    signal_data: dict,
    initial_cash: float,
    allocation: float,
    commission_rate: float,
    stop_loss: float
):
    """
    Simulates a strategy across multiple assets with shared capital and position sizing.
    """
    # --- Data Preparation ---
    # Combine all price data into a single dataframe, sorted by time
    combined_df = pd.concat(price_data.values(), keys=price_data.keys(), names=['symbol', 'timestamp']).reset_index()
    combined_df = combined_df.pivot_table(
        index='timestamp', columns='symbol',
        values=['open', 'high', 'low', 'close']
    )
    combined_df.columns = [f"{price}_{symbol}" for price, symbol in combined_df.columns]
    combined_df.sort_index(inplace=True)

    # --- State Initialization ---
    cash = initial_cash
    total_equity = initial_cash
    positions = {}  # To store holdings: {'BTC/USDC': {'amount': X, 'entry_price': Y}}
    equity_list = []
    trades = []

    # --- Event Loop ---
    for idx, row in combined_df.iterrows():
        # 1. Update total equity based on current close prices
        current_portfolio_value = 0
        for symbol, pos in positions.items():
            close_price = row.get(f"close_{symbol}")
            if pd.notna(close_price):
                current_portfolio_value += pos['amount'] * close_price
        total_equity = cash + current_portfolio_value

        # 2. Check for stop-loss triggers
        symbols_to_exit = []
        for symbol, pos in positions.items():
            low_price = row.get(f"low_{symbol}")
            stop_price = pos['entry_price'] * (1 - stop_loss)
            if pd.notna(low_price) and low_price <= stop_price:
                # Execute stop-loss sell
                gross = pos['amount'] * stop_price
                commission_amt = gross * commission_rate
                cash += gross - commission_amt
                trades.append({
                    "timestamp": idx, "symbol": symbol, "side": "SELL (SL)",
                    "price": stop_price, "amount": pos['amount'], "commission": commission_amt
                })
                symbols_to_exit.append(symbol)

        for symbol in symbols_to_exit:
            del positions[symbol]

        # 3. Check for new signals
        for symbol in price_data.keys():
            if symbol in positions:  # Check for exit signal
                signal = signal_data[symbol].get(idx, 0)
                if signal <= 0: # Exit signal
                    price_open = row.get(f"open_{symbol}")
                    if pd.notna(price_open):
                        pos = positions[symbol]
                        gross = pos['amount'] * price_open
                        commission_amt = gross * commission_rate
                        cash += gross - commission_amt
                        trades.append({
                            "timestamp": idx, "symbol": symbol, "side": "SELL",
                            "price": price_open, "amount": pos['amount'], "commission": commission_amt
                        })
                        del positions[symbol]
            else:  # Check for entry signal
                signal = signal_data[symbol].get(idx, 0)
                if signal == 1: # Entry signal
                    capital_to_allocate = total_equity * allocation
                    if cash >= capital_to_allocate:
                        price_open = row.get(f"open_{symbol}")
                        if pd.notna(price_open):
                            cash_for_trade = capital_to_allocate
                            commission_amt = cash_for_trade * commission_rate
                            amount_to_buy = (cash_for_trade - commission_amt) / price_open
                            positions[symbol] = {'amount': amount_to_buy, 'entry_price': price_open}
                            cash -= cash_for_trade
                            trades.append({
                                "timestamp": idx, "symbol": symbol, "side": "BUY",
                                "price": price_open, "amount": amount_to_buy, "commission": commission_amt
                            })
        
        # Record final equity for the day
        final_portfolio_value = sum(pos['amount'] * row.get(f"close_{symbol}", 0) for symbol, pos in positions.items())
        equity_list.append(cash + final_portfolio_value)

    # --- Build Output DataFrames ---
    equity_df = pd.DataFrame({"equity": equity_list}, index=combined_df.index)
    equity_df["returns"] = equity_df["equity"].pct_change().fillna(0.0)
    equity_df["peak"] = equity_df["equity"].cummax()
    equity_df["drawdown"] = (equity_df["equity"] / equity_df["peak"]) - 1.0
    trades_df = pd.DataFrame(trades)

    return equity_df, trades_df