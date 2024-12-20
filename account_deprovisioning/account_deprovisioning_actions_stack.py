import os

from typing import (
    List
)

from aws_cdk import (
    SecretValue,
    aws_s3 as s3,
    aws_ses as ses,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_kms as kms,
    aws_dynamodb as ddb,
    aws_secretsmanager as sm,
    aws_sns_subscriptions as subscriptions,
    aws_lambda_event_sources as lambda_event_sources,
    Duration
)

from .src.state_machine.state_machine import ad_delete_sfn_workflow
from .src.s3.bucket import bucket_init

from aws_cdk.aws_lambda import (
    IFunction
)

from constructs import Construct

from cdk_utils.cdk_utils import PLNULambda, PLNUStack

BASE_PATH = os.path.join(os.path.dirname(__file__), "..")
REL_SRC_PATH = os.path.join("src", "actions")
SRC_PATH = os.path.join(BASE_PATH, REL_SRC_PATH)


class AccountDeprovisioningActionsStack(PLNUStack):
    """
    AWS CDK Stack for the Account Deprovisioning Actions Stack

    :param scope: The construct to which this stack belongs
    """

    def __init__(self, scope: Construct, construct_id: str, topic: sns.Topic, failure_topic: sns.Topic,
                 evt_table: ddb.Table, sns_kmskey: kms.Key, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # from core stack
        deprov_topic = topic
        failure_topic = failure_topic
        event_table = evt_table
        sns_kmskey = sns_kmskey

        environment = self.cdk_env.get('environment')

        # Set up basic environment variables to be shared across all lambdas
        default_env = {'deploy_environment': environment,
                       'log_level': self.cdk_env.get('log_level'),
                       'failure_topic_arn': failure_topic.topic_arn
                       }

        force_logout_env = {'canvas_url': self.cdk_env.get('canvas_url')}

        # Create lambdas
        lambda_factory = PLNULambda(default_env=default_env)

        lambdas = {}

        lambdas['disable_in_gal'] = lambda_factory.basic_lambda(self, "disable_in_gal", SRC_PATH, BASE_PATH,
                                                                REL_SRC_PATH, 60, "Disables accounts in Google GAL", 2)

        lambdas['remove_google_license'] = lambda_factory.basic_lambda(self, "remove_google_license", SRC_PATH,
                                                                       BASE_PATH, REL_SRC_PATH, 60,
                                                                       "Removes google license from user", 2)

        lambdas['remove_delegates'] = lambda_factory.basic_lambda(self, "remove_delegates", SRC_PATH, BASE_PATH,
                                                                  REL_SRC_PATH, 60,
                                                                  "Removes email delegates from gmail account", 2)

        lambdas['remove_google_oauth_tokens'] = (
            lambda_factory.basic_lambda(self, "remove_google_oauth_tokens",
                                        SRC_PATH, BASE_PATH, REL_SRC_PATH, 60,
                                        "Removes all google oauth tokens for a user", 2))

        lambdas['remove_google_asps'] = (
            lambda_factory.basic_lambda(self, "remove_asps", SRC_PATH, BASE_PATH, REL_SRC_PATH, 60,
                                        "Removes all application specific passwords from user account", 2))

        lambdas['remove_ooo_msg'] = (
            lambda_factory.basic_lambda(self, "remove_ooo_msg", SRC_PATH, BASE_PATH, REL_SRC_PATH, 60,
                                        "Replaces current out of office message for HR approved notice", 2))

        lambdas['suspend_google_account'] = lambda_factory.basic_lambda(self, "suspend_google_account", SRC_PATH,
                                                                        BASE_PATH, REL_SRC_PATH, 60,
                                                                        "Suspends user's Google account", 2)

        lambdas['remove_mfa_factors'] = lambda_factory.basic_lambda(self, "remove_mfa_factors", SRC_PATH,
                                                                    BASE_PATH, REL_SRC_PATH, 60,
                                                                    "Removes mfa factors from onelogin account", 2)

        lambdas['force_logout_canvas'] = lambda_factory.basic_lambda(self, "force_logout_canvas", SRC_PATH,
                                                                     BASE_PATH, REL_SRC_PATH, 60,
                                                                     "Forces logout of all sessions to canvas for user",
                                                                     2, environment=force_logout_env)

        lambdas['force_logout_onelogin'] = (
            lambda_factory.basic_lambda(self, "force_logout_onelogin", SRC_PATH, BASE_PATH, REL_SRC_PATH, 60,
                                        "Forces logout of session in onelogin", 2))

        lambdas['force_logout_google'] = (
            lambda_factory.basic_lambda(self, "force_logout_google", SRC_PATH, BASE_PATH, REL_SRC_PATH, 60,
                                        "Forces log out of session in google", 2))

        if environment == 'production':
            bucket_arn = self.cdk_env.get('integration_files_bucket_arn')
            ad_delete_bucket = s3.Bucket.from_bucket_arn(self, 'ad_delete_bucket', bucket_arn)
        else:
            ad_delete_bucket = bucket_init(self, environment)

        ad_delete_queue = sqs.Queue(self, 'ad_delete_queue.fifo',
                                    queue_name='ad_delete_queue.fifo',
                                    content_based_deduplication=True,
                                    receive_message_wait_time=Duration.seconds(20),
                                    visibility_timeout=Duration.seconds(300)
                                    )

        lambdas['ad_delete_sfn_handler'] = (
            lambda_factory.basic_lambda(self, 'ad_delete_sfn_handler', SRC_PATH, BASE_PATH, REL_SRC_PATH, 60,
                                        "Checks delete state and processes recorsd for deletion", 0,
                                        environment={
                                            'bucket_arn': ad_delete_bucket.bucket_arn,
                                            'bucket_name': ad_delete_bucket.bucket_name,
                                            'queue_url': ad_delete_queue.queue_url,
                                        })
        )

        lambdas['ad_delete_bucket_writer'] = (
            lambda_factory.basic_lambda(self, 'ad_delete_bucket_writer', SRC_PATH, BASE_PATH, REL_SRC_PATH, 60,
                                        'AD delete bucket writer.', 2, environment={
                    'queue_url': ad_delete_queue.queue_url,
                    'bucket_name': ad_delete_bucket.bucket_name
                },
                                        reserved_concurrent_executions=1
                                        )
        )

        ad_delete_queue.grant_send_messages(lambdas['ad_delete_sfn_handler'])
        ad_delete_queue.grant_consume_messages(lambdas['ad_delete_bucket_writer'])
        ad_delete_bucket.grant_read_write(lambdas['ad_delete_bucket_writer'])

        # Give lambda 'GetItem' permission for core stack's 'EventState' db
        event_table.grant_read_data(lambdas['ad_delete_sfn_handler'])

        # Step function
        ad_delete_workflow = ad_delete_sfn_workflow(self, lambdas['ad_delete_sfn_handler'])

        lambdas['ad_delete_entry'] = (
            lambda_factory.basic_lambda(self, 'ad_delete_entry', SRC_PATH,
                                        BASE_PATH, REL_SRC_PATH, 60,
                                        "Step function workflow entry point", 0,
                                        environment={'state_machine_arn': ad_delete_workflow.state_machine_arn}
                                        )
        )

        # set sqs queue as lambda trigger
        lambdas['ad_delete_bucket_writer'].add_event_source(
            lambda_event_sources.SqsEventSource(ad_delete_queue)
        )

        # Step function state machine permission
        ad_delete_workflow.grant_start_execution(lambdas['ad_delete_entry'])

        if environment in ['staging', 'dev']:
            sender_email = self.cdk_env.get('sns_failure_topic_email')
            identity = ses.CfnEmailIdentity(
                self, "DevEnvEmailIdentity", email_identity=sender_email
            )

        google_secret = (
            sm.Secret(self, 'userprovisioning-google-api-credentials',
                      secret_name='userprovisioning-google-api-credentials',
                      secret_object_value={
                          "google_json": SecretValue.unsafe_plain_text("update_me"),
                          "subject": SecretValue.unsafe_plain_text("update_me")
                      })
        )

        # Give all lambdas working with Google APIs permission to secret holding Google credentials
        google_secret.grant_read(lambdas['disable_in_gal'])
        google_secret.grant_read(lambdas['remove_google_license'])
        google_secret.grant_read(lambdas['remove_delegates'])
        google_secret.grant_read(lambdas['remove_google_oauth_tokens'])
        google_secret.grant_read(lambdas['remove_google_asps'])
        google_secret.grant_read(lambdas['remove_ooo_msg'])
        google_secret.grant_read(lambdas['suspend_google_account'])
        google_secret.grant_read(lambdas['force_logout_google'])

        onelogin_secret = sm.Secret(
            self,
            "onelogin_management",
            secret_name="onelogin_management",
            secret_object_value={
                "client_id": SecretValue.unsafe_plain_text("<change_me>"),
                "client_secret": SecretValue.unsafe_plain_text("<change_me>"),
            },
            description="OneLogin API Credentials JSON",
        )

        onelogin_secret.grant_read(lambdas['remove_mfa_factors'])
        onelogin_secret.grant_read(lambdas["force_logout_onelogin"])

        canvas_secret = sm.Secret(self, 'account_deprovisioning_canvas', secret_name='account_deprovisioning_canvas',
                                  secret_object_value={
                                      "api_key": SecretValue.unsafe_plain_text("update_me")
                                  })

        canvas_secret.grant_read(lambdas['force_logout_canvas'])

        # Set up step subscriptions
        add_sns_subscription(deprov_topic, lambdas['disable_in_gal'], ["emp-1"])
        add_sns_subscription(deprov_topic, lambdas['remove_google_license'], ["emp-1"])
        add_sns_subscription(deprov_topic, lambdas['remove_delegates'], ["emp-1", "emp-180"])
        add_sns_subscription(deprov_topic, lambdas['remove_google_oauth_tokens'], ["emp-1"])
        add_sns_subscription(deprov_topic, lambdas['remove_google_asps'], ["emp-1"])
        add_sns_subscription(deprov_topic, lambdas['remove_ooo_msg'], ["emp-1"])
        add_sns_subscription(deprov_topic, lambdas['remove_mfa_factors'], ['emp-1'])
        add_sns_subscription(deprov_topic, lambdas['ad_delete_entry'], ['emp-1'])
        add_sns_subscription(deprov_topic, lambdas['suspend_google_account'], ["emp-180"])
        add_sns_subscription(deprov_topic, lambdas['force_logout_canvas'], ["emp-1"])
        add_sns_subscription(deprov_topic, lambdas['force_logout_onelogin'], ["emp-1"])
        add_sns_subscription(deprov_topic, lambdas['force_logout_google'], ["emp-1"])

        # Grant all lambdas permission to publish to failure event processing sns topic
        for function in lambdas.values():
            failure_topic.grant_publish(function)
            sns_kmskey.grant_encrypt_decrypt(function)


def add_sns_subscription(topic: sns.ITopic, function: IFunction, steps: List[str]):
    """
    Adds the specified Lambda function as a subscription to an SNS topic

    :param aws_cdk.aws_sns.ITopic topic:
    :param aws_cdk.aws_lambda.Function function: Lambda function to subscribe to SNS topic
    :param List[str] steps: A list of steps or instructions for the subscription

    :return: None
    """
    steps_and_lambda = steps
    steps_and_lambda.append(function.function_name)
    topic.add_subscription(subscriptions.LambdaSubscription(
        function,
        filter_policy={
            "step": sns.SubscriptionFilter.string_filter(allowlist=steps_and_lambda)
        }
    ))
