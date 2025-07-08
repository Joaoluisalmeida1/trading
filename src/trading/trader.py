#whatever its going on here
from api.api_client import BinanceClient
from utils.logger import get_logger

class Trader:
    def __init__(self, client: BinanceClient):
        self.client = client
        self.logger = get_logger(self.__class__.__name__)

    def buy(self, symbol: str, amount: float, price: float = None, order_type: str = 'market'):
        self.logger.info(f"Placing BUY order: {symbol}, amount={amount}, price={price}, type={order_type}")
        order = self.client.create_order(symbol, 'buy', order_type, amount, price)
        self.logger.info(f"Order result: {order}")
        return order

    def sell(self, symbol: str, amount: float, price: float = None, order_type: str = 'market'):
        self.logger.info(f"Placing SELL order: {symbol}, amount={amount}, price={price}, type={order_type}")
        order = self.client.create_order(symbol, 'sell', order_type, amount, price)
        self.logger.info(f"Order result: {order}")
        return order