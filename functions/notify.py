import json
import boto3
import os
from contextlib import closing
from tempfile import gettempdir
import datetime as dt
from dateutil.tz import gettz
from boto3.dynamodb.conditions import Key, Attr

import botocore
dynamodb = boto3.resource('dynamodb')

def get_assume_role_credentials(role_arn):
    sts_client = boto3.client('sts')
    try:
        assume_role_response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName="AuditSESLambdaExecution")
        return assume_role_response['Credentials']
    except botocore.exceptions.ClientError as ex:
        # Scrub error message for any internal account info leaks
        print(str(ex))
        if 'AccessDenied' in ex.response['Error']['Code']:
            ex.response['Error']['Message'] = "AWS Lambda does not have permission to assume the IAM role."
        else:
            ex.response['Error']['Message'] = "InternalError"
            ex.response['Error']['Code'] = "InternalError"
        raise ex

def get_client(service, role_arn, assume_role):
    """Return the service boto client. It should be used instead of directly calling the client.

    Keyword arguments:
    service -- the service name used for calling the boto.client()
    event -- the event variable given in the lambda handler
    """
    if not assume_role:
        return boto3.client(service)
    credentials = get_assume_role_credentials(role_arn)
    return boto3.client(service, aws_access_key_id=credentials['AccessKeyId'],
                        aws_secret_access_key=credentials['SecretAccessKey'],
                        aws_session_token=credentials['SessionToken']
                       )

def get_all_tags(client, account_id):
    list_to_return = []
    list = client.list_tags_for_resource(ResourceId=account_id)
    while True:
        for tags in list['Tags']:
            list_to_return.append(tags)
        if 'Marker' in list:
            next_marker = list['Marker']
            list = client.list_tags_for_resource(ResourceId=account_id, fMarker=next_marker)
        else:
            break
    return list_to_return

def get_tags(account_id):
    organization_client = get_client('organizations', os.environ['MASTER_ROLE_ARN'],True)
    account_tags = get_all_tags(organization_client, account_id)
    result = {} 
    for tag in account_tags:
        result[tag['Key']]=result[tag['Value']]
    return result

def send_email(rule_config,account_tags,details):
   

    if ( rule_config['notification_enabled' ] == False):
        return
    mail_config = rule_config

    lst = ['primary_owner', 'group_owner', 'escalate_contact1', 'escalate_contact2'] 

    for config in lst: 
        if config in account_tags:
            mail_config[config] = account_tags[config]

    for config in lst: 
        if rule_config[config] is not None:
            primary_owner = rule_config[config]


    ses_client = get_client('ses', None,False)
    template_data = '"GREETINGS":"{}", "AWS_ACCONT":"{}","MESSAGE_BODY":"{}","URL":"{}"'.format(
        "Hola",
        details['awsAccountId'],
        details['configRuleName'],
        "entel.cl"
    )
    response = ses_client.send_templated_email(
        Source=os.environ['EMAIL_SENDER'],
        Destination={
            'ToAddresses': [
            mail_config['primary_owner'],
            ],
            'CcAddresses': [
            mail_config['primary_owner'],
            ]
    },
    ReplyToAddresses=[
        os.environ['EMAIL_SENDER'],
    ],
    Template=os.environ['TEMPLATE_NAME'],
    TemplateData='{'+template_data+'}'
    )

def get_config(rule):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    dresponse = table.query(
       KeyConditionExpression=Key('id').eq('default_config')
    )
    config = {'notification_enabled': False, 
                'escalation_enabled': False, 
                'escalate_after': 24, 
                'override_notification': True, 
                'escalate_contact1': None, 
                'escalate_contact2': None,
                'primary_owner': None,
                'group_owner': None}
    if (len(dresponse['Items']) == 1):
        for k in dresponse['Items'][0]:
            config[k]=dresponse['Items'][0][k]
    #get key id for current rule
    rule_response = table.scan()
    config_keys = []
    for rule_id in rule_response['Items']:
        if rule.startswith( rule_id['id'] ):
            for k in rule_id:
                config[k]=rule_id[k]
            break
    return config
    

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
        rule_config = get_config(details['configRuleName'])
        account_tags = get_tags(details['awsAccountId'])
        send_email(rule_config,account_tags,details)
    return 
