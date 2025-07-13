import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv, find_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Import your existing, powerful modules
from api.api_client import BinanceClient
from trading.trader import Trader
from trading.strategy import get_strategy_function
from backtesting.data_loader import fetch_ohlcv

# --- Setup ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
load_dotenv(find_dotenv())

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# --- Initialize the core components ---
try:
    client = BinanceClient(api_key=API_KEY, secret_key=API_SECRET)
    trader = Trader(client)
    strategy_fn = get_strategy_function("Reverse RSI")
except Exception as e:
    print(f"Failed to initialize trader: {e}")
    trader = None

SYMBOLS_TO_MONITOR = ["BTC/USDC", "ETH/USDC", "SOL/USDC", "XRP/USDC", "AVAX/USDC"]

# --- PNL Calculation Engine ---
def calculate_pnl(trades_df):
    """
    Processes a raw trades DataFrame to calculate PNL on a position-by-position basis
    using a First-In, First-Out (FIFO) accounting method.
    """
    if trades_df.empty:
        return pd.DataFrame()

    positions = {}
    closed_trades = []

    for _, trade in trades_df.iterrows():
        symbol, side, amount, price = trade['symbol'], trade['side'], trade['amount'], trade['price']

        if symbol not in positions:
            positions[symbol] = {'buys': []}
        
        if side == 'buy':
            positions[symbol]['buys'].append({'amount': amount, 'price': price})
        elif side == 'sell':
            sell_amount, realized_pnl = amount, 0
            while sell_amount > 0 and positions[symbol]['buys']:
                buy_tr = positions[symbol]['buys'][0]
                match_amount = min(sell_amount, buy_tr['amount'])
                realized_pnl += (match_amount * price) - (match_amount * buy_tr['price'])
                sell_amount -= match_amount
                buy_tr['amount'] -= match_amount
                if buy_tr['amount'] < 1e-9:
                    positions[symbol]['buys'].pop(0)

            closed_trades.append({'timestamp': trade['timestamp'], 'symbol': symbol, 'pnl': realized_pnl})

    if not closed_trades:
        return pd.DataFrame()
    return pd.DataFrame(closed_trades)


# --- Helper Functions to Format Messages ---

def format_summary_message():
    if not trader: return "Trader not initialized."
    equity = trader.get_total_equity()
    balance = trader.get_usdc_balance()
    pnl_usd, pnl_pct = trader.get_24h_performance()
    return (
        f"📊 <b>Portfolio Status</b> 📊\n\n"
        f"📈 <b>Total Equity:</b> ${equity:,.2f}\n"
        f"💰 <b>Available USDC:</b> ${balance:,.2f}\n"
        f"⏱️ <b>24h P&L:</b> ${pnl_usd:,.2f} ({pnl_pct:.2f}%)"
    )

def format_positions_message():
    if not trader: return "Trader not initialized."
    positions_df = trader.get_open_positions()
    if positions_df.empty: return "No open positions."
    message = "✅ <b>Open Positions</b> ✅\n\n"
    for _, row in positions_df.iterrows():
        message += (
            f"<b>{row['Symbol']}</b>\n"
            f"  - Amount: {row['Amount']:.6f}\n"
            f"  - Entry Price: ${row['Entry Price']:,.2f}\n"
            f"  - Current Price: ${row['Current Price']:,.2f}\n"
            f"  - <b>P&L: ${row['P&L ($)']:,.2f} ({row['P&L (%)']:.2f}%)</b>\n\n"
        )
    return message

def format_rsi_message():
    if not trader: return "Trader not initialized."
    message = "🔍 <b>RSI Status (4h)</b> 🔍\n\n"
    for symbol in SYMBOLS_TO_MONITOR:
        try:
            df = fetch_ohlcv(trader.client.exchange, symbol, '4h', limit=201)
            sig_df = strategy_fn(df, window=7)
            current_rsi = sig_df['rsi'].iloc[-1]
            message += f"<b>{symbol}:</b> {current_rsi:.2f}\n"
        except Exception:
            message += f"<b>{symbol}:</b> Error fetching data\n"
    return message

