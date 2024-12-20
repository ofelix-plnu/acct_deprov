from aws_cdk import (
    Stack,
    Tags,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)

from aws_cdk.aws_lambda import (
    IFunction
)


def ad_delete_sfn_workflow(stack: Stack, function: IFunction):
    """
    Creates an AWS Step Functions state machine for managing account suspension and deletion.

    :param stack: The AWS CDK stack in which to create the CDN resources
    :type stack: aws_cdk.core.Stack

    :param function: The Lambda function used in the state machine.
    :type function: IFunction

    :return: The AWS Step Functions state machine for account management.
    :rtype: sfn.StateMachine
    """

    # first run
    ad_delete_day_one = tasks.LambdaInvoke(
        stack,
        "ad_delete_day_one",
        lambda_function=function,
        payload_response_only=True,
        retry_on_service_exceptions=True
    )

    # 180 day wait
    wait = sfn.Wait(stack, '180_day_wait', time=sfn.WaitTime.seconds_path('$.waitSeconds'))

    # second run
    ad_delete_day_180 = tasks.LambdaInvoke(
        stack,
        "ad_delete_day_180",
        lambda_function=function,
        payload_response_only=True,
        retry_on_service_exceptions=True
    )

    # this is creating the structure of the state machine.

    workflow_definition = ad_delete_day_one.next(wait).next(ad_delete_day_180)

    sfn_sm = sfn.StateMachine(
        stack,
        "ad_delete_workflow",
        definition_body=sfn.DefinitionBody.from_chainable(workflow_definition)
    )

    Tags.of(sfn_sm).add("plnu:dr:type", "no-backup")

    return sfn_sm
