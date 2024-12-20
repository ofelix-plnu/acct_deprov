from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import os
from acct_decom_utils.event_table import event_table
from acct_decom_utils.plnu_logger import plnu_logger
from acct_decom_utils.google_credentials import google_credentials
from acct_decom_utils.failed_lambda_processing.handle_success import handle_success
from acct_decom_utils.failed_lambda_processing.deprovisioning_action_wrapper import deprovisioning_action
from acct_decom_utils.exceptions.exceptions import GoogleAcctDeprovException

lambda_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME')
sns_arn = os.getenv('failure_topic_arn')

SCOPES = ['https://www.googleapis.com/auth/admin.directory.user']

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()

env = os.getenv('deploy_environment')
domain = '@devptloma.com'
if env == 'production':
    domain = '@pointloma.edu'


# This class is a singleton to ensure that we only have one instance of the google admin service
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
    `disable_in_gal` lambda handler.

    Disables a user's inclusion in the Global Address List (GAL)

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """

    records = json.loads(event.get('Records')[0].get('Sns').get('Message'), cls=event_table.EventTableRecordDecoder)
    for user_to_process in records:
        username = user_to_process.username
        email = username + domain
        admin_svc = GoogleAdminService()
        service = admin_svc.get_service()
        # Check if the user exists in the Google Admin Directory

        failure = False

        try:
            user = get_user(service, email)
        # If user doesn't exist, skip it and continue to the next user
        except Exception as e:
            logger.warn(f"Response: {e}")
            logger.info(f"Skipping: User {email} not found, no action required.")
            continue
        if user['includeInGlobalAddressList']:
            logger.info(f"Removing {email} from GAL")
            try:
                disable_in_gal(service, email, username)
                logger.info("Successfully removed user from GAL.")
            except Exception as e:
                logger.info(f"Failed to remove user {email} from gal: {e}")
                failure = True
        else:
            logger.info("User not in GAL.")

        if not failure:
            handle_success(user_to_process, lambda_name, sns_arn)

    return {
        'statusCode': 200,
        'body': 'Success'
    }


def get_user(service, email):
    """
    Retrieves user information from a Google Admin SDK service based on the provided email

    :param service: Google Admin SDK service object used for interacting with user data
    :param email: The email address of the user whose information is to be retrieved
    """
    return service.users().get(userKey=email).execute()


@deprovisioning_action(sns_arn, lambda_name)
def disable_in_gal(service, email, username):
    """
    Disables a user's inclusion in the Global Address List (GAL) using the provided Google Admin SDK service

    :param service: The Google Admin SDK service object
    :param email: The email addrdss of the user to be excluded from the GAL
    :param username: The username associated with the user account
    """

    # Enable the account in the global address list
    update_data = dict()
    update_data['includeInGlobalAddressList'] = False
    try:
        service.users().update(userKey=email, body=update_data).execute()
    except HttpError as e:
        raise GoogleAcctDeprovException(str(e), username, e.resp)
