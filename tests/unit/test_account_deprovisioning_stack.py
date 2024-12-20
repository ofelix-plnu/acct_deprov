import aws_cdk as core
import aws_cdk.assertions as assertions

from account_deprovisioning.account_deprovisioning_core_stack import AccountDeprovisioningStack

# example tests. To run these tests, uncomment this file along with the example
# resource in account_deprovisioning/account_deprovisioning_core_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AccountDeprovisioningStack(app, "account-deprovisioning")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
