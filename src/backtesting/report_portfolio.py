import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from backtesting.metrics import compute_metrics

def show_portfolio_report(equity_df, trades_df=None, price_data=None):
    """
    Generates a comprehensive, corrected, and enhanced report for a portfolio-level backtest.
    """
    st.header("1. Overall Portfolio Performance")

    # --- Portfolio Equity Curve ---
    st.subheader("📈 Portfolio Equity Curve")
    fig_eq = px.line(equity_df, x=equity_df.index, y="equity", title="Portfolio Equity Curve")
    st.plotly_chart(fig_eq, use_container_width=True)

    # --- P&L and Trade Stats Calculation for Metrics Section ---
    trade_stats = {}
    if trades_df is not None and not trades_df.empty:
        trades_copy = trades_df.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
        trades_copy["pnl"] = pd.NA
        trades_copy["pnl_pct"] = pd.NA

        for symbol in trades_copy["symbol"].unique():
            symbol_trades = trades_copy[trades_copy["symbol"] == symbol].copy().reset_index()
            for i in range(0, len(symbol_trades) - 1, 2):
                buy_row = symbol_trades.iloc[i]
                sell_row = symbol_trades.iloc[i+1]
                
                cost = buy_row["price"] * buy_row["amount"] + buy_row.get("commission", 0)
                proceeds = sell_row["price"] * sell_row["amount"] - sell_row.get("commission", 0)
                pnl = proceeds - cost
                pnl_pct = (pnl / cost) * 100 if cost > 0 else 0
                
                original_index = sell_row['index']
                trades_copy.loc[original_index, "pnl"] = pnl
                trades_copy.loc[original_index, "pnl_pct"] = pnl_pct

        pnl_df = trades_copy.dropna(subset=['pnl'])
        if not pnl_df.empty:
            wins = (pnl_df['pnl'] > 0).sum()
            num_trades = len(pnl_df)
            trade_stats = {
                "num_trades": num_trades,
                "win_rate": (wins / num_trades) if num_trades > 0 else 0,
                "avg_pnl_pct": pnl_df['pnl_pct'].mean()
            }
        
        trades_df = trades_copy

    # --- ENHANCED: Top-Level Portfolio Metrics ---
    st.subheader("📊 Portfolio Performance Metrics")
    base_stats = compute_metrics(equity_df)
    combined_stats = {**base_stats, **trade_stats}
    st.json(combined_stats)
    
    # --- Portfolio Drawdown Chart ---
    st.subheader("📉 Portfolio Drawdown Over Time")
    fig_dd = px.area(equity_df, x=equity_df.index, y="drawdown", title="Portfolio Drawdown", labels={"drawdown": "Drawdown", "index": "Date"})
    fig_dd.update_yaxes(tickformat=".2%")
    st.plotly_chart(fig_dd, use_container_width=True)

    if 'pnl' not in trades_df.columns:
        st.warning("No trades were executed to generate further analysis.")
        return

    st.header("2. Per-Asset Performance Analysis")

    st.subheader("🔍 Per-Asset Performance Breakdown")
    pnl_df = trades_df.dropna(subset=['pnl'])
    if not pnl_df.empty:
        asset_stats = pnl_df.groupby('symbol').agg(
            **{'Total P&L (USDC)': ('pnl', 'sum'),
               '# of Trades': ('pnl', 'count'),
               'Avg. P&L / Trade (%)': ('pnl_pct', 'mean'),
               'Wins': ('pnl', lambda x: (x > 0).sum())}
        )
        asset_stats['Win Rate'] = (asset_stats['Wins'] / asset_stats['# of Trades'])
        total_pnl = asset_stats['Total P&L (USDC)'].sum()
        asset_stats['Contribution'] = (asset_stats['Total P&L (USDC)'] / total_pnl)
        
        st.dataframe(asset_stats[['Total P&L (USDC)', 'Contribution', 'Win Rate', '# of Trades', 'Avg. P&L / Trade (%)']].style.format({
            'Total P&L (USDC)': '{:,.2f}', 'Contribution': '{:.2%}',
            'Win Rate': '{:.2%}', 'Avg. P&L / Trade (%)': '{:.2f}%'
        }), use_container_width=True)

    st.header("3. Detailed Trade-Level Analysis")

    st.subheader("⚔️ Detailed Trade Log")
    
    display_trades_df = trades_df.copy()
    display_trades_df["pnl"] = display_trades_df["pnl"].map(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
    display_trades_df["pnl_pct"] = display_trades_df["pnl_pct"].map(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
    
    symbol_filter = st.selectbox("Filter Trades by Symbol", options=["All"] + sorted(trades_df["symbol"].unique().tolist()))
    
    # --- BUG FIX IS HERE ---
    if symbol_filter == "All":
        # If "All" is selected, use the entire dataframe
        display_df = display_trades_df
    else:
        # Otherwise, filter the dataframe by the selected symbol
        display_df = display_trades_df[display_trades_df["symbol"] == symbol_filter]
    
    st.dataframe(display_df[['timestamp', 'symbol', 'side', 'price', 'amount', 'commission', 'pnl', 'pnl_pct']], use_container_width=True)

    st.subheader("💹 Price Chart with Trade Markers")
    
    if price_data:
        chart_symbol = st.selectbox("Select Symbol for Price Chart", options=sorted(list(price_data.keys())))
        if chart_symbol:
            price_df = price_data[chart_symbol]
            symbol_trades = trades_df[trades_df["symbol"] == chart_symbol]
            
            fig = go.Figure(data=[go.Candlestick(
                x=price_df.index,
                open=price_df["open"], high=price_df["high"],
                low=price_df["low"], close=price_df["close"],
                name=f"{chart_symbol} Price"
            )])

            buys = symbol_trades[symbol_trades["side"].str.startswith("BUY")]
            sells = symbol_trades[symbol_trades["side"].str.startswith("SELL")]

            fig.add_trace(go.Scatter(
                x=buys["timestamp"], y=buys["price"], mode="markers",
                marker_symbol="triangle-up", marker_color="green", marker_size=12, name="Buys"
            ))
            fig.add_trace(go.Scatter(
                x=sells["timestamp"], y=sells["price"], mode="markers",
                marker_symbol="triangle-down", marker_color="red", marker_size=12, name="Sells"
            ))

            fig.update_layout(
                title=f"Trade Executions for {chart_symbol}",
                xaxis_rangeslider_visible=False,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
