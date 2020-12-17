import json
import boto3
import os
from contextlib import closing
from tempfile import gettempdir
import datetime as dt
from dateutil.tz import gettz

dynamodb = boto3.resource('dynamodb')

def greetings(hour):
    if (hour > 5  and  hour < 12):
        return "Buenos dias, "
    elif (hour > 12  and hour < 19):
        return "Buenas tardes, "
    else:
        return "Buenas noches, "


def ssml(message,hour):
    return "<speak>"+greetings(hour)+message+"</speak>"


def handler(event, context):

  for i in range(len(event['Records'])):
      message = event['Records'][i]['Sns']['Message']
      messageID = event['Records'][i]['Sns']['MessageId']
      polly = boto3.client('polly')
      s3 = boto3.client('s3')
      messageJ = json.loads(message)
      hour = dt.datetime.now(gettz(os.environ['TZ'])).hour
      response = polly.synthesize_speech(
        OutputFormat='mp3',
        Text = ssml(messageJ['event'],hour),
        VoiceId = 'Penelope',
        TextType='ssml'
      )


      if "AudioStream" in response:
          with closing(response["AudioStream"]) as stream:
              output = os.path.join(gettempdir(), messageID )
              try:
                  with open(output, "wb") as file:
                      file.write(stream.read())
              except IOError as error:
                  print(error)
                  sys.exit(-1)
      table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
      table.update_item(
            Key={'MessageId': messageID, 'Target': messageJ['target']},
            UpdateExpression="set VoiceAlarmCreatedAt = :val",
            ExpressionAttributeValues={
                ':val': str(dt.datetime.now(gettz(os.environ['TZ'])))
            }
        )

      s3.upload_file('/tmp/' + messageID, os.environ['S3_BUCKET'], messageID + ".mp3")

  return
