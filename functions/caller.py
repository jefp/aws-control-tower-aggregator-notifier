import json
import boto3
import os
import datetime as dt
import logging
from dateutil.tz import gettz

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

def handler(event, context):
    try:
       bucket_name = event['Records'][0]['s3']['bucket']['name']
       file_key = event['Records'][0]['s3']['object']['key']
       messageID = file_key.replace(".mp3","")
       logger.info('Reading {} from {}'.format(file_key, bucket_name))
       obj = s3.get_object(Bucket=bucket_name, Key=file_key)

       table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
       table.update_item(
             Key={'MessageId': messageID},
             UpdateExpression="set CalledAt = :val",
             ExpressionAttributeValues={
                 ':val': str(dt.datetime.now(gettz(os.environ['TZ'])))
             }
         )
    except Exception as e:
      logger.error('Error {} from {}'.format(403, str(e)))
      response = {
           "statusCode": 403,
           "error": str(e)
           }
    return response
