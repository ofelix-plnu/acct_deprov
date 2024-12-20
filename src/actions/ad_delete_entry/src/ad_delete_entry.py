import boto3
import json
import os
from botocore.exceptions import ClientError
from acct_decom_utils.plnu_logger import plnu_logger
from acct_decom_utils.failed_lambda_processing.deprovisioning_action_wrapper import deprovisioning_action
from acct_decom_utils.exceptions.exceptions import AcctDeprovException, RetryException
from acct_decom_utils.failed_lambda_processing.handle_success import handle_success
from acct_decom_utils.event_table import event_table

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()
state_machine_arn = os.getenv('state_machine_arn')

env = os.getenv('deploy_environment')
domain = '@devptloma.com'
wait = '180'
if env == 'production':
    domain = '@pointloma.edu'
    wait = '15552000'  # 180 days

# Values for passing into deporvisioning function decorator
lambda_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME')
sns_arn = os.getenv('failure_topic_arn')

sfn = boto3.client('stepfunctions')


def lambda_handler(event, context):
    """
    ad_delete_entry lambda handler

    Processes SNS messages, extracts records, and initiates the execution of an AWS Step Functions state machine for
    each record.

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    global lambda_name
    lambda_name = context.function_name
    logger.info(lambda_name)

    records = json.loads(event['Records'][0]['Sns']['Message'])
    for record in records:
        try:
            start_sfn_execution(record)
        except Exception as e:
            logger.error(f'Step Function execution failed for record {record}: {e}')
            continue


@deprovisioning_action(sns_arn, lambda_name)
def start_sfn_execution(record):
    """
    Initiates the execution of an AWS Step Functions state machine with a specified input

    :param record: The input record to be processed by the Step Functions state machine
    """
    input_dict = {'record': record, 'action': 'suspend', 'waitSeconds': wait}
    try:
        response = sfn.start_execution(
            stateMachineArn=state_machine_arn,
            input=json.dumps(input_dict)
        )
        logger.info(f'Step Function started successfully: {response}')

        json_data = json.dumps(record)
        event_record = json.loads(json_data, cls=event_table.EventTableRecordDecoder)
        handle_success(event_record, lambda_name, sns_arn)
    except ClientError as e:
        logger.error(f"Something went wrong. Error: {e.response['Error']['Message']}")
        raise RetryException(str(e), record)
