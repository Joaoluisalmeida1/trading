import streamlit as st
import plotly.graph_objects as go
import plotly.express   as px
from backtesting.metrics import compute_metrics
import pandas as pd

def show_report(equity_df, trades_df=None, price_df=None):
    # ─── Equity curve ──────────────────────────────────────────────────────────
    st.subheader("📈 Equity Curve")
    fig_eq = px.line(equity_df, x=equity_df.index, y="equity", title="Equity Curve")
    st.plotly_chart(fig_eq, use_container_width=True)

    # ─── Performance metrics ───────────────────────────────────────────────────
    base_stats = compute_metrics(equity_df)

    # Compute trade‐level stats if we have completed trades
    extra = {"win_rate": None, "avg_pnl_pct": None, "num_trades": 0}
    if trades_df is not None and not trades_df.empty:
        df = trades_df.reset_index(drop=True).copy()

        # Compute absolute P&L (SELL rows only) and cost per trade
        pnls, pnls_pct = [], []
        for i in range(0, len(df) - 1, 2):
            buy  = df.loc[i]
            sell = df.loc[i+1]
            cost     = buy["price"] * buy["amount"] + buy.get("commission", 0)
            proceeds = sell["price"] * sell["amount"] - sell.get("commission", 0)
            pnl      = proceeds - cost
            pnl_pct  = (pnl / cost) * 100 if cost else 0

            # annotate back into df
            df.at[i+1, "pnl"]     = pnl
            df.at[i+1, "pnl_pct"] = pnl_pct

            pnls.append(pnl)
            pnls_pct.append(pnl_pct)

        wins = sum(1 for x in pnls if x > 0)
        total = len(pnls)
        extra = {
            "win_rate":   wins / total if total else None,
            "avg_pnl_pct": sum(pnls_pct) / total if total else None,
            "num_trades": total
        }

        # show the trades table with new columns
        st.subheader("⚔️ Executed Trades with P&L")
        # Format columns for display
        df["pnl"]     = df["pnl"].map(lambda x: f"{x:.4f}" if pd.notnull(x) else "")
        df["pnl_pct"] = df["pnl_pct"].map(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
        st.dataframe(df, use_container_width=True)

    # Merge and display all stats
    stats = {**base_stats, **extra}
    st.subheader("📊 Performance Metrics")
    st.json(stats)

    # ─── Drawdown ──────────────────────────────────────────────────────────────
    st.subheader("📉 Drawdown Over Time")
    fig_dd = px.area(equity_df, x=equity_df.index, y="drawdown", title="Drawdown")
    st.plotly_chart(fig_dd, use_container_width=True)

    # ─── Price + Buy/Sell Markers ──────────────────────────────────────────────
    if price_df is not None and trades_df is not None and not trades_df.empty:
        st.subheader("💹 Price Chart with Buy/Sell Markers")

        # Build a candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=price_df.index,
            open=price_df["open"],
            high=price_df["high"],
            low=price_df["low"],
            close=price_df["close"],
            name="Price"
        )])

        # Plot buy markers
        buys = trades_df[trades_df["side"].str.startswith("BUY")]
        fig.add_trace(go.Scatter(
            x=buys["timestamp"],
            y=buys["price"],
            mode="markers",
            marker_symbol="triangle-up",
            marker_color="green",
            marker_size=12,
            name="Buys"
        ))

        # Plot sell markers (including SL exits)
        sells = trades_df[trades_df["side"].str.startswith("SELL")]
        fig.add_trace(go.Scatter(
            x=sells["timestamp"],
            y=sells["price"],
            mode="markers",
            marker_symbol="triangle-down",
            marker_color="red",
            marker_size=12,
            name="Sells"
        ))

        fig.update_layout(
            xaxis=dict(title="Time"),
            yaxis=dict(title="Price"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig, use_container_width=True)

    # ─── Trades table ──────────────────────────────────────────────────────────
     # ─── Trades table with P&L ────────────────────────────────────────────────
    if trades_df is not None and not trades_df.empty:
        st.subheader("⚔️ Executed Trades with P&L")

        # Compute P&L only on round-trip trades (BUY → SELL pairs)
        df = trades_df.copy().reset_index(drop=True)
        df["pnl"] = None

        # Iterate over pairs: assume even-indexed rows are BUY, odd are SELL
        for i in range(0, len(df) - 1, 2):
            buy  = df.loc[i]
            sell = df.loc[i+1]
            # net proceeds minus net cost
            cost         = buy["price"]  * buy["amount"]  + buy.get("commission", 0)
            proceeds     = sell["price"] * sell["amount"] - sell.get("commission", 0)
            roundtrip_pnl = proceeds - cost
            df.at[i+1, "pnl"] = roundtrip_pnl

        # Format P&L column
        df["pnl"] = df["pnl"].astype(float).map(lambda x: f"{x:.4f}" if pd.notnull(x) else "")

        st.dataframe(df, use_container_width=True)
