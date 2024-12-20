import json
import os
from canvasapi import Canvas
from canvasapi.exceptions import ResourceDoesNotExist
from typing import List
from acct_decom_utils.event_table import event_table
from acct_decom_utils.exceptions.exceptions import RetryException
import boto3

from acct_decom_utils.plnu_logger import plnu_logger
from acct_decom_utils.failed_lambda_processing.deprovisioning_action_wrapper import deprovisioning_action
from acct_decom_utils.failed_lambda_processing.handle_success import handle_success


secret_id = 'account_deprovisioning_canvas'

# Values for passing into deporvisioning function decorator
lambda_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME')
sns_arn = os.getenv('failure_topic_arn')

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()


class CanvasService:

    __instance = None
    service = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super(CanvasService, cls).__new__(cls)
        return cls.__instance

    def __init__(self):

        sm = boto3.client('secretsmanager')
        secret = sm.get_secret_value(SecretId=secret_id)
        secret_val = json.loads(secret['SecretString'])
        self.api_key = secret_val['api_key']

        self.url = os.getenv('canvas_url')
        self.service = Canvas(self.url, self.api_key)

    def get_service(self):
        return self.service


def lambda_handler(event, context):
    """
    `force_logout_canvas` lambda handler.

    Retrieves the specified user and forcefully logs them out.

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """

    records: List[event_table.EventTableRecord] = json.loads(event.get('Records')[0].get('Sns').get('Message'),
                                                             cls=event_table.EventTableRecordDecoder)
    for user_to_process in records:

        uid = user_to_process.universal_id
        acct_type = user_to_process.account_type
        if acct_type == 'employee':
            sis_id = f"UE{uid}"
        else:
            sis_id = f"US{uid}"
        try:
            terminate_canvas_session(sis_id, user_to_process)
        except Exception as e:
            logger.info(f"Something went wrong while terminiating Canvas session. {e}")
            continue
        handle_success(user_to_process, lambda_name, sns_arn)


@deprovisioning_action(sns_arn, lambda_name)
def terminate_canvas_session(sis_id, record):
    """
    Terminate a user's session in Canvas.

    :param sis_id: The SIS ID of the u ser whose session needs to be terminated
    :param record: User's information

    """
    canvas = CanvasService()
    try:
        canvas_user = canvas.get_service().get_user(sis_id, "sis_user_id")
    except ResourceDoesNotExist as e:
        logger.warn(f"User with SIS ID {sis_id} not found. Skipping session termination. Details: {e}")
        return
    except Exception as e:
        logger.error(f"Error retrieving user with SIS ID {sis_id}: {e}")
        raise RetryException(f"User retrieval failed: {str(e)}", record)

    try:
        response = canvas_user.terminate_sessions()
        logger.info(f"Terminate sessions response for user {sis_id}: {response}")

        if response is None or response.strip() == "":
            logger.warn(f"Received empty response from terminate_sessions for user {sis_id}. Treating as success.")
            return

    except Exception as e:
        if "Expecting value" in str(e):
            logger.warn(f"Unexpected response format from terminate_sessions for user {sis_id}. Treating as success.")
        else:
            logger.error(f"Unexpected error during session termination for user {sis_id}: {e}")
            raise RetryException(f"Session termination failed: {str(e)}", record)
    logger.info(f"Successfully processed termination for user {sis_id}.")
