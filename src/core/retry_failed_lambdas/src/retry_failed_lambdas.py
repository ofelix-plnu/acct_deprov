import json
import boto3
from acct_decom_utils.event_table import event_table
from acct_decom_utils.plnu_logger import plnu_logger
import os
from typing import List

topic_arn = os.environ.get("deprov_topic_arn")

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()


def lambda_handler(event, context):
    """
    retry_failed_lambdas lambda handler.

    Process records of failed Lambda executions with a failure count less than 3.

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    sns = boto3.client('sns')

    logger.info("Retrying failed lambdas")
    evt_table = event_table.EventTable()
    failed_items: List[event_table.EventTableRecord] = evt_table.get_failed_items()

    for failed_item in failed_items:
        logger.info(f"Found failed lambdas for {failed_item.username}")
        for lambda_name, fail_count in failed_item.failed_lambdas.items():
            logger.info(f"Publishing retry of lambda {lambda_name} for {failed_item.username}")
            if fail_count < 3:
                sns.publish(
                    TargetArn=topic_arn,
                    # Downstream lambdas expecting list of records, so need to wrap even though sending single record
                    Message=json.dumps({'default': json.dumps([failed_item], cls=event_table.EventTableRecordEncoder)}),
                    MessageStructure='json',
                    MessageAttributes={
                        'step': {
                            'DataType': 'String',
                            'StringValue': f'{lambda_name}'
                        }
                    }
                )

    return {
        'statusCode': 200,
        'body': "Success"
    }
