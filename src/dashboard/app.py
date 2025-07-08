import os
import sys
from dotenv import load_dotenv, find_dotenv
import streamlit as st
from streamlit_option_menu import option_menu

# ─── Make 'src/' a module search path ────────────────────────────────────────
CURRENT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
sys.path.insert(0, SRC_DIR)

# ─── Load environment variables ─────────────────────────────────────────────
load_dotenv(find_dotenv())

# ─── Page configuration ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Crypto Algo Bot Dashboard",
    page_icon="🤖",
    layout="wide",
)

# ─── Sidebar navigation ─────────────────────────────────────────────────────
with st.sidebar:
    selected = option_menu(
        menu_title=None,
        options=["Home", "Backtesting", "Live Trading", "Settings"],
        icons=["house", "bar-chart-line", "rocket", "gear"],
        default_index=0,
        key="main-menu"
    )

# ─── Import your page renderers from the renamed folder ─────────────────────
from dashboard.page_modules.home import render_home
from dashboard.page_modules.backtesting import render_backtesting
from dashboard.page_modules.live_trading import render_live_trading
from dashboard.page_modules.settings import render_settings

# ─── Initialize Binance exchange once ───────────────────────────────────────
import ccxt
API_KEY    = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
exchange   = None
if API_KEY and API_SECRET:
    exchange = ccxt.binance({
        "apiKey": API_KEY,
        "secret": API_SECRET,
        "enableRateLimit": True,
    })

# ─── Dispatch to the selected page ──────────────────────────────────────────
if selected == "Home":
    render_home(exchange)
elif selected == "Backtesting":
    render_backtesting(exchange)
elif selected == "Live Trading":
    render_live_trading(exchange)
else:
    render_settings()