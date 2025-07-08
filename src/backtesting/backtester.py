import pandas as pd

class Backtester:
    def __init__(self, data: pd.DataFrame, strategy_func):
        self.data = data.copy()
        self.strategy = strategy_func
        self.results = None

    def run(self):
        df = self.strategy(self.data)
        # Implementar lógica de backtest: entradas, saídas, cálculo de PnL
        # Exemplo simplificado:
        df['returns'] = df['close'].pct_change()
        df['strategy_returns'] = df['returns'] * df['signal'].shift(1).fillna(0)
        self.results = df
        return df
