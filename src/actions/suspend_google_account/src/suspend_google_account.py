from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import json
import os

from acct_decom_utils.event_table import event_table
from acct_decom_utils.plnu_logger import plnu_logger
from acct_decom_utils.google_credentials import google_credentials
from acct_decom_utils.failed_lambda_processing.deprovisioning_action_wrapper import deprovisioning_action
from acct_decom_utils.failed_lambda_processing.handle_success import handle_success
from acct_decom_utils.exceptions.exceptions import GoogleAcctDeprovException
from typing import List

SCOPES = ['https://www.googleapis.com/auth/admin.directory.user']

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()

env = os.getenv('deploy_environment')
domain = '@devptloma.com'
if env == 'production':
    domain = '@pointloma.edu'

# Values for passing into deporvisioning function decorator
lambda_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME')
sns_arn = os.getenv('failure_topic_arn')


class GoogleAdminService:
    __instance = None
    service = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super(GoogleAdminService, cls).__new__(cls)
        return cls.__instance

    def __init__(self):
        self.credentials = google_credentials.GoogleApiCredentials(scopes=SCOPES).get_credentials()
        self.service = build('admin', 'directory_v1', credentials=self.credentials)

    def get_service(self):
        return self.service


def lambda_handler(event, context):
    """
    suspend_google_account lambda handler.

    Suspends a user's Google account

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    records: List[event_table.EventTableRecord] = json.loads(
        event.get('Records')[0].get('Sns').get('Message'),
        cls=event_table.EventTableRecordDecoder)

    admin_svc = GoogleAdminService()
    service = admin_svc.get_service()

    for record in records:
        username = record.username

        user = get_user(service, record)
        if not user:
            logger.warn(f"{username}'s account does not exist. Not an error, moving on.")
            continue

        try:
            response = suspend_user_acct(service, record)
            logger.info(f"{username}'s account has been suspended. {response}")
        except Exception as e:
            logger.error(e)
            continue

        handle_success(record, lambda_name, sns_arn)


def get_user(service, record):
    """
    Retrieves user information from a Google Admin SDK service based on the provided email

    :param service: Google Admin SDK service object used for interacting with user data
    :param record: The user's record whose information is to be retrieved
    """
    try:
        return service.users().get(userKey=f"{record.username}{domain}").execute()
    except HttpError as err:
        logger.error(str(err))


@deprovisioning_action(sns_arn, lambda_name)
def suspend_user_acct(service, record):
    """
    Suspends the specified user's account.

    :param service: The Google Admin SDK service object
    :param record: User's information
    """
    username = record.username
    email = f"{username}{domain}"
    logger.info(record.to_json())
    try:
        return service.users().update(userKey=email, body={'suspended': True}).execute()
    except HttpError as err:
        logger.error(f"Google issue suspending current account: {str(err)}")
        raise GoogleAcctDeprovException(str(err), record, err.resp)
