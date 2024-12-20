#!/bin/bash

read -p "Enter AWS profile: " profile

read -p "Do you want to perform initial set up or reset? (initial setup/reset): " action

if [[ "$action" == "initial setup" || "$action" == i* ]]; then
  echo "Performing initial setup.."

  aws cloudformation set-stack-policy --stack-name AccountDeprovisioningActionsStack --stack-policy-body file://policies/stack_policy_actions_stack.json --profile $profile --region us-west-2
  aws cloudformation set-stack-policy --stack-name AccountDeprovisioningCoreStack --stack-policy-body file://policies/stack_policy_core_stack.json --profile $profile --region us-west-2
echo "Initial setup complete."
elif [[ "$action" ==  "reset" || "$action" == r* ]]; then
  echo "Performing reset..."

  aws cloudformation set-stack-policy --stack-name AccountDeprovisioningActionsStack --stack-policy-body file://policies/stack_policy_allow_all.json --profile $profile --region us-west-2
  aws cloudformation set-stack-policy --stack-name AccountDeprovisioningCoreStack --stack-policy-body file://policies/stack_policy_allow_all.json --profile $profile --region us-west-2
  echo "..."
  sleep 1
  echo "Reset complete."
else
  echo "Invalid option. Please choose 'initial setup' or 'reset'."
fi