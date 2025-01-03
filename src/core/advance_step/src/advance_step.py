import json
import boto3
import os
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from acct_decom_utils.event_table import event_table
from acct_decom_utils.plnu_logger import plnu_logger

log_level = os.getenv('log_level', 'INFD')
logger = plnu_logger.PLNULogger(log_level).get_logger()

ssm = boto3.client('ssm')


def update_step(event_to_update: event_table.EventTableRecord, param):
    """
    Advances user to the next step in the deprovisioning process. Calculates `next_step` date and updates
    `previous_step`, `next_step`, and `next_step_date` in DynamoDB

    :param event_to_update: User's record
    :type event_to_update: event_table.EventTableRecord

    :param param: Next step data
    :type param: str
    """
    AWS_REGION = 'us-west-2'
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = dynamodb.Table('EventState')

    param_dict = json.loads(param)
    date = datetime.strptime(event_to_update.next_step_date, event_table.TIMESTAMP_STR_FORMAT)
    new_date = date + timedelta(days=int(param_dict.get("next_step_delay")))
    new_date_str = datetime.strftime(new_date, event_table.TIMESTAMP_STR_FORMAT)
    next_step = param_dict.get("next_step")
    previous_step = event_to_update.next_step

    try:
        table.update_item(
            Key={
                'username': event_to_update.username
            },
            UpdateExpression="set previous_step=:prev,next_step=:nxt,next_step_date=:nd",
            ExpressionAttributeValues={
                ':prev': previous_step,
                ':nxt': next_step,
                ':nd': new_date_str
            }
        )
    except ClientError as err:
        logger.error(f"Couldn't update: {err.response['Error']['Message']}")


def get_step_params():
    """
    Uses the AWS Systems Manager (SSM) client to retrieve and format parameters specified by path. Returns the
    formatted parameters in a dictionary

    :return: Formatted parameters in a dictionary
    :rtype: dict
    """
    param_dict = {}
    paginator = ssm.get_paginator('get_parameters_by_path')

    # Handle pagination
    for page in paginator.paginate(
            Path='/deprovisioning/steps',
            Recursive=True
    ):
        for parameter in page['Parameters']:
            param_parts = parameter.get('Name').split('/')
            step_name = param_parts[-1]
            acct_type = param_parts[-2]

            if acct_type not in param_dict:
                param_dict[acct_type] = {}

            param_dict[acct_type][step_name] = parameter.get('Value')

    return param_dict


def lambda_handler(event, context):
    """
    Advances user to the next step in the deprovisioning process.

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    params = get_step_params()

    records = json.loads(event.get('Records')[0].get('Sns').get('Message'), cls=event_table.EventTableRecordDecoder)
    for record in records:
        acct_type = record.account_type
        step_name = record.next_step
        update_step(record, params[acct_type][step_name])

    return {
        'statusCode': 200,
        'body': "Success"
    }
