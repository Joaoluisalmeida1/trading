import ccxt

class BinanceClient:
    def __init__(self, api_key: str, secret_key: str, testnet: bool = False):
        """
        Initializes the Binance client with API keys provided as arguments.
        """
        if not api_key or not secret_key:
            raise ValueError("API key and secret key must be provided during client initialization.")

        # Initialize CCXT Binance client with the provided keys
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
        })
        
        if testnet:
            # Enable sandbox/testnet mode if requested
            self.exchange.set_sandbox_mode(True)

        self.exchange.load_markets()

    def fetch_balance(self):
        """Fetches the account's entire balance information."""
        try:
            return self.exchange.fetch_balance()
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return None

    def fetch_ticker(self, symbol: str):
        """Fetches the latest price ticker for a symbol."""
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            print(f"Error fetching ticker for {symbol}: {e}")
            return None

    def create_order(self, symbol: str, side: str, order_type: str, amount: float, price: float = None):
        """Creates a market or limit order."""
        try:
            if order_type.lower() == 'limit':
                return self.exchange.create_limit_order(symbol, side, amount, price)
            else:
                return self.exchange.create_market_order(symbol, side, amount)
        except Exception as e:
            print(f"Error creating order for {symbol}: {e}")
            return {'error': str(e)}
            
    def fetch_open_orders(self, symbol: str = None):
        """Fetches all open orders, optionally for a specific symbol."""
        try:
            return self.exchange.fetch_open_orders(symbol)
        except Exception as e:
            print(f"Error fetching open orders: {e}")
            return []

    def cancel_order(self, order_id: str, symbol: str):
        """Cancels an existing open order by its ID."""
        try:
            return self.exchange.cancel_order(order_id, symbol)
        except Exception as e:
            print(f"Error canceling order {order_id} for {symbol}: {e}")
            return {'error': str(e)}

    def fetch_order_book(self, symbol: str, limit: int = 25):
        """Fetches the order book for a given symbol."""
        try:
            return self.exchange.fetch_order_book(symbol, limit)
        except Exception as e:
            print(f"Error fetching order book for {symbol}: {e}")
            return None

    def fetch_my_trades(self, symbol: str, since=None, limit: int = 100):
        """Fetches the user's past trades for a specific symbol."""
        try:
            return self.exchange.fetch_my_trades(symbol, since, limit)
        except Exception as e:
            print(f"Error fetching my trades for {symbol}: {e}")
            return []