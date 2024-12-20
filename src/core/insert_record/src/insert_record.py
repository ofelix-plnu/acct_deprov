from acct_decom_utils.event_table import event_table
from acct_decom_utils.plnu_logger import plnu_logger
from acct_decom_utils.exceptions.exceptions import InsertException
import json
import os

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()


def lambda_handler(event, context):
    """
    `insert_record` lambda handler.

    Inserts a record into 'EventState' DynamoDB table.

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    event_json = json.dumps(event)
    insert_rec: event_table.EventTableRecord = json.loads(event_json, cls=event_table.EventTableRecordDecoder)

    insert_rec.next_step = f"{get_step_prefix(insert_rec.account_type)}-1"

    logger.info(f"Creating entry for {insert_rec.username} with entry date of {insert_rec.insert_date}")

    et = event_table.EventTable()

    try:
        et.insert(insert_rec)
    except InsertException as e:
        # Likely need to add some sort of notification here, for now just logging
        logger.error(f"Failed to insert record: {str(e)}")

    return {
        "status": 200,
        "message": "Insert successful"
    }


def get_step_prefix(account_type: str):
    """
    Returns a prefix based on the provided account type

    :param str account_type: The type of account. e.g "employee" or "student"

    :return str: Account type prefix
    """
    if account_type == "employee":
        return "emp"
    elif account_type == "student":
        return "stu"
    else:
        return ""
