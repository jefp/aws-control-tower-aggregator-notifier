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
        if rule_config[config] is not None or rule_config[config] != "None" :
            mail_config[config] = rule_config[config]

    title = "Evaluación de política de compliance sobre recurso de AWS"
    preheader = "{} - {}".format(details['resourceId'],details['newEvaluationResult']['complianceType'])

    bg_color = "#990000"
    if ('newEvaluationResult' in details and \
        'complianceType' in details['newEvaluationResult'] and \
        details['newEvaluationResult']['complianceType'] == "COMPLIANT"):
        bg_color = "#007f00"
        
    ses_client = get_client('ses', None,False)
    template_data = '"awsAccountId":"{}",\
                    "awsRegion":"{}",\
                    "resourceType":"{}",\
                    "resourceId":"{}",\
                    "configRuleName":"{}",\
                    "complianceType":"{}",\
                    "configRuleInvokedTime":"{}",\
                    "resultRecordedTime":"{}",\
                    "notificationCreationTime":"{}",\
                    "MORE_INFO": "{}",\
                    "COMPANY": "{}",\
                    "SRC_LOGO": "{}",\
                    "PREHEADER": "{}",\
                    "TITLE": "{}",\
                    "BG_COLOR": "{}"'.format(
                    details['awsAccountId'],
                    details['awsRegion'],
                    details['resourceType'],
                    details['resourceId'],
                    details['configRuleName'],
                    details['newEvaluationResult']['complianceType'],
                    details['newEvaluationResult']['configRuleInvokedTime'],
                    details['newEvaluationResult']['resultRecordedTime'],
                    details['notificationCreationTime'],
                    os.environ['MORE_INFO'],
                    os.environ['COMPANY'],
                    os.environ['SRC_LOGO'],
                    preheader,
                    title,
                    bg_color
                    )


    response = ses_client.send_templated_email(
        Source=os.environ['SES_EMAIL_SENDER'],
        Destination={
            'ToAddresses': [
            mail_config['primary_owner'],
            ],
            'CcAddresses': [
            mail_config['primary_owner'],
            ]
    },
    ReplyToAddresses=[
        os.environ['SES_EMAIL_REPLY_TO'],
    ],
    Template=os.environ['SES_TEMPLATE_NAME'],
    TemplateData='{'+template_data+'}',
    ConfigurationSetName=os.environ['SES_CONFIGURATION_SET']
    )
    return response

def get_config(rule):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    dresponse = table.query(
       KeyConditionExpression=Key('id').eq('default_config')
    )
    config = {  'notification_enabled': False, 
                'escalation_enabled': False, 
                'escalate_after': 24, 
                'escalate_contact1': None, 
                'escalate_contact2': None,
                'primary_owner': None,
                'group_owner': None}
    if (len(dresponse['Items']) == 1):
        for k in dresponse['Items'][0]:
            config[k]=dresponse['Items'][0][k]

    #get key id for current rule
    rule_response = table.scan()
    for rule_id in rule_response['Items']:
        if rule.startswith( rule_id['id'] ):
            for k in rule_id:
                config[k]=rule_id[k]
            break
    return config
    



def lambda_handler(event, context):
    for i in range(len(event['Records'])):
        message = event['Records'][i]['Sns']['Message']
        messageJ = json.loads(message)
        details = messageJ['detail']
        rule_config = get_config(details['configRuleName'])
        account_tags = get_tags(details['awsAccountId'])
        send_email(rule_config,account_tags,details)
    return 
