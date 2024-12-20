from acct_decom_utils.plnu_logger import plnu_logger
import os
import json
import boto3

log_level = os.getenv('log_level', 'INFO')
logger = plnu_logger.PLNULogger(log_level).get_logger()
deploy_env = os.getenv('deploy_environment')
source_arn = os.getenv('email_arn')

ses = boto3.client('ses')


def lambda_handler(event, context):
    """
    `notify_email_terminal_lambda` lambda handler.

    Sends an email to an interested party informing them of a failed lambda, and the need for manual intervention

    :param event: The event data passed to the Lambda function.
    :param context: The Lambda execution context.
    """
    logger.info(event)
    msg = json.loads(event.get('Records')[0].get('Sns').get('Message'))
    username = msg.get("username")
    lambda_name = msg.get("lambda_name")
    error = msg.get("error")

    response = ses.send_email(
        Destination={"ToAddresses": [os.getenv('sns_failure_topic_email')]},
        SourceArn=source_arn,
        Message={
            "Body": {
                "Text": {
                    "Charset": "UTF-8",
                    "Data": f'A failure has occurred when attempting to deprovision {username} via task {lambda_name}. '
                            f'This is the end of automated attempts to take care of this issue, please check that the '
                            f'account is in the expected state manually\n\n'
                            f'The error passed by the process is {error}\n\n'
                }
            },
            "Subject": {"Charset": "UTF-8", "Data": f"Account Deprovisioning Failure: {lambda_name} in {deploy_env} "
                                                    f"environment"}
        },
        Source=os.getenv('from_email'),
        ReturnPathArn=source_arn
    )
    logger.info(f"response: {response}")

    return {
        'statusCode': 200,
        'body': 'Success'
    }
