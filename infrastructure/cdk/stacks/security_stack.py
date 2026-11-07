"""Security Stack for Richmond Storyline Generator"""

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_wafv2 as waf,
    CfnOutput,
)
from constructs import Construct


class SecurityStack(Stack):
    """Creates security groups, WAF rules, and IAM roles"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        env_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ALB Security Group
        self.alb_sg = ec2.SecurityGroup(
            self,
            "ALBSecurityGroup",
            vpc=vpc,
            description="Security group for Application Load Balancer",
            allow_all_outbound=True,
        )

        # Allow HTTP/HTTPS from anywhere
        self.alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP from anywhere",
        )

        self.alb_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from anywhere",
        )

        # Application Security Group
        self.app_sg = ec2.SecurityGroup(
            self,
            "AppSecurityGroup",
            vpc=vpc,
            description="Security group for ECS tasks",
            allow_all_outbound=True,
        )

        # Allow traffic from ALB
        self.app_sg.add_ingress_rule(
            peer=self.alb_sg,
            connection=ec2.Port.tcp(8080),
            description="Allow traffic from ALB",
        )

        # Cache Security Group (Redis)
        self.cache_sg = ec2.SecurityGroup(
            self,
            "CacheSecurityGroup",
            vpc=vpc,
            description="Security group for Redis cache",
            allow_all_outbound=False,
        )

        # Allow Redis traffic from app
        self.cache_sg.add_ingress_rule(
            peer=self.app_sg,
            connection=ec2.Port.tcp(6379),
            description="Allow Redis from app",
        )

        # Database Security Group
        self.database_sg = ec2.SecurityGroup(
            self,
            "DatabaseSecurityGroup",
            vpc=vpc,
            description="Security group for DynamoDB VPC endpoint",
            allow_all_outbound=False,
        )

        # Allow DynamoDB traffic from app
        self.database_sg.add_ingress_rule(
            peer=self.app_sg,
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from app for DynamoDB",
        )

        # ECS Task Execution Role
        self.task_execution_role = iam.Role(
            self,
            "TaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ],
        )

        # Add permissions for Secrets Manager
        self.task_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue",
                    "kms:Decrypt",
                ],
                resources=["*"],
            )
        )

        # ECS Task Role
        self.task_role = iam.Role(
            self,
            "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        # Add permissions for application
        self.task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["*"],
            )
        )

        self.task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchGetItem",
                    "dynamodb:BatchWriteItem",
                ],
                resources=["*"],
            )
        )

        self.task_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",
                ],
                resources=["*"],
            )
        )

        # WAF Web ACL for additional protection
        if env_name == "prod":
            self.web_acl = waf.CfnWebACL(
                self,
                "WebACL",
                scope="REGIONAL",
                default_action=waf.CfnWebACL.DefaultActionProperty(allow={}),
                rules=[
                    # Rate limiting rule
                    waf.CfnWebACL.RuleProperty(
                        name="RateLimitRule",
                        priority=1,
                        statement=waf.CfnWebACL.StatementProperty(
                            rate_based_statement=waf.CfnWebACL.RateBasedStatementProperty(
                                limit=2000,
                                aggregate_key_type="IP",
                            )
                        ),
                        action=waf.CfnWebACL.RuleActionProperty(block={}),
                        visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                            sampled_requests_enabled=True,
                            cloud_watch_metrics_enabled=True,
                            metric_name="RateLimitRule",
                        ),
                    ),
                    # AWS Managed Rules - Common Rule Set
                    waf.CfnWebACL.RuleProperty(
                        name="AWSManagedRulesCommonRuleSet",
                        priority=2,
                        override_action=waf.CfnWebACL.OverrideActionProperty(none={}),
                        statement=waf.CfnWebACL.StatementProperty(
                            managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                                vendor_name="AWS",
                                name="AWSManagedRulesCommonRuleSet",
                            )
                        ),
                        visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                            sampled_requests_enabled=True,
                            cloud_watch_metrics_enabled=True,
                            metric_name="CommonRuleSet",
                        ),
                    ),
                    # AWS Managed Rules - Known Bad Inputs
                    waf.CfnWebACL.RuleProperty(
                        name="AWSManagedRulesKnownBadInputsRuleSet",
                        priority=3,
                        override_action=waf.CfnWebACL.OverrideActionProperty(none={}),
                        statement=waf.CfnWebACL.StatementProperty(
                            managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                                vendor_name="AWS",
                                name="AWSManagedRulesKnownBadInputsRuleSet",
                            )
                        ),
                        visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                            sampled_requests_enabled=True,
                            cloud_watch_metrics_enabled=True,
                            metric_name="KnownBadInputs",
                        ),
                    ),
                ],
                visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                    sampled_requests_enabled=True,
                    cloud_watch_metrics_enabled=True,
                    metric_name="StoryGenWebACL",
                ),
            )

            CfnOutput(
                self,
                "WebACLArn",
                value=self.web_acl.attr_arn,
                export_name=f"{env_name}-waf-arn",
            )

        # Outputs
        CfnOutput(
            self,
            "TaskExecutionRoleArn",
            value=self.task_execution_role.role_arn,
            export_name=f"{env_name}-task-execution-role-arn",
        )

        CfnOutput(
            self,
            "TaskRoleArn",
            value=self.task_role.role_arn,
            export_name=f"{env_name}-task-role-arn",
        )