"""Database Stack for Richmond Storyline Generator"""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_ec2 as ec2,
    aws_backup as backup,
    CfnOutput,
    Duration,
)
from constructs import Construct


class DatabaseStack(Stack):
    """Creates DynamoDB tables with backup and disaster recovery"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        security_group: ec2.SecurityGroup,
        env_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Main DynamoDB table for stories and sessions
        self.main_table = dynamodb.Table(
            self,
            "MainTable",
            table_name=f"storygen-{env_name}",
            partition_key=dynamodb.Attribute(
                name="pk", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sk", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
            if env_name != "prod"
            else dynamodb.BillingMode.PROVISIONED,
            removal_policy=RemovalPolicy.RETAIN
            if env_name == "prod"
            else RemovalPolicy.DESTROY,
            point_in_time_recovery=True,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        )

        # Production capacity configuration
        if env_name == "prod":
            self.main_table.auto_scale_read_capacity(
                min_capacity=5, max_capacity=1000
            ).scale_on_utilization(target_utilization_percent=70)

            self.main_table.auto_scale_write_capacity(
                min_capacity=5, max_capacity=1000
            ).scale_on_utilization(target_utilization_percent=70)

        # Global Secondary Indexes
        self.main_table.add_global_secondary_index(
            index_name="GSI1",
            partition_key=dynamodb.Attribute(
                name="gsi1pk", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="gsi1sk", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        self.main_table.add_global_secondary_index(
            index_name="GSI2",
            partition_key=dynamodb.Attribute(
                name="userId", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="createdAt", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Session cache table with TTL
        self.session_table = dynamodb.Table(
            self,
            "SessionTable",
            table_name=f"storygen-sessions-{env_name}",
            partition_key=dynamodb.Attribute(
                name="sessionId", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
        )

        # Analytics table for metrics
        self.analytics_table = dynamodb.Table(
            self,
            "AnalyticsTable",
            table_name=f"storygen-analytics-{env_name}",
            partition_key=dynamodb.Attribute(
                name="metricType", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
        )

        # Backup configuration for production
        if env_name == "prod":
            backup_plan = backup.BackupPlan(
                self,
                "BackupPlan",
                backup_plan_name=f"storygen-backup-{env_name}",
                backup_plan_rules=[
                    # Daily backups retained for 30 days
                    backup.BackupPlanRule(
                        backup.BackupPlanRule.daily(),
                        delete_after=Duration.days(30),
                        move_to_cold_storage_after=Duration.days(7),
                    ),
                    # Weekly backups retained for 90 days
                    backup.BackupPlanRule(
                        backup.BackupPlanRule.weekly(),
                        delete_after=Duration.days(90),
                        move_to_cold_storage_after=Duration.days(30),
                    ),
                    # Monthly backups retained for 1 year
                    backup.BackupPlanRule(
                        backup.BackupPlanRule.monthly(),
                        delete_after=Duration.days(365),
                        move_to_cold_storage_after=Duration.days(90),
                    ),
                ],
            )

            # Add tables to backup plan
            backup_plan.add_selection(
                "BackupSelection",
                resources=[
                    backup.BackupResource.from_dynamo_db_table(self.main_table),
                    backup.BackupResource.from_dynamo_db_table(self.analytics_table),
                ],
            )

        # Outputs
        CfnOutput(
            self,
            "MainTableName",
            value=self.main_table.table_name,
            export_name=f"{env_name}-main-table-name",
        )

        CfnOutput(
            self,
            "MainTableArn",
            value=self.main_table.table_arn,
            export_name=f"{env_name}-main-table-arn",
        )

        CfnOutput(
            self,
            "SessionTableName",
            value=self.session_table.table_name,
            export_name=f"{env_name}-session-table-name",
        )

        CfnOutput(
            self,
            "AnalyticsTableName",
            value=self.analytics_table.table_name,
            export_name=f"{env_name}-analytics-table-name",
        )