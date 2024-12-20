from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import os
import json

from acct_decom_utils.event_table import event_table
from acct_decom_utils.plnu_logger import plnu_logger
from acct_decom_utils.google_credentials import google_credentials
from acct_decom_utils.failed_lambda_processing.deprovisioning_action_wrapper import deprovisioning_action
from acct_decom_utils.failed_lambda_processing.handle_success import handle_success
from acct_decom_utils.exceptions.exceptions import GoogleAcctDeprovException
from typing import List

SCOPES = ['https://www.googleapis.com/auth/admin.directory.user',
          'https://www.googleapis.com/auth/admin.directory.user.security']

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
    `force_logout_google` lambda handler.

    Retrieves the specified user and logs them out.

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    records: List[event_table.EventTableRecord] = json.loads(
        event.get('Records')[0].get('Sns').get('Message'),
        cls=event_table.EventTableRecordDecoder)

    admin_svc = GoogleAdminService()
    service = admin_svc.get_service()

    for record in records:
        failure = False
        try:
            user = get_user(service, record)
            logger.info(user)
        # If user doesn't exist, skip it and continue to the next user
        except Exception as e:
            logger.warn(f"Response: {e}")
            logger.info(f"Skipping: User {record.username} not found, no action required.")
            continue
        try:
            response = user_logout(service, record)
            logger.info(f"{record.username} has been successfully logged out. {response}")
        except Exception as e:
            logger.error(f"Google issue with {record.username} log out: {str(e)}")
            failure = True

        if not failure:
            handle_success(record, lambda_name, sns_arn)


def get_user(service, record):
    """
    Retrieves user information from a Google Admin SDK service based on the provided email

    :param service: Google Admin SDK service object used for interacting with user data
    :param record: The user's record whose information is to be retrieved
    """
    return service.users().get(userKey=f"{record.username}{domain}").execute()


@deprovisioning_action(sns_arn, lambda_name)
def user_logout(service, record):
    """
     Initiates a user logout using the provided Google Admin SDK service

    :param service: The Google Admin SDK service object
    :param record: A dictionary containing user information
    """
    email = f"{record.username}{domain}"
    logger.info(f"Attempting {record.username} logout")
    try:
        return service.users().signOut(userKey=email).execute()
    except HttpError as err:
        raise GoogleAcctDeprovException(str(err), record, err.resp)