def format_pnl_report_message(pnl_df):
    if pnl_df.empty: return "No closed trades found to generate a PNL report."
    total_pnl = pnl_df['pnl'].sum()
    wins = (pnl_df['pnl'] > 0).sum()
    num_trades = len(pnl_df)
    win_rate = (wins / num_trades) * 100 if num_trades > 0 else 0
    message = (
        f"💰 <b>Historical PNL Report</b> 💰\n\n"
        f"✅ <b>Total Realized P&L:</b> ${total_pnl:,.2f}\n"
        f"📈 <b>Total Closed Trades:</b> {num_trades}\n"
        f"🎯 <b>Win Rate:</b> {win_rate:.2f}%\n\n"
        f"--- <b>Performance by Asset</b> ---\n"
    )
    asset_pnl = pnl_df.groupby('symbol')['pnl'].sum().sort_values(ascending=False)
    for symbol, pnl in asset_pnl.items():
        message += f"  - <b>{symbol}:</b> ${pnl:,.2f}\n"
    return message

# --- Asynchronous Task for PNL Analysis ---
async def run_pnl_analysis_and_report(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id, days = job.chat_id, job.data['days']
    try:
        await context.bot.send_message(chat_id, text=f"⏳ Starting PNL analysis for the last {days} days... This may take a few minutes.")
        start_date = datetime.now() - timedelta(days=days)
        trades_df = trader.fetch_all_trades_since(start_date.date())
        pnl_df = calculate_pnl(trades_df)
        report_message = format_pnl_report_message(pnl_df)
        await context.bot.send_message(chat_id, text=report_message, parse_mode='HTML')
    except Exception as e:
        await context.bot.send_message(chat_id, text=f"🚨 An error occurred during PNL analysis: {e}")

# --- Telegram Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I am your trading bot reporter. Available commands:\n"
                                    "/status - Full portfolio summary\n"
                                    "/positions - Detailed open positions\n"
                                    "/rsi - Live RSI for monitored assets\n"
                                    "/pnl [days] - Historical PNL report (e.g., /pnl 30)")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    summary = format_summary_message()
    positions = format_positions_message()
    await update.message.reply_html(f"{summary}\n\n---\n\n{positions}")

async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(format_positions_message())

async def rsi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(format_rsi_message())

async def pnl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = 30
    if context.args:
        try:
            days = int(context.args[0])
        except (ValueError, IndexError):
            await update.message.reply_text("Invalid format. Please use `/pnl [number_of_days]`.")
            return
    await update.message.reply_text(f"✅ Roger that! Queuing PNL analysis for the last {days} days. I will send you the report when it's ready.")
    context.application.job_queue.run_once(
        run_pnl_analysis_and_report, 
        when=1, 
        data={'days': days}, 
        chat_id=update.effective_chat.id,
        name=f"pnl_analysis_{update.effective_chat.id}"
    )

# --- Scheduled Update Function ---
async def send_periodic_update(context: ContextTypes.DEFAULT_TYPE):
    logging.info("Sending periodic update...")
    summary = format_summary_message()
    positions = format_positions_message()
    await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"{summary}\n\n---\n\n{positions}", parse_mode='HTML')

# --- Main Application ---
def main():
    if not TELEGRAM_TOKEN or not trader:
        print("🚨 Error: Telegram Token not found or Trader failed to initialize. Exiting.")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("positions", positions_command))
    application.add_handler(CommandHandler("rsi", rsi_command))
    application.add_handler(CommandHandler("pnl", pnl_command))
    
    job_queue = application.job_queue
    job_queue.run_repeating(send_periodic_update, interval=1800, first=10)

    print("✅ Telegram bot started and running...")
    application.run_polling()

if __name__ == '__main__':
    main()
