import numpy as np

def compute_metrics(equity_df, periods_per_year: int = 365) -> dict:
    """
    Given an equity DataFrame with 'equity' and 'returns', computes:
    - total_return
    - annualized_return (approx.)
    - sharpe_ratio (annualized, risk-free=0)
    - max_drawdown
    """
    total_return = equity_df["equity"].iloc[-1] / equity_df["equity"].iloc[0] - 1.0
    n_periods = len(equity_df)

    # Approximate annualized return
    annualized_return = (1 + total_return) ** (periods_per_year / n_periods) - 1 if n_periods > 0 else 0.0

    # Sharpe ratio (assume zero risk-free rate)
    ret = equity_df["returns"]
    if ret.std() != 0:
        sharpe = (ret.mean() / ret.std()) * np.sqrt(periods_per_year)
    else:
        sharpe = float("nan")

    # Max drawdown
    max_dd = float(equity_df["drawdown"].min())

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_dd
    }
