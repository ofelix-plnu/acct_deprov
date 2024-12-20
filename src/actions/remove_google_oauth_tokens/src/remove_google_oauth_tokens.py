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

SCOPES = ['https://www.googleapis.com/auth/admin.directory.user.security']

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()

env = os.getenv('deploy_environment')
domain = '@devptloma.com'
if env == 'production':
    domain = '@pointloma.edu'

# Values for passing into deporvisioning function decorator
lambda_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME')
sns_arn = os.getenv('failure_topic_arn')


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
    `remove_google_oauth_tokens` lambda handler.

    Retrieves and removes all access tokens issued by a user for an application.

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    records = json.loads(event.get('Records')[0].get('Sns').get('Message'), cls=event_table.EventTableRecordDecoder)
    for user_to_process in records:
        email = user_to_process.username + domain
        admin_svc = GoogleAdminService()
        service = admin_svc.get_service()

        failure = False
        try:
            tokens = get_user_tokens(service, email)
            if tokens is None or tokens.get('items') is None:
                logger.info(f"No tokens found to remove for user {email}")
                continue
        except HttpError as e:
            logger.warn(f"User {email} not found. Not an error. Moving on. \nResponse from server: {e}")
            continue
        try:
            for token in tokens.get('items'):
                remove_token(user_to_process, service, token.get('clientId'), email)
        except Exception as e:
            failure = True
            logger.error(str(e))

        if not failure:
            handle_success(user_to_process, lambda_name, sns_arn)

    return {
        'statusCode': 200,
        'body': 'Success'
    }


def get_user_tokens(service, email):
    """
    Returns the set of tokens specified user has issued to 3rd party applications.

    :param service: The Google Admin SDK service object
    :param email: User's email address
    """
    return service.tokens().list(userKey=email).execute()


@deprovisioning_action(sns_arn, lambda_name)
def remove_token(record, service, client_id, email):
    """
    Deletes all access tokens issued by a user for an application.

    :param record: User's information
    :param service: The Google Admin SDK service object
    :param client_id: Identifies user in the API request. The value can be the user's primary email address,
    alias email address, or unique user ID.
    :param email: The Client ID of the application the token is issued to.
    """
    logger.info(f"Removing token with clientId {client_id} from {email}")
    try:
        service.tokens().delete(userKey=email, clientId=client_id).execute()
    except HttpError as e:
        msg = f"Failed to remove oauth token associated with clientId {client_id} for user {email}"
        logger.error(msg)
        raise GoogleAcctDeprovException(msg, record, e.resp)
