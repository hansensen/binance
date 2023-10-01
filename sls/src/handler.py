import json
import sys

def hello(event, context):
    body = {
        "message": "Python Function executed successfully!"
    }
    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }
    return response
