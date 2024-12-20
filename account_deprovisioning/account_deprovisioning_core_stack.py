import os
import json

from aws_cdk import (
    Duration,
    aws_lambda as _lambda,
    aws_sns as sns,
    aws_iam as iam,
    aws_sns_subscriptions as sns_sub,
    aws_dynamodb as ddb,
    aws_ssm as ssm,
    aws_kms as kms,
    aws_apigateway as apigw,
    aws_events as events,
    aws_events_targets as etargets,
    aws_ses as ses,
)
from constructs import Construct

from cdk_utils.cdk_utils import PLNUStack, PLNULambda

state_parameter_file = 'state_params.json'

BASE_PATH = os.path.join(os.path.dirname(__file__), "..")
REL_SRC_PATH = os.path.join("src", "core")
SRC_PATH = os.path.join(BASE_PATH, REL_SRC_PATH)
ENVIRONMENT_CONFIG_VAR = 'config'

CORE_API_ROOT = "core"
CORE_API_ACCOUNT = "account"


class AccountDeprovisioningCoreStack(PLNUStack):
    """
    AWS CDK Stack for the Account Deprovisioning Core Stack

    :param scope: The construct to which this stack belongs
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.sns_kmskey = kms.Key.from_lookup(self, "DefaultKeyLookup", alias_name="alias/aws/sns")

        self.deprov_topic = sns.Topic(self, "acct_deprovisioning_actions", master_key=self.sns_kmskey)

        self.event_table = self.build_event_table()

        deprov_topic_env = {"deprov_topic_arn": self.deprov_topic.topic_arn}

        default_env = {'deploy_environment': self.cdk_env.get('environment'),
                       'log_level': self.cdk_env.get('log_level')}

        lam_fac = PLNULambda(default_env=default_env)

        records_to_process_lambda = \
            lam_fac.basic_lambda(self, "get_records_to_process", SRC_PATH, BASE_PATH, REL_SRC_PATH, 60,
                                 "Gets records that are ready to be processed, puts them in the processing SNS topic",
                                 0, deprov_topic_env)

        self.sns_kmskey.grant_encrypt_decrypt(records_to_process_lambda)
        self.deprov_topic.grant_publish(records_to_process_lambda)
        self.event_table.grant_read_data(records_to_process_lambda)

        advance_step_lambda = \
            lam_fac.basic_lambda(self, "advance_step", SRC_PATH, BASE_PATH, REL_SRC_PATH, 60,
                                 "Updates a state record to the next step and next trigger time", 2)

        self.deprov_topic.add_subscription(
            sns_sub.LambdaSubscription(
                advance_step_lambda,
                filter_policy={"step": sns.SubscriptionFilter.string_filter(match_prefixes=["emp", "stu"])}
            )
        )
        self.event_table.grant_read_write_data(advance_step_lambda)

        insert_record_lambda = \
            lam_fac.basic_lambda(self, "insert_record", SRC_PATH, BASE_PATH, REL_SRC_PATH, 60,
                                 "Inserts initial record for a user to decommission", 2)

        self.event_table.grant_read_write_data(insert_record_lambda)
        api_gw = self.core_api(self.cdk_env)
        # self.api_gw_lambda_integration(insert_record_lambda, api_gw=api_gw)

        delete_record_lambda = \
            lam_fac.basic_lambda(self, "delete_record", SRC_PATH, BASE_PATH, REL_SRC_PATH, 60,
                                 "Removes user's decommission record. Sends re-enrollment notification for students.",
                                 0)

        self.event_table.grant_read_write_data(delete_record_lambda)
        self.api_gw_lambda_integration(insert_record_lambda, delete_record_lambda, api_gw=api_gw)

        step_processing_lambdas = [advance_step_lambda, records_to_process_lambda]

        self.build_state_machine_steps(step_processing_lambdas)

        process_failed_lambda = lam_fac.basic_lambda(
            self, "retry_failed_lambdas", SRC_PATH, BASE_PATH, REL_SRC_PATH, 60,
            "Checks for lambdas that failed with a retry expectation, requeues them for processing",
            0, deprov_topic_env)

        self.event_table.grant_read_data(process_failed_lambda)
        self.deprov_topic.grant_publish(process_failed_lambda)

        flag_failed_lambda_retry = lam_fac.basic_lambda(self, "flag_failed_lambda_retry", SRC_PATH, BASE_PATH,
                                                        REL_SRC_PATH, 60, "Flags failed lambda for retry",
                                                        0)

        self.event_table.grant_read_write_data(flag_failed_lambda_retry)

        process_terminal_failure = lam_fac.basic_lambda(self, "process_terminal_failure", SRC_PATH, BASE_PATH,
                                                        REL_SRC_PATH, 60, "Notifies about unrecoverable failures",
                                                        0)

        self.event_table.grant_read_write_data(process_terminal_failure)

        remove_failure_state = lam_fac.basic_lambda(self, "remove_failure_state", SRC_PATH, BASE_PATH,
                                                    REL_SRC_PATH, 60, "Removes retry flag for a given lambda and user",
                                                    0)

        notify_env = {'sns_failure_topic_email': self.cdk_env.get('sns_failure_topic_email'),
                      'email_arn': self.cdk_env.get('email_arn'),
                      'from_email': self.cdk_env.get('from_email')
                      }

        notify_email_terminal_lambda = lam_fac.basic_lambda(self, "notify_email_terminal_lambda", SRC_PATH,
                                                            BASE_PATH, REL_SRC_PATH, 60,
                                                            "Sends email notification if lambda failed "
                                                            "and will not be retried", 0,
                                                            environment=notify_env)

        self.grant_lambda_ses_access(notify_email_terminal_lambda)

        self.event_table.grant_read_write_data(remove_failure_state)

        failure_handler_info = [
            {"lambda": flag_failed_lambda_retry, "allowlist": ['retry']},
            {"lambda": process_terminal_failure, "allowlist": ['terminal']},
            {"lambda": remove_failure_state, "allowlist": ['clear']},
            {"lambda": notify_email_terminal_lambda, "allowlist": ['terminal']}
        ]

        self.failure_topic = self.build_failure_topic(self.sns_kmskey, failure_handler_info)

        process_records_rule = self.build_process_cron_rule()
        process_records_rule.add_target(etargets.LambdaFunction(records_to_process_lambda))

        retry_records_rule = self.build_retry_cron_rule()
        retry_records_rule.add_target(etargets.LambdaFunction(process_failed_lambda))

        self.deprov_topic.add_subscription(sns_sub.LambdaSubscription(
            delete_record_lambda,
            filter_policy={
                "step": sns.SubscriptionFilter.string_filter(allowlist=['end'])
            }
        ))

    def build_state_machine_steps(self, lambdas: list[_lambda.Function]):
        """
        Grants SSM parameter retrieval permissions, creates parameters from a JSON file, and provides read access to
        Lambdas

        :param list[_lambda.Function] lambdas: List of Lambda functions
        """

        for deprovisioning_lambda in lambdas:
            deprovisioning_lambda.add_to_role_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ssm:GetParametersByPath",
                    ],
                    resources=["*"],
                )
            )

        with open(f'parameters/{state_parameter_file}') as f:
            params = f.read()
        params_json = json.loads(params)
        for param in params_json.keys():
            new_param = ssm.StringParameter(self, param, string_value=params_json[param], parameter_name=param)
            for deprovisioning_lambda in lambdas:
                new_param.grant_read(deprovisioning_lambda)

    def build_event_table(self):
        """
        Creates a DynamDB table with two global secondary indexes (next_step-index & has_failed_lambdas-index)

        :return: aws_cdk.aws_dynamodb.Table: The configured DynamoDB table
        """

        table = ddb.Table(self, 'EventState', table_name='EventState',
                          partition_key=ddb.Attribute(name="username", type=ddb.AttributeType.STRING),
                          billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
                          encryption=ddb.TableEncryption.AWS_MANAGED,
                          deletion_protection=True,
                          point_in_time_recovery=True
                          )

        table.add_global_secondary_index(index_name='next_step-index',
                                         partition_key=ddb.Attribute(name="next_step", type=ddb.AttributeType.STRING),
                                         sort_key=ddb.Attribute(name="next_step_date", type=ddb.AttributeType.STRING),
                                         projection_type=ddb.ProjectionType.ALL)

        table.add_global_secondary_index(index_name='has_failed_lambdas-index',
                                         partition_key=ddb.Attribute(name="has_failed_lambdas",
                                                                     type=ddb.AttributeType.STRING))

        return table

    def core_api(self, cdk_env):
        """
        Builds and configures the "core" API Gateway with an inbound API key, usage plan, and needed resources

        :param cdk_env: The environment-specific configuration
        """

        api_gw = apigw.RestApi(
            self,
            "AccountDecommission",
            deploy=True,
            policy=self.build_api_gw_policy(),
            deploy_options=apigw.StageOptions(
                stage_name=cdk_env.get("environment"),
                throttling_burst_limit=100,
                throttling_rate_limit=50,
                tracing_enabled=True
            ),
            endpoint_types=[apigw.EndpointType.REGIONAL]
        )
        wd_inbound_api_key = api_gw.add_api_key(
            "WDAPIKEY", description="API key for requests originating from WD"
        )
        usage_plan = api_gw.add_usage_plan(
            "WDUsagePlan",
            throttle=apigw.ThrottleSettings(burst_limit=20, rate_limit=15)
        )
        usage_plan.add_api_key(wd_inbound_api_key)
        usage_plan.add_api_stage(stage=api_gw.deployment_stage)

        core = api_gw.root.add_resource(CORE_API_ROOT)
        core.add_resource(CORE_API_ACCOUNT)

        return api_gw

    def build_api_gw_policy(self):
        """
        Constructs IAM policy document for use on API Gateway, including handling IP whitelisting

        :return: Security policy for api gateway
        :rtype: aws_cdk.aws_iam.PolicyDocument
        """
        stmt = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["execute-api:Invoke"],
            resources=["execute-api:/*"],
        )

        stmt.add_any_principal()
        stmt.add_condition(
            "IpAddress",
            {
                "aws:SourceIp": [
                    "54.71.89.247/32",
                    "34.200.5.50/32",
                    "44.206.54.134/32",
                    "192.147.249.189/32",
                    "52.36.173.74/32",
                    "52.42.229.224/32",
                    "209.177.165.160/32",
                    "209.177.167.160/32",
                    "209.177.167.164/32",
                    "52.25.19.91/32",
                    "52.42.112.90/32",
                    "44.234.22.80/30",
                    "20.106.79.32/32",
                ]
            },
        )
        return iam.PolicyDocument(statements=[stmt])

    def api_gw_lambda_integration(self, insert_lambda: _lambda.Function, delete_lambda: _lambda.Function,
                                  api_gw: apigw.RestApi):
        """
        Configures API Gateway integration with lambda functions for insert and delete operations

        :param _lambda.Function insert_lambda: Lambda function for data insertion
        :param _lambda.Function delete_lambda: Lambda function for data deletion
        :param api_gw.RestApi api_gw: AWS API Gateway instance to be configured
        """

        insert_record_integration = apigw.LambdaIntegration(
            insert_lambda,
            proxy=False,
            timeout=Duration.seconds(29),
            passthrough_behavior=apigw.PassthroughBehavior.WHEN_NO_MATCH,
            integration_responses=[
                apigw.IntegrationResponse(status_code="200")
            ]
        )

        api_core_resource = api_gw.root.get_resource(CORE_API_ROOT)
        api_account_resource = api_core_resource.get_resource(CORE_API_ACCOUNT)
        api_account_resource.add_method(
            "POST",
            insert_record_integration,
            api_key_required=True,
            method_responses=[
                apigw.MethodResponse(status_code="200")
            ]
        )

        delete_record_integration = apigw.LambdaIntegration(
            delete_lambda,
            proxy=False,
            timeout=Duration.seconds(29),
            passthrough_behavior=apigw.PassthroughBehavior.WHEN_NO_MATCH,
            integration_responses=[
                apigw.IntegrationResponse(status_code="200")]
        )

        api_account_resource.add_method(
            "DELETE",
            delete_record_integration,
            api_key_required=True,
            method_responses=[
                apigw.MethodResponse(status_code="200")
            ]
        )

    def build_failure_topic(self, sns_kmskey, lambdas_info: list[dict]):
        """
        Builds an SNS topic for handling failure notifications and subscribes included Lambda functions

        :param sns_kmskey: KMS key for SNS topic encryption
        :param lambdas_info: List of dictionaries with Lambda functions and associated allowlists for failure types

        :return: Configured SNS topic for failure notifications
        """

        failure_topic = sns.Topic(self, "acct_deprovisioning_failed_actions", master_key=sns_kmskey)

        for lambda_data in lambdas_info:
            failure_topic.add_subscription(sns_sub.LambdaSubscription(
                lambda_data.get("lambda"),
                filter_policy={"failure_type":
                                   sns.SubscriptionFilter.string_filter(allowlist=lambda_data.get("allowlist"))}
            ))

        return failure_topic

    def grant_lambda_ses_access(self, function: _lambda.Function):
        """
        Handles security policy changes to allow a lambda to send email via SES

        :param aws_cdk.aws_lambda.Function function: Lambda function to grant access to SES
        """
        function.add_to_role_policy(
            iam.PolicyStatement(effect=iam.Effect.ALLOW,
                                actions=['ses:SendEmail', 'ses:SendRawEmail', 'ses:SendTemplatedEmail'],
                                resources=['*']
                                )
        )

    def build_process_cron_rule(self) -> events.Rule:
        """
        Builds an EventBridge rule for scheduling getting records eligible for processing,
        with the schedule depending on if it's deployed to prod or somewhere else
        :return events.Rule: Rule object to be used to tie eventbridge schedule to a lambda execution.
        """
        if self.cdk_env.get('environment') == 'production':
            schedule = events.Schedule.cron(minute='0/15')
        else:
            schedule = events.Schedule.cron(minute='0', hour='0')
            # schedule = events.Schedule.cron(minute='0/3')
        return events.Rule(self, "get_records_rule", schedule=schedule)

    def build_retry_cron_rule(self) -> events.Rule:
        """
        Builds and EventBridge rule for scheduling getting records that have lambdas in a retry state,
        with the schedule depending on if it's deployed to prod or somewhere else
        :return events.Rule: Rule object to be used to tie eventbridge schedule to lambda execution
        """

        if self.cdk_env.get('environment') == 'production':
            schedule = events.Schedule.cron(minute='0')
        else:
            schedule = events.Schedule.cron(minute='0', hour='0')

        return events.Rule(self, "get_retry_records_rule", schedule=schedule)
