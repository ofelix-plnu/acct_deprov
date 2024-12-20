from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import os
from acct_decom_utils.event_table import event_table
from acct_decom_utils.plnu_logger import plnu_logger
from acct_decom_utils.google_credentials import google_credentials
from acct_decom_utils.failed_lambda_processing.handle_success import handle_success
from acct_decom_utils.failed_lambda_processing.deprovisioning_action_wrapper import deprovisioning_action
from acct_decom_utils.exceptions.exceptions import GoogleAcctDeprovException, AcctDeprovException

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


# This class is a singleton to ensure that we only have one instance of the Google admin service
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
    `remove_asps` lambda handler.

    Retrieves and removes a user's ASPs

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    records = json.loads(event.get('Records')[0].get('Sns').get('Message'), cls=event_table.EventTableRecordDecoder)
    admin_svc = GoogleAdminService()
    service = admin_svc.get_service()

    for user_to_process in records:
        username = user_to_process.username
        email = username + domain

        failure = False
        try:
            asps = get_user_asps(service, email)
            if asps is None or asps.get('items') is None:
                logger.info(f"Skipping: No asp tokens associated with user {username}")
                continue
        except HttpError as e:
            logger.warning(e)
            logger.info(f"Skipping: User {username} not found, no action required.")
            continue
        for asp in asps.get('items'):

            code = asp.get('clientId')

            try:
                remove_asp(user_to_process, service, code, email)
            except Exception as e:
                failure = True
                logger.error(f"Failed to delete asp with clientId {code} from {username}: {e}")

        if not failure:
            handle_success(user_to_process, lambda_name, sns_arn)

        logger.info("Successfully removed ASPs")
    return {
        'statusCode': 200,
        'body': 'Success'
    }


def get_user_asps(service, email):
    """
    Retrieves user's ASPs

    :param service: The Google Admin SDK service object
    :param email: User's email address
    """
    return service.asps().list(userKey=email).execute()


@deprovisioning_action(sns_arn, lambda_name)
def remove_asp(record, service, code_id, email):
    """
    Removes user's ASPs

    :param record: User's information
    :param service:  The Google Admin SDK service object
    :param code_id: Authorized app's unique identifier
    :param email: User's email address
    """
    try:
        service.asps().delete(userKey=email, codeId=code_id).execute()
    except HttpError as e:
        msg = f"Failed to remove asp associated with codeId {code_id} for user {email}: {str(e)}"
        logger.error(msg)
        raise GoogleAcctDeprovException(msg, record, e.resp)
