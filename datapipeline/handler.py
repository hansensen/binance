import boto3
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
    s3 = boto3.client('s3', region_name='ap-southeast-1')
    
    table = dynamodb.Table('TradingState')
    
    # Scanning the entire table (adjust based on your table's size)
    response = table.scan()
    items = response['Items']
    
    # Convert data to JSON
    data_str = json.dumps(items, cls=DecimalEncoder)
    
    # Upload data to S3
    s3.put_object(Body=data_str, Bucket='tradingdatabucket', Key='my-data.json')
