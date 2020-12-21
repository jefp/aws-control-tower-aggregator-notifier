# aws-controltower-config-aggregator-notifier
**In the Master account**


Create the Cloudformation in the master account using this link: [master-role](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/template?templateURL=https://raw.githubusercontent.com/jefp/aws-controltower-config-aggregator-notifier/main/role-master.yml&stackName=ControlTowerCustomizationsConfigNotificationMaster)

Copy the values of the CF output:

* MASTER_BUCKET
* MASTER_ROLE

If using Customizations for AWS Control Tower:

Deploy the account-tags-config-rule.template into the template folder of the "Customizations for AWS Control Tower" solution 
Deploy theaccount-tags-config-rule.json into the parameters folder of the "Customizations for AWS Control Tower" solution 

Modify the parametrs SourceBucket, RequiredTags and AdminRoleToAssume in the file account-tags-config-rule.json

Deploy in the OUs: 

Example

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


**In the audit account**

Create SES template in audit account

```bash
 aws ses create-template --cli-input-json file://template.json
```

zip the function and upload to s3 bucket.

```bash
cd functions 
zip notify.zip notify.py
aws s3 cp notify.zip s3://$MASTER_BUCKET/
```
Create the Cloudformation in the audit account using this link: [audit-cf](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/template?templateURL=https://raw.githubusercontent.com/jefp/aws-controltower-config-aggregator-notifier/main/audit_cf.yml&stackName=ControlTowerCustomizationsConfigNotificationAudit)

Subscribe the lambda function CustomControlTower-Config-Notification-function to topic 	aws-controltower-AggregateSecurityNotifications
