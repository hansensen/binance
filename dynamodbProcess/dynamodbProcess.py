import json
import os
import pymysql
from datetime import datetime, timezone


# Get database info from environment variables
db_host = os.environ['DB_HOST']
db_user = os.environ['DB_USER']
db_password = os.environ['DB_PASSWORD']
db_name = os.environ['DB_NAME']
db_table_name = os.environ['DB_TABLE_NAME']

def lambda_handler(event, context):

    # Log the received event
    print("Received event: " + json.dumps(event, indent=2))

    connection = pymysql.connect(host=db_host, user=db_user, password=db_password, db=db_name)

    try:
        for record in event['Records']:
            # Check if the event is an INSERT operation
            if record['eventName'] == 'INSERT':
                new_image = record['dynamodb']['NewImage']

                # Extract data
                symbol = new_image['symbol']['S']
                price = float(new_image['price']['N'])
                action = new_image['action']['S']
                accumulated_gain = float(new_image['accumulated_gain']['N'])
                position = new_image['position']['S']
                timestamp = int(new_image['timestamp']['N'])  # Assuming timestamp is in milliseconds

                if position != 'NEUTRAL':
                    continue

                timestamp_human_readable = datetime.fromtimestamp(timestamp / 1000.0, tz=timezone.utc)

                print(timestamp_human_readable.strftime('%Y-%m-%d %H:%M:%S'))  # Format as a string if needed

                print(f"Symbol: {symbol}, Price: {price}, Action: {action}, "
                      f"Accumulated Gain: {accumulated_gain}, Position: {position}, Timestamp: {timestamp}")

                # Prepare SQL query
                with connection.cursor() as cursor:
                    sql = f"INSERT INTO {db_table_name} (timestamp, symbol, price, action, accumulated_gain, position) VALUES (%s, %s, %s, %s, %s, %s)"
                    cursor.execute(sql, (timestamp, symbol, price, action, accumulated_gain, position))
                
                # Commit the changes
                connection.commit()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the connection
        connection.close()

    return {
        'statusCode': 200,
        'body': json.dumps('Successfully inserted data into RDS MySQL database and successfully processed DynamoDB stream records.')
    }
