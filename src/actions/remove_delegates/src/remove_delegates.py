import acct_decom_utils.exceptions.exceptions
import google.auth.exceptions
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import http.client
import json
import os
from acct_decom_utils.event_table import event_table
from acct_decom_utils.plnu_logger import plnu_logger
from acct_decom_utils.google_credentials import google_credentials
from acct_decom_utils.failed_lambda_processing.deprovisioning_action_wrapper import deprovisioning_action
from acct_decom_utils.failed_lambda_processing.handle_success import handle_success
from acct_decom_utils.exceptions.exceptions import GoogleAcctDeprovException
from typing import List
import re

SCOPES = ['https://www.googleapis.com/auth/gmail.settings.sharing',
          'https://www.googleapis.com/auth/gmail.settings.basic']

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()

env = os.getenv('deploy_environment')
domain = '@devptloma.com'
if env == 'production':
    domain = '@pointloma.edu'

# Values for passing into deporvisioning function decorator
lambda_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME')
sns_arn = os.getenv('failure_topic_arn')

remove_all_delegates_step = "emp-180"


# This class is a singleton to ensure that we only have one instance of the google admin service
class GoogleGMailService:
    __instance = None
    service = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super(GoogleGMailService, cls).__new__(cls)
        return cls.__instance

    def __init__(self):
        self.credentials = google_credentials.GoogleApiCredentials(scopes=SCOPES).get_credentials()

    def get_service(self, delegated_user):
        self.service = build('gmail', 'v1', credentials=self.credentials.with_subject(delegated_user))
        return self.service


def lambda_handler(event, context):
    """
    `remove_delagates` lambda handler. Retrieves and removes user's delegates. Adds user's manager as a delegate
    """
    records: List[event_table.EventTableRecord] = json.loads(
        event.get('Records')[0].get('Sns').get('Message'),
        cls=event_table.EventTableRecordDecoder)

    gls = GoogleGMailService()

    for record in records:

        # Track if we've hit a failure scenario or not
        failure = False

        username = record.username
        user_id = f"{username}{domain}"
        mgr_email = record.mgr_email
        service = gls.get_service(user_id)

        logger.info(f"Processing delegate removal for {username}")
        # Get list of delegates for user
        try:
            delegates_payload = get_delegates(record, service)
            logger.info("Delegate data fetched.")
        except Exception as e:
            logger.error(f"Failed to get delegates for {user_id}: {str(e)}")
            failure = True
            continue

        # User not being found is not an error condition, but there's nothing else to do
        if delegates_payload is None:
            handle_success(record, lambda_name, sns_arn)
            continue

        delegates = delegates_payload.get("delegates", [])

        for delegate in delegates:
            delegate_email = delegate.get("delegateEmail")

            try:
                delete_delegate(record, service, delegate_email)
            except Exception as e:
                # If deletion fails, lambda should be flagged for retry for user. Not going to continue on this user
                logger.error(f"Failed to remove {delegate_email} from {user_id}: {str(e)}")
                failure = True
                break

        if mgr_email and record.next_step != remove_all_delegates_step:

            try:
                add_mgr_delegate(record, service)
            except Exception as e:
                logger.error(f"Failed to add {mgr_email} as delegate to {user_id}: {str(e)}")
                failure = True
                continue

        if not failure:
            handle_success(record, lambda_name, sns_arn)


class Response:

    def __init__(self, status="429"):
        self.status = status


@deprovisioning_action(sns_arn, lambda_name)
def get_delegates(record, service):
    """
    Retrieves user's specified delegates

    :param record: User's information
    :param service: The Google GMail SDK service object
    """
    username = record.username
    try:
        return service.users().settings().delegates().list(userId='me').execute()
    except HttpError as e:
        logger.error(f"Google issue getting delegate list from user: {str(e)}")
        raise GoogleAcctDeprovException(str(e), record, e.resp)
    except google.auth.exceptions.RefreshError as e:
        error = str(e).lower()
        no_user = r'.*invalid email or user id.*'
        match = re.match(no_user, error)
        if match:
            # logger.warn(f"User {username} not found in google. Not an error. Moving on.")
            logger.warn(f"Skipping: User {username} not found, no action required.")
            return
            # Forcing a test of SNS/retry lambda flow
            # raise GoogleAcctDeprovException("User blow up", record, Response())
        else:
            logger.warn(f"Unexpected issue requesting access to Google: {str(e)}")
            raise e


@deprovisioning_action(sns_arn, lambda_name)
def delete_delegate(record, service, delegate_email):
    """
    Removes the specified delegate (which can be of any verification status), and revokes any verification that may
    have been required for using it.

    :param record: User's information
    :param service: The Google GMail SDK service object
    :param delegate_email:
    """
    username = record.username
    logger.info(f"Deleting delegate {delegate_email} from {username}")
    try:
        service.users().settings().delegates().delete(userId='me', delegateEmail=delegate_email).execute()
        logger.info("Success.")
    except HttpError as e:
        raise GoogleAcctDeprovException(str(e), record, e.resp)
    logger.info(f"Successfully removed {delegate_email} from {username}")


@deprovisioning_action(sns_arn, lambda_name)
def add_mgr_delegate(record, service):
    """
    Adds a delegate with its verification status set directly to accepted, without sending any verification email.
    The delegate user must be a member of the same Google Workspace organization as the delegator user.

    :param record: User's information
    :param service: The Google GMail SDK service object
    """
    username = record.username
    mgr_email = record.mgr_email

    logger.info(f"Adding former manager as delegate to {username}: {mgr_email}")
    try:
        service.users().settings().delegates().create(userId='me',
                                                      body={'delegateEmail': mgr_email}).execute()
    except HttpError as e:
        # This block is only for development. If you can't add delegate in prod, let decorator take over.
        if env != 'production' and e.resp.status == 400:  # User is inactive
            logger.warn(f"Attempted to add delegate to inactive user {username}")
            return
        logger.error(f"Google issue adding manager as delegate: {str(e)}")
        raise GoogleAcctDeprovException(str(e), record, e.resp)
    logger.info(f"Successfully added {mgr_email} as delegate to {username}")
