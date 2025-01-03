from acct_decom_utils.plnu_logger import plnu_logger
from acct_decom_utils.event_table import event_table
import os
import json

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()


def lambda_handler(event, context):
    """
    `remove_failure_state` lambda handler.

    Handles removing a given lambda from the list of failed lambdas for a user in their dynamodb record

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    msg = json.loads(event.get('Records')[0].get('Sns').get('Message'))
    evt_table = event_table.EventTable()
    evt_table.remove_failed_lambda(msg.get("username"), msg.get("lambda_name"))
    logger.info('Successfully removed failure state')

    return {
        'statusCode': 200,
        'body': 'Success'
    }
