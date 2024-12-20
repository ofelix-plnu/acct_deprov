#!/usr/bin/env python3

import aws_cdk as cdk

from account_deprovisioning.account_deprovisioning_core_stack import AccountDeprovisioningCoreStack
from account_deprovisioning.account_deprovisioning_actions_stack import AccountDeprovisioningActionsStack

app = cdk.App()
config = app.node.try_get_context('config')
if config is None:
    config = 'dev'

config_details = app.node.try_get_context(config)

core = AccountDeprovisioningCoreStack(app, "AccountDeprovisioningCoreStack",
                                      env=cdk.Environment(account=config_details.get('account'),
                                                          region=config_details.get('region'))
                                      )

AccountDeprovisioningActionsStack(app, "AccountDeprovisioningActionsStack",
                                  core.deprov_topic,
                                  core.failure_topic,
                                  core.event_table,
                                  core.sns_kmskey,
                                  env=cdk.Environment(account=config_details.get('account'),
                                                      region=config_details.get('region'))
                                  )

app.synth()
