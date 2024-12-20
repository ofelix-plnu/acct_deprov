from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import os
from acct_decom_utils.event_table import event_table
from acct_decom_utils.plnu_logger import plnu_logger
from acct_decom_utils.google_credentials import google_credentials
from acct_decom_utils.failed_lambda_processing.deprovisioning_action_wrapper import deprovisioning_action
from acct_decom_utils.failed_lambda_processing.handle_success import handle_success
from acct_decom_utils.exceptions.exceptions import (AcctDeprovException, GoogleAcctDeprovException,
                                                    GoogleRetryException, GoogleTerminalException)
from typing import List

PRODUCT_ID = "101031"
EMP_SKU = "1010310006"
STU_SKU = "1010310005"

SCOPES = ['https://www.googleapis.com/auth/apps.licensing', 'https://www.googleapis.com/auth/admin.directory.user']

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()

env = os.getenv('deploy_environment')
domain = '@devptloma.com'
if env == 'production':
    domain = '@pointloma.edu'

# Values for passing into deporvisioning function decorator.
lambda_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME')
sns_arn = os.getenv('failure_topic_arn')


# This class is a singleton to ensure that we only have one instance of the google admin service.
class GoogleLicenseService:
    __instance = None
    service = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super(GoogleLicenseService, cls).__new__(cls)
        return cls.__instance

    def __init__(self):
        self.credentials = google_credentials.GoogleApiCredentials(scopes=SCOPES).get_credentials()
        self.service = build('licensing', 'v1', credentials=self.credentials)

    def get_service(self):
        return self.service


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
    `remove_google_license` lambda_handler.

    Revokes user's license

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    gls = GoogleLicenseService()
    gas = GoogleAdminService()
    license_service = gls.get_service()
    admin_service = gas.get_service()

    records: List[event_table.EventTableRecord] = json.loads(
        event.get('Records')[0].get('Sns').get('Message'),
        cls=event_table.EventTableRecordDecoder)

    for record in records:
        failure = False
        try:
            process_user(record, license_service, admin_service, domain, EMP_SKU, STU_SKU)
        except Exception as e:
            logger.error(f"Failure in remove Google license workflow: {e}")
            failure = True
            continue

        if not failure:
            handle_success(record, lambda_name, sns_arn)


def get_user(admin_service, user_id, record):
    try:
        user = admin_service.users().get(userKey=user_id).execute()
        return user
    except HttpError as e:
        logger.info(f"User {user_id} not found")
        return None


@deprovisioning_action(sns_arn, lambda_name)
def remove_user_license(license_service, user_id, sku, record):
    """
    Revokes user's license

    :param record: User's information
    :param license_service: The Google Admin SDK service object
    :param sku: A product SKU's unique identifier.
    :param user_id: The user's current primary email address
    """
    logger.info(f"Removing license {PRODUCT_ID}:{sku} from {user_id}")
    try:
        license_service.licenseAssignments().delete(productId=PRODUCT_ID, skuId=sku, userId=user_id).execute()
        return True
    except HttpError as e:
        msg = f"Error processing licensing removal for {user_id}: {e}: {e.status_code}"
        logger.error(msg)
        if e.resp.status == 404:
            logger.error("License not found for user. Moving on.")
            return True
        else:
            raise GoogleAcctDeprovException(msg, record, e.resp)


@deprovisioning_action(sns_arn, lambda_name)
def move_user_to_org(admin_service, user_id, org_path, record):
    try:
        admin_service.users().update(userKey=user_id, body={"orgUnitPath": org_path}).execute()
        logger.info(f"Moved user {user_id} to org unit {org_path}")
        return True
    except HttpError as e:
        logger.error(f"Error moving user {user_id} to {org_path}: {e}")
        raise GoogleAcctDeprovException(e.reason, record, e.resp)


@deprovisioning_action(sns_arn, lambda_name)
def process_user(record, license_service, admin_service, domain, emp_sku, stu_sku):
    sku = ""
    user_id = f"{record.username}{domain}"
    if record.account_type == "employee":
        sku = emp_sku
    elif record.account_type == "student":
        sku = stu_sku
    former_employee_org_path = '/Former Employees'

    try:
        # check if user exists
        user = get_user(admin_service, user_id, record)
        if not user:
            logger.info(f"User {user_id} not found. Not an error. Skipping.")
            return True

        # move user to inactive employee org
        move_user_to_org(admin_service, user_id, former_employee_org_path, record)

        # remove user license
        remove_user_license(license_service, user_id, sku, record)
        return True
    except Exception as e:
        logger.error(e)
