import os
import boto3
import json

from botocore.exceptions import ClientError
from acct_decom_utils.plnu_logger import plnu_logger

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()

# Values for passing into deporvisioning function decorator
lambda_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME')
sns_arn = os.getenv('failure_topic_arn')

bucket_arn = os.getenv('bucket_arn')
bucket_name = os.getenv('bucket_name')
queue_url = os.getenv('queue_url')

# BOTO3 Clients
sqs = boto3.client('sqs')
ddb = boto3.client('dynamodb')


def lambda_handler(event, context):
    """
    `ad_delete_sfn_handler` lambda handler.

    Extracts record information and sends the user's details, along with specified "suspend" or delete" actions,
    to the "ad_delete" SQS queue

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    record = event['record']
    action = event['action']
    wait = event['waitSeconds']

    if action == 'suspend':
        process_suspend(record, action, queue_url, lambda_name)
        action = 'delete'
    else:
        process_delete(record, action, queue_url, lambda_name)
        action = 'end'

    return {'record': record, 'action': action, 'waitSeconds': wait}


def process_suspend(record, action, url, message_group_id):
    """
    Handles the suspend action by sending the record to the SQS queue.

    :param record: The record to be processed.
    :param action: The action to take.
    :param url: The URL of the SQS queue.
    :param message_group_id: The message group ID for FIFO queues.
    """
    logger.info(f"Processing suspend for {record.get('username')}")

    message_body = {
        "action": action,
        "id": record.get('universal_id'),
        "username": record.get('username'),
        "account_type": record.get('account_type')
    }

    send_to_sqs(url, message_body, message_group_id)


def process_delete(record, action, url, message_group_id):
    """
    Handles the delete action by checking the record's status in DynamoDB.

    :param record: The record to be processed.
    :param action: The action to take.
    :param url: The URL of the SQS queue.
    :param message_group_id: The message group ID for FIFO queues.
    """
    record_username = record.get('username')
    logger.info(f"Processing delete for {record_username}")

    ddb_item = query_dynamodb(record_username)

    if ddb_item:
        ddb_username = ddb_item['username']['S']
        if ddb_username == record_username:
            message_body = {
                "action": action,
                "id": record.get('universal_id'),
                "username": record_username,
                "account_type": record.get('account_type'),
            }
            send_to_sqs(url, message_body, message_group_id)
    else:
        logger.warn(f"User {record_username} not in DynamoDB. Assuming user is rehired. Moving on.")


def query_dynamodb(username):
    """
    Queries the DynamoDB table for the given username.

    :param username: The username to query.
    :return: The DynamoDB item or None if not found.
    """
    try:
        response = ddb.get_item(
            TableName='EventState',
            Key={'username': {'S': username}},
        )
        return response.get('Item')
    except boto3.exceptions.Boto3Error as e:
        logger.error(f'Failed to query DynamoDB for username {username}: {e}')
        raise e


def send_to_sqs(queueurl, message_body, message_group_id):
    """
    Sends a message to the SQS queue.

    :param queueurl: The URL of the SQS queue.
    :param message_body: The content of the message to be sent.
    :param message_group_id: The message group ID for FIFO queues.
    """
    try:
        sqs.send_message(
            QueueUrl=queueurl,
            MessageBody=json.dumps(message_body),
            MessageGroupId=message_group_id
        )
        logger.info(f"Message successfully sent to SQS: {message_body}")
    except ClientError as e:
        logger.error(f"Something went wrong: {e.response['Error']['Message']}")
        raise e
