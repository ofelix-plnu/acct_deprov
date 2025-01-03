from acct_decom_utils.event_table import event_table
from acct_decom_utils.plnu_logger import plnu_logger
import os
import json

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()


def lambda_handler(event, context):
    """
    `flag_failed_lambda_retry` lambda handler.

    Update 'EventState' DynamoDB table to add info about a failed Lambda execution.

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    msg = json.loads(event.get('Records')[0].get('Sns').get('Message'))

    username = msg.get('username')
    lambda_name = msg.get('lambda_name')

    evt_table = event_table.EventTable()
    record = json.loads(json.dumps(
        evt_table.add_failed_lambda(username, lambda_name), cls=event_table.EventTableRecordEncoder),
        cls=event_table.EventTableRecordDecoder)
    logger.info(f'Add failed lambda reponse: {record.HTTPStatusCode}')
