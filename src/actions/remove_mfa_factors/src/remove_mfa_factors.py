from userprovisioning.oneloginwrapper import oneloginwrapper
from acct_decom_utils.plnu_logger import plnu_logger
from acct_decom_utils.failed_lambda_processing.deprovisioning_action_wrapper import deprovisioning_action
from acct_decom_utils.failed_lambda_processing.handle_success import handle_success
from acct_decom_utils.exceptions.exceptions import RetryException, TerminalException
from acct_decom_utils.event_table import event_table
import json
from typing import List
import os

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()

# Values for passing into deporvisioning function decorator
lambda_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME')
sns_arn = os.getenv('failure_topic_arn')


def lambda_handler(event, context):
    """
    `remove_mfa_factors` lambda handler.

    Removes user's OneLogin mfa factors.

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    records: List[event_table.EventTableRecord] = json.loads(
        event.get('Records')[0].get('Sns').get('Message'),
        cls=event_table.EventTableRecordDecoder)

    for record in records:
        failure = False
        try:
            remove_mfa_factors(record)
        except Exception as e:
            logger.error(e)
            failure = True
            continue

        if not failure:
            handle_success(record, lambda_name, sns_arn)


@deprovisioning_action(sns_arn, lambda_name)
def remove_mfa_factors(record: event_table.EventTableRecord):
    """
    Removes multi-factor authentication factors for a user based on their username.

    :param record: User's information
    """
    ol_client = oneloginwrapper.OneLoginClientWrapper()
    username = record.username

    user = ol_client.get_user_by_username_from_ol(username)
    if user:
        logger.info(f"Removing mfa factors for user {username}")
        factors = ol_client.get_mfa_factors(user.id)
        logger.info(f"Found mfa factors with ids {factors}: removing now")
        success = ol_client.remove_mfa_factors(user.id, factors)
        if not success:
            raise RetryException(f"Failed to remove mfa factors for {username}", record)
        else:
            logger.info(f"Removed mfa factors from {username}")

    else:
        logger.warn(f"No user found in OneLogin with username {username}")
