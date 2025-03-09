import time
from datetime import datetime, timedelta
import pytz
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import alpaca_trade_api as tradeapi
import backtrader as bt

# Alpaca API Credentials
API_KEY = 'PKU5UOUPLT3W3V1HJG59'
API_SECRET = 'EghcfIHcnkdTtNpLO11VvvBehq5iXKmJk4uPeXp0'
BASE_URL = 'https://paper-api.alpaca.markets'

# Connect to Alpaca API
api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')

# Timezone for Market Hours
eastern = pytz.timezone('US/Eastern')

# Streamlit Setup
st.set_page_config(page_title="Trading Dashboard", page_icon="📈", layout="wide")
st.title("Automated Trading Dashboard")

# Trading Strategy Class
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
                self.highest_price = price
                self.entry_price = price
                self.stop_loss = price * self.params.stop_loss_factor
        else:
            self.highest_price = max(self.highest_price, self.data.close[0])
            trailing_stop = self.highest_price * (1 - self.params.trailing_stop_factor)
            if self.data.close[0] < trailing_stop or self.data.close[0] < self.stop_loss:
                self.close()

# Fetch Live Data
def fetch_data(ticker):
    try:
        bars = api.get_bars(ticker, tradeapi.TimeFrame.Minute, limit=30).df
        bars.index = pd.to_datetime(bars.index)
        return bars[['open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        st.error(f"Data Fetch Error for {ticker}: {e}")
        return None

# Portfolio Status
def get_portfolio():
    account = api.get_account()
    positions = api.list_positions()
    portfolio = {
        "cash": float(account.cash),
        "equity": float(account.equity),
        "profit_loss": float(account.equity) - float(account.last_equity),
        "positions": []
    }
    for position in positions:
        portfolio["positions"].append({
            "symbol": position.symbol,
            "qty": int(position.qty),
            "avg_entry_price": float(position.avg_entry_price),
            "current_price": float(position.current_price),
            "unrealized_pl": float(position.unrealized_pl)
        })
    return portfolio

# Candlestick Chart
def create_candlestick_chart(data, symbol):
    fig = go.Figure(data=[go.Candlestick(x=data.index,
                open=data['open'], high=data['high'], low=data['low'], close=data['close'])])
    fig.update_layout(title=f'{symbol} Price Chart', yaxis_title='Price', template='plotly_dark', height=500)
    return fig

# Run Live Trading
def run_live_trading(stock_list):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(MonthlyProfitOptimizationStrategy)
    while True:
        if api.get_clock().is_open:
            for stock in stock_list:
                stock_data = fetch_data(stock)
                if stock_data is not None:
                    data_feed = bt.feeds.PandasData(dataname=stock_data)
                    cerebro.adddata(data_feed)
                    cerebro.run()
            portfolio = get_portfolio()
            st.subheader("Portfolio Summary")
            st.write(f"Cash: ${portfolio['cash']:.2f}")
            st.write(f"Equity: ${portfolio['equity']:.2f}")
            st.write(f"Profit/Loss: ${portfolio['profit_loss']:.2f}")
            st.subheader("Open Positions")
            if portfolio["positions"]:
                st.dataframe(pd.DataFrame(portfolio["positions"]))
            else:
                st.write("No open positions.")
            time.sleep(15 * 60)
        else:
            st.write("Market Closed. Waiting...")
            time.sleep(60 * 60)

# Sidebar and UI Setup
st.sidebar.header("Trading Controls")
trading_enabled = st.sidebar.toggle("Enable Trading", value=True)
risk_percentage = st.sidebar.slider("Risk Per Trade (%)", 0.1, 5.0, 2.0)
selected_symbol = st.selectbox("Select Symbol", ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META', 'TSLA', 'NVDA', 'BA', 'DIS', 'NFLX'])
if st.sidebar.button("Start Trading"):
    run_live_trading([selected_symbol])

data = fetch_data(selected_symbol)
if data is not None:
    st.plotly_chart(create_candlestick_chart(data, selected_symbol), use_container_width=True)

portfolio = get_portfolio()
st.subheader("Account Summary")
st.write(f"Buying Power: ${portfolio['cash']:.2f}")
st.write(f"Portfolio Value: ${portfolio['equity']:.2f}")


# Custom Styling
st.markdown("""
    <style>
    body { background-color: #0e1117; color: white; font-family: 'Arial', sans-serif; }
    .stSidebar { background-color: #161b22; }
    .css-1d391kg { padding: 20px; }
    .stButton>button { background-color: #238636; color: white; font-weight: bold; }
    .stTabs { font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

# Navigation
st.sidebar.title("📌 Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Live Trading", "Portfolio", "Settings"])

# Dashboard Page
if page == "Dashboard":
    st.title("📈 Real-Time Trading Dashboard")
    selected_symbol = st.selectbox("📊 Select Symbol", ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META', 'TSLA', 'NVDA', 'BA', 'DIS', 'NFLX'])
    
    def fetch_data(ticker):
        try:
            bars = api.get_bars(ticker, tradeapi.TimeFrame.Minute, limit=30).df
            bars.index = pd.to_datetime(bars.index)
            return bars[['open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            st.error(f"Data Fetch Error for {ticker}: {e}")
            return None
    
    def create_candlestick_chart(data, symbol):
        fig = go.Figure(data=[go.Candlestick(x=data.index,
                    open=data['open'], high=data['high'], low=data['low'], close=data['close'])])
        fig.update_layout(title=f'{symbol} Price Chart', yaxis_title='Price', template='plotly_dark', height=500)
        return fig
    
    data = fetch_data(selected_symbol)
    if data is not None:
        st.plotly_chart(create_candlestick_chart(data, selected_symbol), use_container_width=True)

# Live Trading Page
elif page == "Live Trading":
    st.title("🚀 Live Trading Panel")
    trading_enabled = st.toggle("Enable Trading", value=True)
    risk_percentage = st.slider("Risk Per Trade (%)", 0.1, 5.0, 2.0)
    
    def moving_average_crossover(symbol):
        bars = api.get_bars(symbol, tradeapi.TimeFrame.Minute, limit=50).df
        bars['SMA_10'] = bars['close'].rolling(window=10).mean()
        bars['SMA_30'] = bars['close'].rolling(window=30).mean()
        
        if bars['SMA_10'].iloc[-1] > bars['SMA_30'].iloc[-1]:
            api.submit_order(symbol=symbol, qty=1, side='buy', type='market', time_in_force='gtc')
            st.success(f"Bought {symbol}")
        elif bars['SMA_10'].iloc[-1] < bars['SMA_30'].iloc[-1]:
            api.submit_order(symbol=symbol, qty=1, side='sell', type='market', time_in_force='gtc')
            st.warning(f"Sold {symbol}")
    
    if trading_enabled and st.button("Start Trading"):
        st.success("Trading started!")
        moving_average_crossover(selected_symbol)

# Portfolio Page
elif page == "Portfolio":
    st.title("💰 Portfolio Overview")
    def get_portfolio():
        account = api.get_account()
        positions = api.list_positions()
        portfolio = {
            "cash": float(account.cash),
            "equity": float(account.equity),
            "profit_loss": float(account.equity) - float(account.last_equity),
            "positions": []
        }
        for position in positions:
            portfolio["positions"].append({
                "symbol": position.symbol,
                "qty": int(position.qty),
                "avg_entry_price": float(position.avg_entry_price),
                "current_price": float(position.current_price),
                "unrealized_pl": float(position.unrealized_pl)
            })
        return portfolio
    
    portfolio = get_portfolio()
    st.write(f"**Buying Power:** ${portfolio['cash']:.2f}")
    st.write(f"**Portfolio Value:** ${portfolio['equity']:.2f}")
    if portfolio["positions"]:
        st.table(portfolio["positions"])
    else:
        st.write("No open positions.")

# Settings Page
elif page == "Settings":
    st.title("⚙️ Settings & Configuration")
    st.write("Manage API keys, strategy parameters, and app preferences here.")
