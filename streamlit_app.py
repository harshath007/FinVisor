import time
from datetime import datetime
import pytz
import alpaca_trade_api as tradeapi
import backtrader as bt
import pandas as pd
import streamlit as st

# Alpaca API Credentials
API_KEY = 'your_api_key_here'
API_SECRET = 'your_api_secret_here'
BASE_URL = 'https://paper-api.alpaca.markets'  # Use live API URL in production

# Connect to Alpaca API
api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')

# Define Market Hours (Eastern Standard Time)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16  # 4:00 PM EST

# Timezone for Market Hours
eastern = pytz.timezone('US/Eastern')

# ✅ Streamlit Setup
st.set_page_config(page_title="📊 Live Trading Bot", layout="wide")
st.title("📈 Real-Time Trading Dashboard")


def is_market_open():
    """Check if the market is open (9:30 AM - 4:00 PM EST)."""
    clock = api.get_clock()
    return clock.is_open


# ✅ **Trading Strategy for Monthly Profit Optimization**
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

                st.write(f"✅ **BUY**: {max_shares} shares at ${price:.2f} on {self.data.datetime.date(0)}")
                self.highest_price = price
                self.entry_price = price
                self.stop_loss = price * self.params.stop_loss_factor

        else:
            self.highest_price = max(self.highest_price, self.data.close[0])
            trailing_stop = self.highest_price * (1 - self.params.trailing_stop_factor)

            if self.data.close[0] < trailing_stop or self.data.close[0] < self.stop_loss:
                profit_loss = (self.data.close[0] - self.entry_price) * self.position.size
                self.close()
                st.write(f"⛔ **STOP LOSS TRIGGERED** at ${self.data.close[0]:.2f} on {self.data.datetime.date(0)}")
                st.write(f"📉 **Trade Profit/Loss**: ${profit_loss:.2f}")


def fetch_data(ticker):
    """Fetch live stock data from Alpaca's API."""
    try:
        bars = api.get_bars(ticker, tradeapi.TimeFrame.Minute, limit=30).df
        bars.index = pd.to_datetime(bars.index)
        bars = bars[['open', 'high', 'low', 'close', 'volume']]
        return bars
    except Exception as e:
        st.error(f"⚠️ Data Fetch Error for {ticker}: {e}")
        return None


def get_portfolio():
    """Retrieve current portfolio details."""
    account = api.get_account()
    positions = api.list_positions()

    portfolio = {
        "cash": float(account.cash),
        "equity": float(account.equity),
        "profit_loss": float(account.equity) - float(account.last_equity),
        "positions": [],
    }

    for position in positions:
        portfolio["positions"].append(
            {
                "symbol": position.symbol,
                "qty": int(position.qty),
                "avg_entry_price": float(position.avg_entry_price),
                "current_price": float(position.current_price),
                "unrealized_pl": float(position.unrealized_pl),
            }
        )

    return portfolio


def run_live_trading(stock_list):
    """
    ✅ **Main function to run live trading**
    - Checks if the market is open
    - Fetches data from Alpaca API
    - Runs strategy on each stock every 15 minutes
    """
    cerebro = bt.Cerebro()
    cerebro.addstrategy(MonthlyProfitOptimizationStrategy)

    while True:
        if is_market_open():
            st.write(f"📊 **Market Open**: {datetime.now(eastern)}")

            for stock in stock_list:
                st.write(f"🔄 Fetching data for **{stock}**...")
                stock_data = fetch_data(stock)

                if stock_data is not None:
                    data_feed = bt.feeds.PandasData(dataname=stock_data)
                    cerebro.adddata(data_feed)

                    st.write(f"🚀 Running strategy for **{stock}**...")
                    cerebro.run()

            # ✅ Update Portfolio Info on Streamlit
            portfolio = get_portfolio()
            st.subheader("💰 Portfolio Summary")
            st.write(f"💵 **Cash:** ${portfolio['cash']:.2f}")
            st.write(f"📊 **Equity:** ${portfolio['equity']:.2f}")
            st.write(f"📉 **Profit/Loss:** ${portfolio['profit_loss']:.2f}")

            # ✅ Display Positions
            st.subheader("📈 Open Positions")
            if portfolio["positions"]:
                position_df = pd.DataFrame(portfolio["positions"])
                st.dataframe(position_df)
            else:
                st.write("No open positions.")

            st.write("⏳ **Waiting for next 15-minute interval...**")
            time.sleep(15 * 60)  # Sleep for 15 minutes
        else:
            st.write(f"❌ **Market Closed**: {datetime.now(eastern)}")
            st.write("🕰️ Waiting for market to open...")
            time.sleep(60 * 60)  # Sleep for one hour


if __name__ == "__main__":
    st.sidebar.header("🚀 Start Live Trading")

    # ✅ **Define the top 10 stocks to trade**
    stock_list = ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META', 'TSLA', 'NVDA', 'BA', 'DIS', 'NFLX']

    # ✅ **Start live trading button**
    if st.sidebar.button("Start Trading"):
        st.sidebar.success("✅ Trading started!")
        run_live_trading(stock_list)
