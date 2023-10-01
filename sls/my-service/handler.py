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

def save_state_to_dynamodb(trade_id, trade_data):
    """Saves trade data to DynamoDB."""
    table.put_item(Item={'id': trade_id, 'trade_data': trade_data})

def get_state_from_dynamodb(trade_id):
    """Retrieve trade data from DynamoDB based on trade ID."""
    response = table.get_item(Key={'id': trade_id})
    if 'Item' in response:
        return response['Item']
    return None

def execute_trade():
    try:
        # Fetch data from Binance
        klines = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
        if not klines:
            return

        close_values = [float(k[4]) for k in klines]
        average_close = sum(close_values) / len(close_values)

        current_price = float(client.get_symbol_ticker(symbol="BTCUSDT")["price"])

        trade_data = {}

        # Logic for a very simple moving average trading strategy
        if current_price > average_close:
            # Buy logic
            trade_data = {
                "action": "BUY",
                "price": Decimal(str(current_price))
            }
        elif current_price < average_close:
            # Sell logic
            trade_data = {
                "action": "SELL",
                "price": Decimal(str(current_price))
            }

        # Save trade data to DynamoDB
        if trade_data:
            trade_id = str(int(time.time()))  # Using the current timestamp as a unique trade_id
            save_state_to_dynamodb(trade_id, trade_data)

        return trade_data
    except BinanceAPIException as e:
        print(f"BinanceAPIException: {e}")
        return None

def lambda_handler(event, context):
    result = execute_trade()
    if result:
        return {
            'statusCode': 200,
            'body': f"Trade executed successfully with action {result['action']} at price {str(result['price'])}!"
        }
    else:
        return {
            'statusCode': 200,
            'body': 'No trade executed.'
        }
