# Account Deprovisioning

This process simplifies the management of employee terminations by automating tasks involved in the decommissioning process. It ensures the removal of access and permissions, facilitates delegation to relevant mangers, and automates these actions on a schedule, allowing HR and IT departments to react to changes and errors. The application is written in Python and built on AWS using the AWS CDK (Cloud Development Kit).

### Features:
* Access Management - Manages user access by removing licenses, OAuth tokens and multi-factor authentication factors.
* Session management - Logs users out from various services.
* Delegation - Removes delegated access and adds access to managers where necessary.
* Account Suspensions - Suspends user accounts to prevent unauthorized access.
* Data Forwarding - Integrates with other systems for additional deprovisioning workflows.


This app consists of two main sections: the Actions Stack and the Core Stack. The Actions Stack, as described above, 
handles the employee termination process by automating tasks involved in the decommissioning process. The Core Stack serves as the engine driving these processes. 

The Core Stack is structured around three key scenarios: the first involves workflows without failure, the second are 
workflows with failed attempts and successful retries, and the third entails notifying operators after reaching the maximum retry limit for manual intervention. 

The core flow of the application begins with an API Gateway trigger initiating the creation of user records in a DynamoDB table. These records, contain user information and details about their current and upcoming steps. A scheduled event runs nightly to identify records with upcoming steps and sends notifications to a processing queue. This queue triggers actions to update the user records based on their current step. Then, the system executes tasks associated with the user's current step. In case of errors during task execution, the system retries failed tasks up to three times. If the maximum retry limit is reached without success, the system removes failure states from the user records and notifies the app's operator for manual intervention. 

## AWS Cloud Development Kit Library

The AWS CDK construct library provides APIs to define your CDK application and add CDK constructs to the application. It allows you to define and set up infrastructure as code, using familiar programming languages like Python.

Before deploying, you need to have AWS CDK installed and configured properly. For a detailed getting started guide, follow steps outlined in [this repository](https://github.com/russomi-labs/aws-cdk-python/blob/master/README.md) and for in depth information about concepts and specific resources see the [API reference](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-construct-library.html). 


To ensure a clean and isolated environment for, it's recommended to create a virtual environment. Follow the steps below to set up yours up. 


**Windows:**

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

**virtualenv on MacOS and Linux:**

```
$ python -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```


To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * **`cdk ls` -** list all stacks in the app
 * **`cdk synth` -** emits the synthesized CloudFormation template
 * **`cdk deploy` -** deploy this stack to your default AWS account/region
 * **`cdk diff` -** compare deployed stack with current state
 * **`cdk docs` -** open CDK documentation

## CI/CD with Bitbucket Pipelines

This project uses Bitbucket pipelines to manage Continuous Integration and Deployment (CI/CD) processes. This CI/CD pipeline manages the application update, static web pages and s3 bucket content uploads, Lambda functions, synthesis and both development and production environment deployments. You can edit the **`bitbucket-pipelines.yml`** file in this repo's root to manage the pipeline's behavior. 

To make updates or fix issues, ensure your CDK project and environment are set up. Make the necessary changes and commit them to the remote repository. This will automatically trigger the pipeline workflow to manage the rest. The pipeline will take care of synthesizing and deploying your changes to the development environment. From there, the change will be reviewed and manually deployed into the production environment. 
