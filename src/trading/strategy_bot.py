import pandas as pd
from trading.trader import Trader
from backtesting.data_loader import fetch_ohlcv
from trading.strategy import get_strategy_function
import time

class StrategyBot:
    def __init__(self, config: dict, trader: Trader):
        self.config = config
        self.trader = trader
        self.strategy_fn = get_strategy_function(config['strategy_name'])
        self.last_processed_candle = {}
        self.last_fetched_df = None

    def run_check(self):
        """
        The main bot loop, now with symbol translation logic. It analyzes a
        configured symbol but executes trades on a compliant execution pair.
        """
        logs = [f"[{time.ctime()}] Running strategy check..."]
        
        open_positions = {
            pos['Symbol']: pos for pos in self.trader.get_open_positions().to_dict('records')
        }

        # --- Priority 1: Stop-Loss Monitoring (Unchanged but still critical) ---
        for symbol in list(open_positions.keys()):
            position = open_positions[symbol]
            current_price = self.trader.get_live_price(symbol)
            entry_price = position.get('Entry Price', 0)
            
            if entry_price > 0:
                stop_loss_price = entry_price * (1 - self.config['stop_loss_pct'] / 100)
                if current_price <= stop_loss_price:
                    logs.append(f"🚨 STOP-LOSS TRIGGERED for {symbol} at ${current_price:,.2f}. Closing position.")
                    self.trader.close_position(symbol, position['Amount'])
                    del open_positions[symbol]
                    continue

        # --- Priority 2: RSI Signal Analysis with Symbol Translation ---
        for analysis_symbol in self.config['symbols']:
            try:
                # --- NEW: Get the execution symbol from the trader ---
                execution_symbol = self.trader.get_execution_symbol(analysis_symbol)

                # Fetch data using the specified analysis_symbol (e.g., MATIC/USDT)
                df = fetch_ohlcv(self.trader.client.exchange, analysis_symbol, self.config['timeframe'], limit=self.config['rsi_window'] + 201)
                self.last_fetched_df = df

                if df.empty or len(df) < 2:
                    logs.append(f"Warning: Not enough data for {analysis_symbol}. Skipping.")
                    continue

                sig_df = self.strategy_fn(df, **self.config['strategy_params'])
                current_rsi = sig_df['rsi'].iloc[-1] 

                last_candle = df.iloc[-2]
                last_candle_ts = last_candle.name

                if self.last_processed_candle.get(analysis_symbol) == last_candle_ts:
                    logs.append(f"Pulse: On candle {last_candle_ts} for {analysis_symbol} (Current RSI: {current_rsi:.2f}). No action.")
                    continue

                logs.append(f"✅ New {self.config['timeframe']} candle for {analysis_symbol} at {last_candle_ts} detected. Analyzing...")

                latest_signal = sig_df['signal'].iloc[-2]
                rsi_on_signal = sig_df['rsi'].iloc[-2]
                close_price = last_candle.get('close')

                if pd.isna(close_price) or close_price <= 0:
                    logs.append(f"🚨 ERROR: Invalid close price ({close_price}) for {analysis_symbol}. Skipping.")
                    continue

                # --- State-Aware Trading Logic with Translated Symbols ---
                # BUY Condition: Signal is BUY and we do NOT have a position in the EXECUTION symbol.
                if latest_signal == 1 and (not execution_symbol or execution_symbol not in open_positions):
                    if execution_symbol:
                        logs.append(f"BUY signal on {analysis_symbol} (RSI: {rsi_on_signal:.2f}). Executing on compliant pair: {execution_symbol}.")
                        amount_to_buy = self.config['allocation_usd'] / close_price
                        self.trader.buy(execution_symbol, amount_to_buy, order_type='market')
                    else:
                        logs.append(f"BUY signal on {analysis_symbol}, but no compliant USDC pair exists. Skipping trade.")
                
                # SELL Condition: Signal is SELL and we DO have a position in the EXECUTION symbol.
                elif latest_signal == -1 and execution_symbol and execution_symbol in open_positions:
                    logs.append(f"SELL signal on {analysis_symbol} (RSI: {rsi_on_signal:.2f}). Closing position for {execution_symbol}.")
                    position_amount = open_positions[execution_symbol]['Amount']
                    self.trader.close_position(execution_symbol, position_amount)

                self.last_processed_candle[analysis_symbol] = last_candle_ts

            except Exception as e:
                logs.append(f"🚨 FATAL ERROR processing {analysis_symbol}: {e}. Bot will continue.")
                continue
        
        return logs
