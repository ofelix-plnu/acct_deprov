import csv
import json
import os

import boto3
from botocore.exceptions import ClientError

from acct_decom_utils.plnu_logger import plnu_logger
from datetime import datetime

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()

# Values for passing into deporvisioning function decorator
lambda_name = os.getenv('AWS_LAMBDA_FUNCTION_NAME')
sns_arn = os.getenv('failure_topic_arn')

queue_url = os.getenv('queue_url')
bucket_name = os.getenv('bucket_name')
deploy_environment = os.getenv('deploy_environment')
TIMESTAMP_STR_FORMAT = "%Y-%m-%dT%H-%M"

env = 'Dev'
if deploy_environment == 'production':
    env = 'Prod'

# BOTO3 Clients
s3 = boto3.client('s3')
sqs = boto3.client('sqs')


def lambda_handler(event, context):
    """
    ad_delete_bucket_writer lambda handler.

    Accumulates content of each record and updates S3 file by adding to it or creating a new one if it doesn't exist.

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    date_str = datetime.now().strftime(TIMESTAMP_STR_FORMAT)
    csv_file_name = f'iam2ad{date_str}.csv'
    csv_file_path = f'/tmp/{csv_file_name}'

    try:
        logger.info("Creating file..")
        with open(csv_file_path, 'w', newline='') as csvfile:
            fieldnames = ['action', 'username']
            writer = csv.DictWriter(csvfile, fieldnames)
            writer.writeheader()

            sqs_messages_to_delete = []
            for record in event['Records']:
                body = json.loads(record['body'])
                writer.writerow({
                    'action': body['action'],
                    'username': body['username']
                })
                logger.info("Creating file..")
                sqs_messages_to_delete.append({
                    'Id': record['messageId'],
                    'ReceiptHandle': record['receiptHandle']
                })
        logger.info("Successfully created file.")

        object_key = f"IAM/iam2ad/{env}/{csv_file_name}"
        upload_to_s3(f'/tmp/{csv_file_name}', bucket_name, object_key)
        sqs_msg_cleanup(queue_url, sqs_messages_to_delete)
    except Exception as e:
        logger.error(f"Failed to write to CSV file: {e}")
        raise


def upload_to_s3(file_name, bucket_name, object_key):
    """
    Uploads a file to S3.

    :param file_name: The path to the file to upload.
    :param bucket_name: The name of the S3 bucket.
    :param object_key: The object key for the file in S3.
    """
    try:
        logger.info("Uploading file..")
        s3.upload_file(Filename=file_name, Bucket=bucket_name, Key=object_key)
        logger.info(f"File uploaded: s3://{bucket_name}/{object_key}")
    except ClientError as e:
        logger.error(f"Failed to upload file to S3: {e}")
        raise


def sqs_msg_cleanup(url, sqs_msgs):
    """
    Deletes specified messages from an SQS queue

    :param url: The URL of the SQS queue
    :param sqs_msgs: A list of dictionaries representing SQS messages to be deleted
    """

    try:
        logger.info("Attempting sqs cleanup..")
        response = sqs.delete_message_batch(
            QueueUrl=url,
            Entries=sqs_msgs
        )
        failed = response.get('Failed', [])
        if failed:
            logger.error(f"Some messages failed to delete: {failed}")
        else:
            logger.info("Success.")
    except boto3.exceptions.ClientError as e:
        logger.error(f'Error deleting SQS messages: {e}')
        raise
