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
GAIN_THRESHOLD = 0.02  # e.g., 2%
LOSS_THRESHOLD = 0.01  # e.g., 1%

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
        klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
        if not klines:
            return

        close_values = [float(k[4]) for k in klines]
        average_close = sum(close_values) / len(close_values)

        current_price = float(client.get_symbol_ticker(symbol=symbol)["price"])

        last_trade = get_last_trade_from_dynamodb(symbol)

        trade_action = "HOLD"
        accumulated_gain = Decimal('0')
        last_trade_price = 0

        if last_trade:
            last_trade_price = float(last_trade.get('price', 0))
            accumulated_gain = Decimal(last_trade.get('accumulated_gain', '0'))
            percentage_change = (current_price - last_trade_price) / last_trade_price

            if percentage_change >= GAIN_THRESHOLD and current_price > average_close:
                trade_action = "SELL"
                accumulated_gain += Decimal(str(percentage_change))
            elif percentage_change <= -LOSS_THRESHOLD and current_price < average_close:
                trade_action = "BUY"
                accumulated_gain += Decimal(str(percentage_change))
        else:
            trade_action = "BUY_STARTING_AMOUNT"

        trade_data = {
            "price": Decimal(str(current_price)),
            "action": trade_action,
            "accumulated_gain": accumulated_gain
        }

        # Log the details
        print(f"Current Price: {current_price}")
        print(f"Last Trade Price: {last_trade_price}")
        print(f"Average Close (24h): {average_close}")
        print(f"Action: {trade_action}")
        print(f"Accumulated Gain: {accumulated_gain}")

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
