import pandas as pd
from api.api_client import BinanceClient
from utils.logger import get_logger
import datetime 
import streamlit as st

class Trader:
    """
    The Trader class acts as an intermediary between the low-level API client
    and the high-level user interface. It translates raw API responses into
    clean, actionable data and business logic for trading.
    """
    def __init__(self, client: BinanceClient):
        """
        Initializes the Trader with an instance of the BinanceClient.

        Args:
            client (BinanceClient): An initialized API client.
        """
        self.client = client
        self.logger = get_logger(self.__class__.__name__)

    # --- Core Order Execution Methods ---

    def buy(self, symbol: str, amount: float, price: float = None, order_type: str = 'market'):
        """
        Places a BUY order on the exchange.

        Args:
            symbol (str): The trading symbol (e.g., 'BTC/USDC').
            amount (float): The amount of the base currency to buy.
            price (float, optional): The price for a limit order. Defaults to None.
            order_type (str, optional): 'market' or 'limit'. Defaults to 'market'.

        Returns:
            dict: The result of the order execution from the exchange.
        """
        self.logger.info(f"Placing BUY order: {amount} of {symbol} at {order_type} price.")
        order = self.client.create_order(symbol, 'buy', order_type, amount, price)
        self.logger.info(f"Order result: {order}")
        return order

    def sell(self, symbol: str, amount: float, price: float = None, order_type: str = 'market'):
        """
        Places a SELL order on the exchange.

        Args:
            symbol (str): The trading symbol (e.g., 'BTC/USDC').
            amount (float): The amount of the base currency to sell.
            price (float, optional): The price for a limit order. Defaults to None.
            order_type (str, optional): 'market' or 'limit'. Defaults to 'market'.

        Returns:
            dict: The result of the order execution from the exchange.
        """
        self.logger.info(f"Placing SELL order: {amount} of {symbol} at {order_type} price.")
        order = self.client.create_order(symbol, 'sell', order_type, amount, price)
        self.logger.info(f"Order result: {order}")
        return order

    # --- Dashboard Data Provider Methods ---

    def get_usdc_balance(self) -> float:
        """
        Fetches the account balance and returns the available (free) USDC amount.

        Returns:
            float: The amount of free USDC available.
        """
        balance = self.client.fetch_balance()
        if balance and 'USDC' in balance:
            return balance['USDC']['free']
        return 0.0

    def get_open_positions(self) -> pd.DataFrame:
        balance = self.client.fetch_balance()
        positions = []
        if balance and 'total' in balance:
            for asset, total_amount in balance['total'].items():
                if total_amount > 0.00001 and asset not in ['USDC', 'USDT']:
                    symbol = f"{asset}/USDC"
                    live_price = self.get_live_price(symbol)
                    avg_entry_price = self._get_avg_entry_price(symbol, total_amount)
                    
                    pnl_usd = (live_price - avg_entry_price) * total_amount
                    pnl_pct = (pnl_usd / (avg_entry_price * total_amount)) * 100 if avg_entry_price > 0 else 0

                    positions.append({
                        'Symbol': symbol,
                        'Amount': total_amount,
                        'Entry Price': avg_entry_price,
                        'Current Price': live_price,
                        'P&L ($)': pnl_usd,
                        'P&L (%)': pnl_pct,
                    })
        return pd.DataFrame(positions)

    # --- NEW: Order Book Method ---
    def get_order_book(self, symbol: str, limit: int = 10):
        order_book = self.client.fetch_order_book(symbol, limit)
        if not order_book:
            return pd.DataFrame(), pd.DataFrame()

        bids = pd.DataFrame(order_book['bids'], columns=['Price', 'Amount']).sort_values('Price', ascending=False)
        asks = pd.DataFrame(order_book['asks'], columns=['Price', 'Amount'])
        return bids, asks

    def get_open_orders(self, symbol: str = None) -> pd.DataFrame:
        """
        Fetches open orders from the exchange and formats them into a clean DataFrame.

        Args:
            symbol (str, optional): Filter orders by a specific symbol. Defaults to None.

        Returns:
            pd.DataFrame: A DataFrame of open orders.
        """
        open_orders = self.client.fetch_open_orders(symbol)
        if not open_orders:
            return pd.DataFrame() # Return empty DataFrame if no open orders

        # Format the raw data from the exchange into a more readable DataFrame
        df = pd.DataFrame(open_orders)
        df_formatted = df[['datetime', 'symbol', 'side', 'type', 'amount', 'price', 'id']]
        return df_formatted.rename(columns={'datetime': 'Timestamp', 'id': 'Order ID'})

    def get_live_price(self, symbol: str) -> float:
        """
        Gets the last traded price for a given symbol.

        Args:
            symbol (str): The trading symbol.

        Returns:
            float: The last traded price, or 0.0 if not available.
        """
        ticker = self.client.fetch_ticker(symbol)
        if ticker and 'last' in ticker:
            return ticker['last']
        return 0.0

    # --- Position and Order Management Methods ---

    def close_position(self, symbol: str, amount: float):
        """
        Closes an entire position by placing a market sell order.

        Args:
            symbol (str): The symbol of the position to close.
            amount (float): The amount to sell.

        Returns:
            dict: The result of the market sell order.
        """
        self.logger.info(f"Closing position for {symbol} by selling {amount} at market price.")
        return self.sell(symbol=symbol, amount=amount, order_type='market')

    def cancel_order(self, order_id: str, symbol: str):
        """
        Cancels an existing open order.

        Args:
            order_id (str): The ID of the order to cancel.
            symbol (str): The symbol of the order.

        Returns:
            dict: The result of the cancellation from the exchange.
        """
        self.logger.info(f"Attempting to cancel order {order_id} for {symbol}.")
        result = self.client.cancel_order(order_id, symbol)
        self.logger.info(f"Cancellation result: {result}")
        return result

    def get_total_equity(self) -> float:
        """
        Calculates the total account equity by summing the cash balance and the
        current market value of all open positions.
        """
        balance = self.client.fetch_balance()
        if not balance:
            return 0.0

        total_equity = 0.0
        
        # Start with free cash balances (USDC, USDT, etc.)
        for currency in ['USDC', 'USDT']:
            if currency in balance:
                total_equity += balance[currency]['free']

        # Add the value of all non-stablecoin positions
        if 'total' in balance:
            for asset, amount in balance['total'].items():
                if amount > 0 and asset not in ['USDC', 'USDT']:
                    live_price = self.get_live_price(f"{asset}/USDC")
                    total_equity += amount * live_price
                    
        return total_equity

    def _get_avg_entry_price(self, symbol: str, position_amount: float) -> float:
        """
        Calculates the average entry price for a position by fetching recent trades.
        NOTE: This is a simplified logic. A production system would use a more robust
        method, like a dedicated trade database.
        """
        trades = self.client.fetch_my_trades(symbol, limit=200)
        if not trades:
            return 0.0

        df = pd.DataFrame(trades)
        buys = df[df['side'] == 'buy'].tail(100) # Look at recent buys

        # Find the trades that constitute the current position
        cumulative_amount = 0
        total_cost = 0
        for index, trade in buys.iloc[::-1].iterrows():
            if cumulative_amount < position_amount:
                cost = trade['price'] * trade['amount']
                total_cost += cost
                cumulative_amount += trade['amount']
            else:
                break
        
        return total_cost / cumulative_amount if cumulative_amount > 0 else 0.0

    def get_24h_performance(self):
        """
        Calculates the portfolio's 24-hour P&L by comparing the current value
        of assets against their value 24 hours ago (using the 'open' price from the ticker).

        Returns:
            tuple: A tuple containing (pnl_usd, pnl_pct).
        """
        balance = self.client.fetch_balance()
        if not balance or 'total' not in balance:
            return 0.0, 0.0

        pnl_usd = 0.0
        previous_total_value = 0.0

        # Calculate the starting value of the portfolio 24h ago
        # and the P&L contribution from each asset.
        for asset, amount in balance['total'].items():
            if amount <= 0:
                continue
            
            symbol = f"{asset}/USDC"
            
            if asset == 'USDC':
                # USDC itself doesn't change in value, but it's part of the base capital
                previous_total_value += amount
                continue

            try:
                ticker = self.client.fetch_ticker(symbol)
                if not ticker: continue
                
                # Use the standardized 'open' and 'last' fields for reliability
                open_price_24h = ticker.get('open', ticker['last'])
                current_price = ticker['last']
                
                previous_asset_value = amount * open_price_24h
                current_asset_value = amount * current_price
                
                pnl_usd += (current_asset_value - previous_asset_value)
                previous_total_value += previous_asset_value
                
            except Exception as e:
                self.logger.error(f"Could not fetch 24h performance for {asset}: {e}")
                # In case of an error, assume its value was stable
                current_price = self.get_live_price(symbol)
                previous_total_value += amount * current_price

        # Calculate the percentage change based on the total starting value
        pnl_pct = (pnl_usd / previous_total_value) * 100 if previous_total_value > 0 else 0.0
        
        return pnl_usd, pnl_pct

    def get_recent_trades(self, limit: int = 10):
        """
        Fetches the user's most recent trades from the exchange and formats them
        into a clean DataFrame for display.

        Args:
            limit (int): The maximum number of recent trades to fetch.

        Returns:
            pd.DataFrame: A DataFrame of recent trades.
        """
        try:
            # We fetch from all symbols by not passing a symbol argument
            trades = self.client.fetch_my_trades(limit=limit)
            if not trades:
                return pd.DataFrame()

            # Convert to DataFrame and format for display
            df = pd.DataFrame(trades)
            df_formatted = df[['datetime', 'symbol', 'side', 'price', 'amount', 'cost', 'fee']]
            
            # Make the 'fee' column more readable
            df_formatted['fee'] = df_formatted['fee'].apply(lambda x: f"{x['cost']:.4f} {x['currency']}")
            
            return df_formatted.sort_values(by='datetime', ascending=False)
        
        except Exception as e:
            self.logger.error(f"Failed to fetch recent trades: {e}")
            return pd.DataFrame()

    def does_symbol_exist(self, symbol: str) -> bool:
        """Checks if a given trading symbol exists on the exchange."""
        return symbol in self.client.exchange.markets

    def get_execution_symbol(self, analysis_symbol: str) -> str | None:
        """
        Translates a data analysis symbol (e.g., MATIC/USDT) to a compliant
        execution symbol (e.g., MATIC/USDC), if it exists.
        
        Returns the execution symbol or None if it's not available.
        """
        # If the symbol is already a USDC pair, it's compliant.
        if analysis_symbol.endswith('/USDC'):
            return analysis_symbol
            
        # If it's a USDT pair, check if the USDC equivalent exists.
        if analysis_symbol.endswith('/USDT'):
            base_currency = analysis_symbol.split('/')[0]
            execution_symbol = f"{base_currency}/USDC"
            
            if self.does_symbol_exist(execution_symbol):
                return execution_symbol
            else:
                return None # The compliant pair does not exist.
                
        # Return None for any other quote currency (e.g., /BTC, /ETH)
        return None

    def fetch_all_trades_since(self, start_date):
        """
        Fetches all trades for a specific list of user-defined symbols from a 
        given start date. This is much faster than querying all markets.
        """
        self.logger.info(f"Starting targeted historical trade fetch since {start_date}...")
        
        start_datetime = datetime.datetime.combine(start_date, datetime.datetime.min.time())
        since_timestamp = int(start_datetime.timestamp() * 1000)
        
        all_trades = []
        
        # --- FIX IS HERE: Use the user-defined list instead of all markets ---
        # This dramatically reduces the number of API calls from thousands to just a handful.
        symbols_to_check = [
            "BTC/USDC", "ETH/USDC", "SOL/USDC", "ADA/USDC", "DOGE/USDC", 
            "SHIB/USDC", "XRP/USDC", "PEPE/USDC", "NEIRO/USDC", "LTC/USDC", 
            "UNI/USDC", "WLD/USDC", "TRUMP/USDC"
        ]
        
        progress_bar = st.progress(0, text="Fetching trade history for your core symbols...")

        for i, symbol in enumerate(symbols_to_check):
            try:
                trades = self.client.fetch_my_trades(symbol=symbol, since=since_timestamp, limit=1000)
                if trades:
                    all_trades.extend(trades)
                    self.logger.info(f"Found {len(trades)} trades for {symbol}.")
                
                progress_bar.progress((i + 1) / len(symbols_to_check), text=f"Checked {symbol}...")
            except Exception:
                # Silently ignore symbols that might fail (e.g., delisted)
                continue
                
        progress_bar.empty()
        
        if not all_trades:
            return pd.DataFrame()

        df = pd.DataFrame(all_trades)
        df['timestamp'] = pd.to_datetime(df['datetime'])
        return df.sort_values(by='timestamp').reset_index(drop=True)
