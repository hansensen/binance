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

# Gain and Loss thresholds
GAIN_THRESHOLD = 0.02  # Adjust as necessary
LOSS_THRESHOLD = 0.01  # Adjust as necessary

def save_state_to_dynamodb(trade_data):
    """Saves trade data to DynamoDB."""
    table.put_item(Item=trade_data)

def get_state_from_dynamodb():
    """Retrieve the latest trade data from DynamoDB."""
    response = table.scan(Limit=1)
    if 'Items' in response and response['Items']:
        return response['Items'][0]
    return None

def execute_trade():
    try:
        klines = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
        if not klines:
            return

        close_values = [float(k[4]) for k in klines]
        average_close = sum(close_values) / len(close_values)
        current_price = float(client.get_symbol_ticker(symbol="BTCUSDT")["price"])

        last_trade = get_state_from_dynamodb()

        if not last_trade or 'price' not in last_trade:
            last_trade_price = current_price
            accumulated_gain = 0.0
        else:
            last_trade_price = float(last_trade['price'])
            accumulated_gain = float(last_trade.get('accumulated_gain', 0))

        potential_gain = current_price - last_trade_price
        trade_data = {
            "id": str(int(time.time())),
            "action": "HOLD",
            "price": Decimal(str(current_price)),
            "accumulated_gain": Decimal(str(accumulated_gain))
        }

        if potential_gain >= GAIN_THRESHOLD and current_price > average_close:
            trade_data["action"] = "SELL"
            trade_data["accumulated_gain"] = Decimal(str(accumulated_gain + potential_gain))
        elif potential_gain >= LOSS_THRESHOLD and current_price < average_close:
            trade_data["action"] = "BUY"
            trade_data["accumulated_gain"] = Decimal(str(accumulated_gain - potential_gain))

        save_state_to_dynamodb(trade_data)

        return trade_data
    except BinanceAPIException as e:
        print(f"BinanceAPIException: {e}")
        return None

def lambda_handler(event, context):
    result = execute_trade()
    if result:
        return {
            'statusCode': 200,
            'body': f"Trade executed with action {result['action']} at price {str(result['price'])} with accumulated gain {str(result['accumulated_gain'])}."
        }
    else:
        return {
            'statusCode': 200,
            'body': 'No trade executed.'
        }
