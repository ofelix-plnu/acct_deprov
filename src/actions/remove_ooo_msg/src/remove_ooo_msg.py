from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import os
import json
import time

from acct_decom_utils.event_table import event_table
from acct_decom_utils.plnu_logger import plnu_logger
from acct_decom_utils.google_credentials import google_credentials
from acct_decom_utils.failed_lambda_processing.deprovisioning_action_wrapper import deprovisioning_action
from acct_decom_utils.failed_lambda_processing.handle_success import handle_success
from acct_decom_utils.exceptions.exceptions import GoogleAcctDeprovException
from typing import List
from string import Template
from datetime import datetime, timezone

SCOPES = ['https://www.googleapis.com/auth/gmail.settings.basic']

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()

env = os.getenv('deploy_environment')
domain = '@devptloma.com'
if env == 'production':
    domain = '@pointloma.edu'

# Values for passing into deporvisioning function decorator
lambda_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME')
sns_arn = os.getenv('failure_topic_arn')


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
    remove_ooo_msg lambda handler.

    Updates user's out of office message to display a departure notification for a former employee.

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    records: List[event_table.EventTableRecord] = json.loads(
        event.get('Records')[0].get('Sns').get('Message'),
        cls=event_table.EventTableRecordDecoder)

    gls = GoogleGMailService()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    ooo_html_path = os.path.join(current_dir, "ooo.html")

    with open(ooo_html_path, 'r') as html_file:
        html_content = html_file.read()

    for record in records:

        failure = False

        username = record.username
        user_id = f"{username}{domain}"
        service = gls.get_service(user_id)

        user_data = {
            'first_name': record.firstname,
            'last_name': record.lastname,
            'manager_first': record.mgr_first,
            'manager_last': record.mgr_last,
            'manager_email': record.mgr_email,
            'cpy_yr': datetime.now(timezone.utc).year
        }
        template = Template(html_content)

        message_config = {
            'enableAutoReply': True,
            'responseSubject': f"{record.firstname} {record.lastname} - Employment Status Update",
            'responseBodyHtml': template.substitute(user_data),
            'restrictToDomain': False,
            'startTime': round(time.time() * 1000)
        }

        logger.info(f"Processing out of office message for {username}")
        try:
            set_user_ooo_msg(record, service, message_config)
            logger.info(f"Successfuly processed out of office message for {username}.")
        except Exception as e:

            for item in e.args:
                print(item)
                print(type(item))

            logger.error(f"Failed to update out of office message for {user_id}: {str(e)}")
            failure = True
            continue

        if not failure:
            handle_success(record, lambda_name, sns_arn)

        return {'statusCode': 200, 'body': 'Success'}


@deprovisioning_action(sns_arn, lambda_name)
def set_user_ooo_msg(record, service, message_config):
    """
    Updates vacation responder settings.

    :param record: User's information
    :param service: The Google Admin SDK service object
    :param message_config: The new out-of-office message/configuration
    """
    try:
        service.users().settings().updateVacation(userId='me', body=message_config).execute()
    except RefreshError as e:
        if len(e.args) > 1 and isinstance(e.args[1], dict):
            error = e.args[1]
            if error.get("error") == "invalid_grant" and error.get("error_description") == "Invalid email or User ID":
                logger.info(f"User {record.username} does not exist. Not an error. Moving on.")
                return
        logger.error(f"Unexpected error while updating out-of-office for {record.username}: {e}")
        raise
    except HttpError as e:
        logger.error(f"Google issue updating out of office message: {str(e)}")
        raise GoogleAcctDeprovException(str(e), record, e.resp)
