"""Storage Stack for Richmond Storyline Generator"""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_s3 as s3,
    aws_ec2 as ec2,
    CfnOutput,
    Duration,
)
from constructs import Construct


class StorageStack(Stack):
    """Creates S3 buckets for assets, uploads, and backups"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        env_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Assets bucket for static files
        self.assets_bucket = s3.Bucket(
            self,
            "AssetsBucket",
            bucket_name=f"storygen-assets-{env_name}-{self.account}",
            versioned=True if env_name == "prod" else False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN
            if env_name == "prod"
            else RemovalPolicy.DESTROY,
            auto_delete_objects=env_name != "prod",
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    noncurrent_version_expiration=Duration.days(30),
                    enabled=True,
                ),
                s3.LifecycleRule(
                    id="TransitionToIA",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30),
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90),
                        ),
                    ],
                    enabled=env_name == "prod",
                ),
            ],
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                    ],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    max_age=3600,
                )
            ],
        )

        # Uploads bucket for user-generated content
        self.uploads_bucket = s3.Bucket(
            self,
            "UploadsBucket",
            bucket_name=f"storygen-uploads-{env_name}-{self.account}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN
            if env_name == "prod"
            else RemovalPolicy.DESTROY,
            auto_delete_objects=env_name != "prod",
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ExpireTempUploads",
                    prefix="temp/",
                    expiration=Duration.days(1),
                    enabled=True,
                ),
                s3.LifecycleRule(
                    id="ArchiveOldUploads",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(60),
                        ),
                    ],
                    enabled=True,
                ),
            ],
            intelligent_tiering_configurations=[
                s3.IntelligentTieringConfiguration(
                    name="OptimizeCosts",
                    archive_access_tier_time=Duration.days(90),
                    deep_archive_access_tier_time=Duration.days(180),
                )
            ] if env_name == "prod" else None,
        )

        # Backups bucket
        self.backups_bucket = s3.Bucket(
            self,
            "BackupsBucket",
            bucket_name=f"storygen-backups-{env_name}-{self.account}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="TransitionBackups",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(7),
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(30),
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.DEEP_ARCHIVE,
                            transition_after=Duration.days(90),
                        ),
                    ],
                    enabled=True,
                ),
            ],
        )

        # Logs bucket for centralized logging
        self.logs_bucket = s3.Bucket(
            self,
            "LogsBucket",
            bucket_name=f"storygen-logs-{env_name}-{self.account}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldLogs",
                    expiration=Duration.days(90 if env_name == "prod" else 30),
                    enabled=True,
                ),
                s3.LifecycleRule(
                    id="TransitionLogs",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30),
                        ),
                    ],
                    enabled=env_name == "prod",
                ),
            ],
        )

        # Enable S3 access logging
        self.assets_bucket.add_to_resource_policy(
            statement=s3.BucketPolicy(
                actions=["s3:GetBucketAcl"],
                principals=[s3.ServicePrincipal("logging.s3.amazonaws.com")],
                resources=[self.logs_bucket.bucket_arn],
            ).statement_json
        )

        # Outputs
        CfnOutput(
            self,
            "AssetsBucketName",
            value=self.assets_bucket.bucket_name,
            export_name=f"{env_name}-assets-bucket-name",
        )

        CfnOutput(
            self,
            "UploadsBucketName",
            value=self.uploads_bucket.bucket_name,
            export_name=f"{env_name}-uploads-bucket-name",
        )

        CfnOutput(
            self,
            "BackupsBucketName",
            value=self.backups_bucket.bucket_name,
            export_name=f"{env_name}-backups-bucket-name",
        )

        CfnOutput(
            self,
            "LogsBucketName",
            value=self.logs_bucket.bucket_name,
            export_name=f"{env_name}-logs-bucket-name",
        )