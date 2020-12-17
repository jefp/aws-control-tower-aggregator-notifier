import json
import boto3
import os
import uuid
import datetime as dt
from dateutil.tz import gettz


dynamodb = boto3.resource('dynamodb')

def handler(event, context):
    response = {}
    sns_client = boto3.client('sns')

    try:
       table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
       # write the todo to the database
       # create a response
       sns_payload = json.dumps({
             "event": event['body']['event'],
             "description": event['body']['description'],
             "target": event['body']['target'],
             "status": event['body']['status'],
             "date": event['body']['date']
       })


       sns_id = sns_client.publish(Message = sns_payload , TargetArn = os.environ['SNS_ARN'])
       item = {
           'MessageId': sns_id['MessageId'],
           'Target': event['body']['target'],
           'AlarmCreatedAt': str(dt.datetime.now(gettz(os.environ['TZ']))),
           'VoiceAlarmCreatedAt': "null"
       }

       table.put_item(Item=item)
       response = {
           "statusCode": 200,
           "body": json.dumps(item)
       }
    except Exception as e:
      response = {
           "statusCode": 403,
           "error": str(e)
           }
    return response
