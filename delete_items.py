import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('TradingState')

# Scan the table
response = table.scan()

with table.batch_writer() as batch:
    for item in response['Items']:
        table.delete_item(
            Key={
                'symbol': item['symbol'],
                'timestamp': item['timestamp']
            }
        )

