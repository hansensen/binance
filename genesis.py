import logging
import time
from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import BINANCE_API_KEY, BINANCE_API_SECRET

# Set up logging configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# Binance client initialization
client = Client(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)

# Additional global variables to manage the trading position and prices
position_price = None
stop_loss = None
take_profit = None
current_profit = 0

def get_current_price():
    try:
        ticker = client.get_symbol_ticker(symbol="BTCUSDT")
        return float(ticker["price"])
    except BinanceAPIException as e:
        logging.error("Error fetching current price: %s", e)
        return None

def moving_average():
    try:
        # Adjusted to get the last 20 minutes of data for the moving average calculation
        klines = client.get_klines(symbol="BTCUSDT", interval=Client.KLINE_INTERVAL_1MINUTE)
        prices = [float(k[4]) for k in klines[-20:]]
        return sum(prices) / len(prices)
    except BinanceAPIException as e:
        logging.error("Error fetching historical data: %s", e)
        return None

def buy(current_price):
    global position_price, stop_loss, take_profit

    logging.info("Executing buy logic...")
    position_price = current_price

    # Set stop loss and take profit percentages (e.g., 2% for stop loss, 5% for take profit)
    stop_loss = position_price * 0.98
    take_profit = position_price * 1.05

def sell():
    global position_price, stop_loss, take_profit

    logging.info("Executing sell logic...")
    position_price = None
    stop_loss = None
    take_profit = None

def main():
    global position_price
    global current_profit

    position = False
    while True:
        current_price = get_current_price()
        ma = moving_average()

        if current_price is None or ma is None:
            logging.warning("Failed to fetch price or MA, retrying in next iteration")
            time.sleep(60)  # Sleep for 1 minute
            continue

        logging.info("Current price is %s, Moving Average is %s", current_price, ma)

        # Check stop-loss and take-profit levels
        if position and (current_price <= stop_loss or current_price >= take_profit):
            sell()
            position = False
            current_profit += current_price
            logging.info("Sold due to hitting stop-loss/take-profit at %s, current profit is %s", current_price, current_profit)
            continue

        # Original strategy
        if not position and current_price > ma:
            buy(current_price)
            position = True
            current_profit -= current_price
            logging.info("Bought at %s, current profit is %s", current_price, current_profit)
        elif position and current_price < ma:
            sell()
            position = False
            current_profit += current_price
            logging.info("Sold at %s, current profit is %s", current_price, current_profit)

        time.sleep(60)  # Sleep for 1 minute

if __name__ == "__main__":
    main()
