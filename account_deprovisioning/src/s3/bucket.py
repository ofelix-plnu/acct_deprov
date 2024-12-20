from aws_cdk import Stack, Tags, aws_s3 as s3
import os


def bucket_init(stack: Stack, environment):
    """
    Instantiate a bucket with the provided stack.

    :param stack: The AWS CDK stack in which to create the bucket.
    :type stack: aws_cdk.Stack
    :param environment:

    :return: An instance of the created S3 bucket.
    :rtype: s3.Bucket
    """
    # S3 bucket

    bucket = s3.Bucket(
        stack,
        "account-deprovisioning.bucket",
        bucket_name=f"account-deprovisioning.bucket.{environment}",
        public_read_access=False,
        block_public_access=s3.BlockPublicAccess(
            block_public_acls=True,
            block_public_policy=True,
            ignore_public_acls=True,
            restrict_public_buckets=True,
        ),
        versioned=False,
        encryption=s3.BucketEncryption.S3_MANAGED,
    )

    Tags.of(bucket).add("plnu:dr:type", "no-backup")

    return bucket
