import os
import boto3
from binance.client import Client
from binance.exceptions import BinanceAPIException
from decimal import Decimal
import time

# Load your Binance API keys from Lambda's environment variables
BINANCE_API_KEY = os.environ.get('BINANCE_API_KEY')
BINANCE_API_SECRET = os.environ.get('BINANCE_API_SECRET')

# Initialize the Binance client
client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

# Initialize the DynamoDB client and table
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('TradingState')

# Gain and Loss thresholds (as percentages)
GAIN_THRESHOLD = 0.02  # e.g., 2% profit
LOSS_THRESHOLD = 0.01  # e.g., 1% loss

SHORT_WINDOW = 5  # e.g., 5-minute MA
LONG_WINDOW = 20  # e.g., 20-minute MA

def save_state_to_dynamodb(symbol, trade_data):
    """Saves trade data to DynamoDB."""
    trade_data['symbol'] = symbol
    trade_data['timestamp'] = int(time.time() * 1000)  # current time in milliseconds
    table.put_item(Item=trade_data)

def get_last_trade_from_dynamodb(symbol):
    """Retrieve the latest trade data from DynamoDB for a particular symbol."""
    response = table.query(
        KeyConditionExpression='symbol = :symbol_val',
        ExpressionAttributeValues={':symbol_val': symbol},
        Limit=1,
        ScanIndexForward=False  # to get the latest (descending order by timestamp)
    )
    if 'Items' in response and response['Items']:
        return response['Items'][0]
    return None

def execute_trade(symbol="BTCUSDT"):
    try:
        klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, "30 minutes ago UTC")
        if not klines:
            return

        close_values = [float(k[4]) for k in klines]

        short_ma = sum(close_values[-SHORT_WINDOW:]) / SHORT_WINDOW
        long_ma = sum(close_values[-LONG_WINDOW:]) / LONG_WINDOW

        current_price = float(client.get_symbol_ticker(symbol=symbol)["price"])
        last_trade = get_last_trade_from_dynamodb(symbol)

        position = None
        last_trade_price = 0
        if last_trade:
            position = last_trade.get('position')
            last_trade_price = float(last_trade.get('price', 0))
            accumulated_gain = Decimal(last_trade.get('accumulated_gain', '0'))
        else:
            accumulated_gain = Decimal('0')

        trade_action = "HOLD"
        percentage_change = (current_price - last_trade_price) / last_trade_price if last_trade_price != 0 else 0

        # Gain/Loss control checks
        if position == "LONG":
            if percentage_change >= GAIN_THRESHOLD:
                trade_action = "SELL"
                position = "SHORT"
                accumulated_gain += Decimal(str(percentage_change))
            elif percentage_change <= -LOSS_THRESHOLD:
                trade_action = "SELL"
                position = "SHORT"
                accumulated_gain += Decimal(str(percentage_change))
        elif position == "SHORT":
            if percentage_change <= -GAIN_THRESHOLD:
                trade_action = "BUY"
                position = "LONG"
                accumulated_gain -= Decimal(str(percentage_change))
            elif percentage_change >= LOSS_THRESHOLD:
                trade_action = "BUY"
                position = "LONG"
                accumulated_gain -= Decimal(str(percentage_change))

        if trade_action == "SELL":
            accumulated_gain = Decimal('0')

        # Dual MA crossover checks (only if no action determined by gain/loss control)
        if trade_action == "HOLD":
            if short_ma > long_ma and position != "LONG":
                trade_action = "BUY"
                position = "LONG"
            elif short_ma < long_ma and position != "SHORT":
                trade_action = "SELL"
                position = "SHORT"

        trade_data = {
            "price": Decimal(str(current_price)),
            "action": trade_action,
            "position": position,
            "accumulated_gain": accumulated_gain
        }

        print(f"Current Price: {current_price}")
        print(f"Short MA: {short_ma}")
        print(f"Long MA: {long_ma}")
        print(f"Action: {trade_action}")

        save_state_to_dynamodb(symbol, trade_data)
        return trade_data

    except BinanceAPIException as e:
        print(f"BinanceAPIException: {e}")
        return None

def lambda_handler(event, context):
    result = execute_trade()
    if result:
        return {
            'statusCode': 200,
            'body': f"Trade executed with action {result['action']} for {str(result['price'])} with accumulated gain {str(result['accumulated_gain'])}."
        }
    else:
        return {
            'statusCode': 200,
            'body': 'No trade executed.'
        }
