from acct_decom_utils.event_table import event_table
from acct_decom_utils.plnu_logger import plnu_logger
from acct_decom_utils.failed_lambda_processing.handle_success import handle_success

import json
import os

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()

lambda_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME')
sns_arn = os.getenv('failure_topic_arn')


def lambda_handler(event, context):
    """
    `delete_record` lambda handler.

    Removes specified user from 'EventState' DynamoDB/account deprovisioning process.

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    if 'Records' in event and 'Sns' in event['Records'][0]:
        records = json.loads(
            event.get('Records')[0].get('Sns').get('Message'),
            cls=event_table.EventTableRecordDecoder)
    else:
        records = json.loads(event['body'], cls=event_table.EventTableRecordDecoder)

    for record in records:
        if record.account_type == 'student':
            pass

        et = event_table.EventTable()
        et.delete(record.username)
        handle_success(record, sns_arn, lambda_name)

    return {"status": 200, "message": "Delete successful"}
