from userprovisioning.oneloginwrapper import oneloginwrapper
from acct_decom_utils.plnu_logger import plnu_logger
from acct_decom_utils.failed_lambda_processing.deprovisioning_action_wrapper import deprovisioning_action
from acct_decom_utils.failed_lambda_processing.handle_success import handle_success
from acct_decom_utils.exceptions.exceptions import RetryException, TerminalException
from acct_decom_utils.event_table import event_table
import json
import os

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()

# Values for passing into deporvisioning function decorator
lambda_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME')
sns_arn = os.getenv('failure_topic_arn')


def lambda_handler(event, context):
    """
    `force_logout_onelogin` lambda handler.

    Logs out specified user

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    records = json.loads(
        event.get('Records')[0].get('Sns').get('Message'),
        cls=event_table.EventTableRecordDecoder)

    for record in records:
        try:
            log_user_out(record)
        except Exception as e:
            logger.error(e)
            continue
        handle_success(record, lambda_name, sns_arn)


@deprovisioning_action(sns_arn, lambda_name)
def log_user_out(record):
    """
    Logs a user out from OneLogin using the provided client.

    :param record: The user's information
    """
    ol_client = oneloginwrapper.OneLoginClientWrapper()
    username = record.username

    user = ol_client.get_user_by_username_from_ol(username)
    if user:
        logger.info(f"Attempting to log out {username}")
        success = ol_client.user_logout(user.id)
        if not success:
            raise RetryException(f"Failed to force logout {username}", json.loads(
                record, cls=event_table.EventTableRecordDecoder))
        logger.info(f"{record.username} is now logged out")
    else:
        logger.warn(f"No user found in OneLogin with username {username}. Not an error, moving on.")
