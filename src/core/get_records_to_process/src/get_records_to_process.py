import json
import boto3
from acct_decom_utils.event_table import event_table
from acct_decom_utils.plnu_logger import plnu_logger
import os

topic_arn = os.environ.get("deprov_topic_arn")

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()


def get_step_params():
    """
    Uses the AWS Systems Manager (SSM) client to retrieve and format parameters specified by path. Returns the
    formatted parameters in a dictionary

    :return: Formatted parameters in a dictionary
    :rtype: dict
    """
    ssm = boto3.client('ssm')
    params = ssm.get_parameters_by_path(
        Path='/deprovisioning/steps',
        Recursive=True
    )

    param_dict = {}
    for parameter in params.get('Parameters'):
        param_parts = parameter.get('Name').split('/')
        step_name = param_parts[-1]
        acct_type = param_parts[-2]

        if acct_type not in param_dict:
            param_dict[acct_type] = {}

        param_dict[acct_type][step_name] = parameter.get('Value')

    return param_dict


def lambda_handler(event, context):
    """
    `get_records_to_process` lambda handler.

    Retrieves pending events from 'EventTable' DynamoDB table for processing.

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    params = get_step_params()

    sns = boto3.client('sns')

    for acct_type in params.keys():

        logger.info(f"Processing steps for account type {acct_type}")
        for step in params[acct_type].keys():
            logger.info(f"Processing records for step {step}")

            evt_table = event_table.EventTable()
            pending = evt_table.get_pending_events(step)

            if pending:
                sns.publish(
                    TargetArn=topic_arn,
                    Message=json.dumps({'default': json.dumps(pending, cls=event_table.EventTableRecordEncoder)}),
                    MessageStructure='json',
                    MessageAttributes={
                        'step': {
                            'DataType': 'String',
                            'StringValue': f'{step}'
                        }
                    }
                )
            else:
                logger.warn(f"No pending records found for {acct_type}:{step}")

    return {
        'statusCode': 200,
        'body': "Success"
    }
