Usage
=====

category: Account & Group Management/ Account Management

subject: Account Deprovisioning Initial deployment guide

Account Deprovisioning Initial Deployment Guide
-----------------------------------------------

This process simplifies the management of employee terminations by automating tasks involved in the decommissioning process. It ensures the removal of access and permissions, facilitates delegation to relevant mangers, and automates these actions on a schedule, allowing HR and IT departments to react to changes and errors. The application is written in Python and built on AWS using the AWS CDK (Cloud Development Kit).

This guide outlines the initial deployment process for this application. We'll cover deployment steps and the manual configurations needed immediately after the first deployment. This setup is essential to ensure the app functions correctly.

**AWS Cloud Development Kit Library**

The AWS CDK construct library provides APIs to define your CDK application and add CDK constructs to the application.
It allows you to define and set up infrastructure as code, using familiar programming languages like Python.

Before deploying, you need to have AWS CDK installed and configured properly. For a detailed getting started guide,
follow steps outlined in this repository and for in depth information about concepts and specific resources see the
API reference. (https://docs.aws.amazon.com/cdk/api/v2/python/)

Installation
------------

Installation Source: https://bitbucket.org/pointloma/axxount_deprovisioning/src/master/

For installation or updates, clone the repository using the provided installation source. Ensure that you have AWS
CDK installed.

To ensure a clean and isolated environment, it's recommended to create a virtual environment. Follow the steps below to set yours up.


**Windows:**

.. code-block:: console

   % .venv\Scripts\activate.bat

Once the virtualenv is activated, you can install the required dependencies.

.. code-block:: console

   $ pip install -r requirements.txt

At this point you can now synthesize the CloudFormation template for this code.

.. code-block:: console

   $ cdk synth

**virtualenv on MacOS and Linux:**

.. code-block:: console

   $ python -m venv .venv

After the init process completes and the virtualenv is created, you can use the following step to activate your virtualenv.

.. code-block:: console

   $ source .venv/bin/activate


To add additional dependencies, for example other CDK libraries, just add them to your ` setup.py ` file and rerun the ` pip install -r requirements.txt ` command.

Useful Commands
---------------

- **cdk ls** - List all stacks in the app
- **cdk synth** - Emits the synthesized CloudFormation template
- **cdk deploy** - Deploy this stack to your default AWS account/region
- **cdk diff** - Compare deployed stack with current state
- **cdk docs** - Open CDK documentation


Process Steps
-------------

**CI/CD with Bitbucket Pipelines**

This project uses Bitbucket pipelines to manage Continuous Integration and Deployment (CI/CD) processes. This CI/CD pipeline manages the application update, static web pages and s3 bucket content uploads, Lambda functions, synthesis and both development and production environment deployments. You can edit the _**`bitbucket-pipelines.yml`**_ file in this repo's root to manage the pipeline's behavior.

To make updates or fix issues, make sure your CDK project and environment are set up. Make the necessary changes and commit them to the remote repository. This will automatically trigger the pipeline workflow to manage the rest. The pipeline will take care of synthesizing and deploying your changes to the development environment. From there, the change will be reviewed and manually deployed into the production environment.

**Bitbucket Pipelines with OIDC**

This app uses OpenID Connect (OIDC) to make sure only authorized users initiate and oversee pipeline execution. To set up OIDC in your AWS environment, follow steps outlined in this [Atlassian article](https://support.atlassian.com/bitbucket-cloud/docs/deploy-on-aws-using-bitbucket-pipelines-openid-connect/).

The process involves configuring an OIDC identity provider and establishing trust between AWS and the identity provider, enabling secure authentication and authorization in the pipeline.

Manual Configuration
--------------------

Pushing code to the remote repository will handle the majority of the required configurations, but a few specific values need to be manually set:

**AWS Secrets Manager**

The app generates these secrets during deployment (AWS CDK deploy), initializing them with placeholder values that require updating. Find the secret names listed below and update to their actual development or production values. You can access these credentials in [Passwordstate](https://passwords.pointloma.edu/).

**Secret Names:**

**account_deprovisioning_canvas:** Canvas API credentials

**onelogin_management:** OneLogin API credentials

**userprovisioning-google-api-credentials:** Google API credentials

**AWS S3**

Ensure that the IAM role assigned to `plnu-systems-integration-files` S3 bucket in the `Secure Dropbox - 521379338166` account allows list, get, and put operations for the AWS account associated with this app. Files generated by a workflow in the Actions Stack must be directed to this S3 bucket located in this account.

**AWS Stack Policy**

Stack Policies are configurations used to control access to resources within AWS CloudFormation stacks. By default, anyone with stack update permissions can update all of the resources in the stack. Stack Policies prevent stack resources from being unintentionally updated or deleted during a stack update. 

To apply the policy, navigate to the `stack_policies` directory and execute the `set_stack_policy.sh` file. This is a script written to apply stack policies to this project. The script prompts the user to specify their AWS profile and whether they want to perform an initial setup or reset the policy to allow all changes. Based on the user's input, the script sets the AWS profile for the AWS CLI command and executes the necessary commands to apply the appropriate predefined stack policies. This approach ensures that the specified stack policies are enforced consistently across each stack.
