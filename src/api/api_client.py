import os
from dotenv import load_dotenv, find_dotenv
import ccxt

# Load environment variables
load_dotenv(find_dotenv())

# Retrieve API keys from environment
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

class BinanceClient:
    def __init__(self, testnet: bool = False):
        if not API_KEY or not API_SECRET:
            raise ValueError("BINANCE_API_KEY and BINANCE_API_SECRET must be set in environment variables.")

        # Initialize CCXT Binance client
        self.exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'enableRateLimit': True,
        })
        if testnet:
            # Enable sandbox/testnet mode
            self.exchange.set_sandbox_mode(True)

    def fetch_balance(self):
        return self.exchange.fetch_balance()

    def fetch_ticker(self, symbol: str):
        return self.exchange.fetch_ticker(symbol)

    def create_order(self, symbol: str, side: str, order_type: str, amount: float, price: float = None):
        if order_type.lower() == 'limit':
            return self.exchange.create_limit_order(symbol, side, amount, price)
        else:
            return self.exchange.create_market_order(symbol, side, amount)