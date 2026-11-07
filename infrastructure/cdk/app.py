#!/usr/bin/env python3
"""
AWS CDK Application for Richmond Storyline Generator
Production-ready infrastructure with auto-scaling, monitoring, and security
"""

import os
from aws_cdk import App, Environment, Tags
from stacks.vpc_stack import VPCStack
from stacks.security_stack import SecurityStack
from stacks.database_stack import DatabaseStack
from stacks.storage_stack import StorageStack
from stacks.compute_stack import ComputeStack
from stacks.monitoring_stack import MonitoringStack
from stacks.cicd_stack import CICDStack
from stacks.cdn_stack import CDNStack

# Environment configuration
env_name = os.environ.get("CDK_ENV", "dev")
account = os.environ.get("CDK_ACCOUNT", os.environ.get("AWS_ACCOUNT_ID"))
region = os.environ.get("CDK_REGION", "us-east-1")

# Create CDK app
app = App()

# Define environment
env = Environment(account=account, region=region)

# Common tags for all resources
common_tags = {
    "Project": "StoryGen",
    "Environment": env_name,
    "ManagedBy": "CDK",
    "CostCenter": "Engineering",
}

# Create stacks
vpc_stack = VPCStack(
    app,
    f"StoryGen-VPC-{env_name}",
    env=env,
    env_name=env_name,
)

security_stack = SecurityStack(
    app,
    f"StoryGen-Security-{env_name}",
    vpc=vpc_stack.vpc,
    env=env,
    env_name=env_name,
)

database_stack = DatabaseStack(
    app,
    f"StoryGen-Database-{env_name}",
    vpc=vpc_stack.vpc,
    security_group=security_stack.database_sg,
    env=env,
    env_name=env_name,
)

storage_stack = StorageStack(
    app,
    f"StoryGen-Storage-{env_name}",
    vpc=vpc_stack.vpc,
    env=env,
    env_name=env_name,
)

compute_stack = ComputeStack(
    app,
    f"StoryGen-Compute-{env_name}",
    vpc=vpc_stack.vpc,
    security_groups={
        "alb": security_stack.alb_sg,
        "app": security_stack.app_sg,
        "cache": security_stack.cache_sg,
    },
    database_table=database_stack.main_table,
    s3_bucket=storage_stack.assets_bucket,
    env=env,
    env_name=env_name,
)

monitoring_stack = MonitoringStack(
    app,
    f"StoryGen-Monitoring-{env_name}",
    cluster=compute_stack.cluster,
    service=compute_stack.service,
    alb=compute_stack.alb,
    env=env,
    env_name=env_name,
)

cdn_stack = CDNStack(
    app,
    f"StoryGen-CDN-{env_name}",
    alb=compute_stack.alb,
    s3_bucket=storage_stack.assets_bucket,
    env=env,
    env_name=env_name,
)

# CI/CD stack only for production
if env_name == "prod":
    cicd_stack = CICDStack(
        app,
        f"StoryGen-CICD-{env_name}",
        env=env,
        env_name=env_name,
    )

# Apply tags to all stacks
for stack in app.node.children:
    for key, value in common_tags.items():
        Tags.of(stack).add(key, value)

# Synthesize
app.synth()