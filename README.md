# AWS ControlTower Config Aggregator notifier
The AWS ControlTower Configuration Aggregator Notifier is a solution that allows AWS account administrators that are implemented with [AWS Control Tower](https://aws.amazon.com/controltower/) and relies on the [Customizations for AWS Control Tower Solution] (https://aws.amazon.com/solutions/implementations/customizations-for-aws-control-tower/) to implement an automatednotifications to the AWS Account responsibles about compliance change in your AWS resources.


## Instructions

1. Clone the github repo and change the directory: 
```bash
git clone https://github.com/jefp/aws-control-tower-config-aggregator-notifier.git
cd aws-control-tower-config-aggregator-notifier
```
2. Run ```src/package.sh``` to package the code and dependencies

3. Gather other information for deployment parameters:
    In AWS Organizations, look on the Settings page for the Organization ID. It will be o-xxxxxxxxxx
    In AWS Organizations, look on the Accounts page for the Master Account ID and the Audit Account ID

##   **In the Master Account** 

1. Launch the CloudFormation Stack in the region where you have deployed the [Customizations for AWS Control Tower Solution](https://aws.amazon.com/solutions/implementations/customizations-for-aws-control-tower/) using the template cf-master.yml

*You can name the CF as: ControlTowerCustomizationsConfigNotificationMaster*

Copy the values of the CloudFormation Output:

* MASTER_BUCKET
* MASTER_ROLE

2. Upload the lambda files to the MASTER_BUCKET created in the previous step:
```bash
aws s3 cp src/account_tags.zip s3://$MASTER_BUCKET/
aws s3 cp src/notify_config.zip s3://$MASTER_BUCKET/
aws s3 cp src/notify_guardduty.zip s3://$MASTER_BUCKET/
```
3. Update the manifest.yaml file of the custom-control-tower-configuration include the config rule to audit the Account Tagging:

Example:

```yaml
  - name: ConfigRuleAccountTags
    template_file: templates/account-tags-config-rule.template
    parameter_file: parameters/account-tags-config-rule.json
    deploy_method: stack_set
    deploy_to_ou: # :type: list
      - Custom
    regions:
      - us-east-1
```

4. Copy the file: **ct-customizations/account-tags-config-rule.template** into the **custom-control-tower-configuration/template/** folder 
5. Copy the file: **ct-customizations/account-tags-config-rule.json** into the **custom-control-tower-configuration/parameters/** folder 

Update the parameters **SourceBucket**, **RequiredTags** and **AdminRoleToAssume** in custom-control-tower-configuration/parameters/account-tags-config-rule.json
using the **MASTER_BUCKET** and **MASTER_ROLE** 

The **RequiredTags** parameter contains the list of the mandatory tags for the AWS Accounts. 

##   **In the Audit Account** 

1. Create SES template in audit account
```bash
 aws ses create-template --cli-input-json file://template_config.json
 aws ses create-template --cli-input-json file://template_gd.json
```

2. Launch the CloudFormation Stack in the region where you want to have the centralized config notification using the template cf-audit.yml

*You can name the CF as: ControlTowerCustomizationsConfigNotificationAudit*

Copy the values of the CloudFormation Output:

* NOTIFY_LAMBDA_ARN
* CONFIG_TABLE

3. Subscribe the NOTIFY_LAMBDA function CustomControlTower-Config-Notification-function to topic **aws-controltower-AggregateSecurityNotifications**
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:REGION:AUDIT_ACCOUNT_ID:aws-controltower-AggregateSecurityNotifications \
  --protocol lambda \
  --notification-endpoint NOTIFY_LAMBDA_ARN
  
# Add Lambda to SNS as subscription
aws sns subscribe \
    --topic-arn arn:aws:sns:REGION:AUDIT_ACCOUNT_ID:aws-controltower-AggregateSecurityNotifications \
    --protocol lambda \
    --notification-endpoint NOTIFY_LAMBDA_ARN

# Give permissions to Lambda to access that subscription i.e. Add it through triggers
aws lambda add-permission \
    --function-name HourlyLambdaFunction \
    --statement-id AUDIT_ACCOUNT_ID\
    --action "lambda:InvokeFunction" \
    --principal sns.amazonaws.com \
    --source-arn NOTIFY_LAMBDA_ARN
    
```
4. Update the configurations table in the **CONFIG_TABLE**



## License

This project is licensed under the Apache-2.0 License.

