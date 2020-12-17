import json
import boto3
import os
from contextlib import closing
from tempfile import gettempdir
import datetime as dt
from dateutil.tz import gettz

dynamodb = boto3.resource('dynamodb')

'''
{
    "version": "0",
    "id": "51677f1d-1ae8-5357-cc9b-387ac98e26ab",
    "detail-type": "Config Rules Compliance Change",
    "source": "aws.config",
    "account": "616241992003",
    "time": "2020-12-17T05:13:50Z",
    "region": "eu-west-2",
    "resources": [],
    "detail": {
        "resourceId": "AROAY66XCSFB4WL7AHL3V",
        "awsRegion": "eu-west-2",
        "awsAccountId": "616241992003",
        "configRuleName": "securityhub-iam-inline-policy-blocked-kms-actions-baa2cf8c",
        "recordVersion": "1.0",
        "configRuleARN": "arn:aws:config:eu-west-2:616241992003:config-rule/aws-service-rule/securityhub.amazonaws.com/config-rule-lcprsx",
        "messageType": "ComplianceChangeNotification",
        "newEvaluationResult": {
            "evaluationResultIdentifier": {
                "evaluationResultQualifier": {
                    "configRuleName": "securityhub-iam-inline-policy-blocked-kms-actions-baa2cf8c",
                    "resourceType": "AWS::IAM::Role",
                    "resourceId": "AROAY66XCSFB4WL7AHL3V"
                },
                "orderingTimestamp": "2020-12-16T18:46:38.764Z"
            },
            "complianceType": "COMPLIANT",
            "resultRecordedTime": "2020-12-17T05:13:49.210Z",
            "configRuleInvokedTime": "2020-12-17T05:13:48.933Z"
        },
        "notificationCreationTime": "2020-12-17T05:13:50.188Z",
        "resourceType": "AWS::IAM::Role"
    }
}
'''

def handler(event, context):
    for i in range(len(event['Records'])):
        message = event['Records'][i]['Sns']['Message']
        messageID = event['Records'][i]['Sns']['MessageId']
        messageJ = json.loads(message)
        details = messageJ['detail']
        print(details['configRuleName'])
        print(details['awsAccountId'])
        print(details['awsRegion'])
        print(details['resourceType'])
        print(details['resourceId'])
        print(details['newEvaluationResult']['complianceType'])
        print(details['newEvaluationResult']['configRuleInvokedTime'])
        print(details['newEvaluationResult']['resultRecordedTime'])
        print(details['notificationCreationTime'])
    
  return
