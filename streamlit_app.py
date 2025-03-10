import time
from datetime import datetime
import pytz
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import requests
import alpaca_trade_api as tradeapi
import backtrader as bt

# Alpaca API Credentials
API_KEY = 'PKU5UOUPLT3W3V1HJG59'
API_SECRET = 'EghcfIHcnkdTtNpLO11VvvBehq5iXKmJk4uPeXp0'
BASE_URL = 'https://paper-api.alpaca.markets'

# Connect to Alpaca API
api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')

eastern = pytz.timezone('US/Eastern')

st.set_page_config(page_title="Trading Dashboard", page_icon="📈", layout="wide")
st.title("📈 Automated Trading Dashboard")

# Define market open and close times
MARKET_OPEN = 9
MARKET_CLOSE = 16

def is_market_open():
    current_time = datetime.now(eastern).time()
    market_open_time = datetime.now(eastern).replace(hour=MARKET_OPEN, minute=30, second=0, microsecond=0).time()
    market_close_time = datetime.now(eastern).replace(hour=MARKET_CLOSE, minute=0, second=0, microsecond=0).time()
    return market_open_time <= current_time <= market_close_time

# Trading strategy class for buying stocks in an upward trend
class MonthlyProfitOptimizationStrategy(bt.Strategy):
    params = dict(
        rsi_period=14,
        ema_period=20,
        tema_period=30,
        adx_period=14,
        atr_period=14,
        rsi_overbought=70,
        adx_trend_strength=20,
        stop_loss_factor=0.5,
        trailing_stop_factor=0.1,
    )

    def __init__(self):
        self.ema = bt.indicators.EMA(self.data.close, period=self.params.ema_period)
        self.tema = bt.indicators.TEMA(self.data.close, period=self.params.tema_period)
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.adx = bt.indicators.ADX(self.data, period=self.params.adx_period)
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)
        self.highest_price = None
        self.entry_price = None
        self.stop_loss = None

    def next(self):
        if not self.position:
            if self.ema > self.tema and self.rsi < self.params.rsi_overbought and self.adx > self.params.adx_trend_strength:
                available_cash = self.broker.get_cash()
                price = self.data.close[0]
                max_shares = int(available_cash / price)
                self.buy(size=max_shares)
                self.highest_price = self.data.close[0]
                self.entry_price = self.data.close[0]
                self.stop_loss = self.data.close[0] * self.params.stop_loss_factor
        else:
            self.highest_price = max(self.highest_price, self.data.close[0])
            trailing_stop = self.highest_price * (1 - self.params.trailing_stop_factor)
            if self.data.close[0] < trailing_stop or self.data.close[0] < self.stop_loss:
                self.close()

# Fetch Market Data
def get_market_data():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=dow-jones-industrial-average,s&p-500,nasdaq-100&vs_currencies=usd&include_market_cap=true&include_24hr_change=true"
    try:
        response = requests.get(url).json()
        return {
            "DOW": response['dow-jones-industrial-average'],
            "S&P 500": response['s&p-500'],
            "NASDAQ": response['nasdaq-100']
        }
    except:
        return None

# Fetch Financial News
def get_news():
    url = "https://newsapi.org/v2/top-headlines?category=business&apiKey=YOUR_NEWS_API_KEY"
    try:
        response = requests.get(url).json()
        articles = response.get("articles", [])[:5]
        return [(article["title"], article["url"]) for article in articles]
    except:
        return []

# UI Layout
st.sidebar.header("⚙️ Trading Controls")
selected_symbol = st.sidebar.selectbox("Select Symbol", ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META', 'TSLA', 'NVDA', 'BA', 'DIS', 'NFLX'])

st.sidebar.header("📌 Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Live Trading", "Portfolio", "Settings"])

if page == "Dashboard":
    st.subheader("📊 Market Overview")
    market_data = get_market_data()
    if market_data:
        col1, col2, col3 = st.columns(3)
        col1.metric("DOW", f"{market_data['DOW']['usd']}", f"{market_data['DOW']['usd_24h_change']:.2f}%")
        col2.metric("S&P 500", f"{market_data['S&P 500']['usd']}", f"{market_data['S&P 500']['usd_24h_change']:.2f}%")
        col3.metric("NASDAQ", f"{market_data['NASDAQ']['usd']}", f"{market_data['NASDAQ']['usd_24h_change']:.2f}%")
    
    st.subheader("📰 Market News")
    news = get_news()
    for title, url in news:
        st.markdown(f"[🔗 {title}]({url})")
    
    st.subheader("📈 Real-Time Stock Data")
    data = api.get_barset(selected_symbol, 'minute', limit=30)[selected_symbol]
    if data:
        df = pd.DataFrame([{ 'Time': bar.t, 'Close': bar.c } for bar in data])
        fig = go.Figure(data=[go.Candlestick(x=df['Time'], open=df['Close'], high=df['Close'], low=df['Close'], close=df['Close'])])
        fig.update_layout(template='plotly_dark')
        st.plotly_chart(fig)

elif page == "Portfolio":
    st.subheader("💰 Portfolio Overview")
    account = api.get_account()
    st.write(f"**Buying Power:** ${float(account.cash):.2f}")
    st.write(f"**Portfolio Value:** ${float(account.equity):.2f}")

elif page == "Settings":
    st.subheader("⚙️ Settings")
    st.write("Configure API keys and preferences here.")
