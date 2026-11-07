# ☁️ AWS CDK Deployment Guide

This document outlines the AWS CDK infrastructure setup for the Richmond Storyline Generator, including all necessary AWS services and their configuration.

---

## 🏗️ Infrastructure Overview

The Richmond Storyline Generator uses a serverless architecture built on AWS CDK, providing scalability, cost-effectiveness, and ease of deployment.

### Core AWS Services
- **Lambda Functions**: Serverless compute for story generation and orchestration
- **API Gateway**: RESTful API endpoints for the conversational interface
- **DynamoDB**: Session state management and conversation history
- **S3**: Audio file storage and story asset management
- **Bedrock**: LLM integration (Claude, Nova)
- **Pinecone**: Vector search for Richmond context retrieval
- **CloudFront**: CDN for fast content delivery

---

## 📁 CDK Project Structure

```
storygen/
├── cdk/
│   ├── app.py                    # CDK app entry point
│   ├── cdk.json                  # CDK configuration
│   ├── requirements.txt          # CDK dependencies
│   └── storygen_stack/
│       ├── __init__.py
│       ├── storygen_stack.py     # Main stack definition
│       ├── config.py             # Configuration constants
│       └── constructs/
│           ├── __init__.py
│           ├── api_construct.py  # API Gateway setup
│           ├── storage_construct.py  # S3 and DynamoDB setup
│           └── lambda_construct.py   # Lambda functions setup
├── lambdas/
│   ├── whisper_transcription/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── session_orchestrator/
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── story_generator/
│       ├── handler.py
│       └── requirements.txt
└── infrastructure/
    ├── iam_policies/
    └── environment_variables/
```

---

## 🚀 CDK Stack Implementation

### Main Stack Definition

```python
# cdk/storygen_stack/storygen_stack.py
from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_iam as iam,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    Duration,
    RemovalPolicy,
)
from constructs import Construct

class StoryGenStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Storage Resources
        self.storage_bucket = self._create_storage_bucket()
        self.session_table = self._create_session_table()
        
        # Lambda Functions
        self.whisper_function = self._create_whisper_function()
        self.orchestrator_function = self._create_orchestrator_function()
        self.story_generator_function = self._create_story_generator_function()
        
        # API Gateway
        self.api = self._create_api_gateway()
        
        # CloudFront Distribution
        self.cloudfront = self._create_cloudfront_distribution()
        
        # Permissions and Policies
        self._setup_permissions()

    def _create_storage_bucket(self):
        """Create S3 bucket for audio and story assets"""
        bucket = s3.Bucket(
            self, "StoryGenAssets",
            bucket_name=f"storygen-assets-{self.account}",
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="CleanupTempFiles",
                    prefix="temp/",
                    expiration=Duration.days(7)
                )
            ]
        )
        return bucket

    def _create_session_table(self):
        """Create DynamoDB table for session management"""
        table = dynamodb.Table(
            self, "SessionTable",
            table_name="storygen-sessions",
            partition_key=dynamodb.Attribute(
                name="session_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )
        
        # Add GSI for user sessions
        table.add_global_secondary_index(
            index_name="UserSessions",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.STRING
            )
        )
        
        return table

    def _create_whisper_function(self):
        """Create Lambda function for audio transcription"""
        function = _lambda.Function(
            self, "WhisperTranscription",
            function_name="storygen-whisper-transcription",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("lambdas/whisper_transcription"),
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment={
                "BUCKET_NAME": self.storage_bucket.bucket_name,
                "OPENAI_API_KEY": "{{resolve:secretsmanager:openai-api-key}}"
            }
        )
        return function

    def _create_orchestrator_function(self):
        """Create Lambda function for conversation orchestration"""
        function = _lambda.Function(
            self, "SessionOrchestrator",
            function_name="storygen-session-orchestrator",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("lambdas/session_orchestrator"),
            timeout=Duration.minutes(3),
            memory_size=512,
            environment={
                "TABLE_NAME": self.session_table.table_name,
                "BUCKET_NAME": self.storage_bucket.bucket_name,
                "WHISPER_FUNCTION": self.whisper_function.function_name,
                "STORY_GENERATOR_FUNCTION": self.story_generator_function.function_name
            }
        )
        return function

    def _create_story_generator_function(self):
        """Create Lambda function for final story generation"""
        function = _lambda.Function(
            self, "StoryGenerator",
            function_name="storygen-story-generator",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("lambdas/story_generator"),
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment={
                "TABLE_NAME": self.session_table.table_name,
                "BUCKET_NAME": self.storage_bucket.bucket_name,
                "PINECONE_API_KEY": "{{resolve:secretsmanager:pinecone-api-key}}",
                "AWS_REGION": "us-east-1"
            }
        )
        return function

    def _create_api_gateway(self):
        """Create API Gateway with REST endpoints"""
        api = apigateway.RestApi(
            self, "StoryGenAPI",
            rest_api_name="Richmond Storyline Generator API",
            description="API for conversational story generation",
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,
                throttling_burst_limit=200
            ),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["*"],
                allow_methods=["GET", "POST", "PUT", "DELETE"],
                allow_headers=["*"]
            )
        )

        # Story endpoints
        story_resource = api.root.add_resource("story")
        story_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.orchestrator_function),
            authorization_type=apigateway.AuthorizationType.NONE
        )

        # Session endpoints
        session_resource = api.root.add_resource("session")
        session_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.orchestrator_function)
        )

        return api

    def _create_cloudfront_distribution(self):
        """Create CloudFront distribution for S3 content"""
        distribution = cloudfront.Distribution(
            self, "StoryGenCDN",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(self.storage_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED
            ),
            additional_behaviors={
                "/stories/*": cloudfront.BehaviorOptions(
                    origin=origins.S3Origin(self.storage_bucket),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED
                )
            }
        )
        return distribution

    def _setup_permissions(self):
        """Setup IAM permissions and policies"""
        # Grant S3 access to Lambda functions
        self.storage_bucket.grant_read_write(self.whisper_function)
        self.storage_bucket.grant_read_write(self.orchestrator_function)
        self.storage_bucket.grant_read_write(self.story_generator_function)

        # Grant DynamoDB access
        self.session_table.grant_read_write_data(self.orchestrator_function)
        self.session_table.grant_read_write_data(self.story_generator_function)

        # Grant Lambda invoke permissions
        self.whisper_function.grant_invoke(self.orchestrator_function)
        self.story_generator_function.grant_invoke(self.orchestrator_function)

        # Bedrock permissions
        bedrock_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            resources=["*"]
        )
        
        self.orchestrator_function.add_to_role_policy(bedrock_policy)
        self.story_generator_function.add_to_role_policy(bedrock_policy)

        # Secrets Manager permissions
        secrets_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["secretsmanager:GetSecretValue"],
            resources=["*"]
        )
        
        self.whisper_function.add_to_role_policy(secrets_policy)
        self.orchestrator_function.add_to_role_policy(secrets_policy)
        self.story_generator_function.add_to_role_policy(secrets_policy)
```

---

## 🔧 Configuration

### CDK Configuration

```json
// cdk/cdk.json
{
  "app": "python app.py",
  "watch": {
    "include": [
      "**"
    ],
    "exclude": [
      "README.md",
      "cdk*.json",
      "requirements*.txt",
      "source/**/*.js",
      "source/**/*.d.ts"
    ]
  },
  "context": {
    "@aws-cdk/aws-lambda:recognizeLayerVersion": true,
    "@aws-cdk/core:checkSecretUsage": true,
    "@aws-cdk/core:target-partitions": [
      "aws",
      "aws-cn"
    ],
    "@aws-cdk-containers/ecs-service-extensions:enableDefaultLogDriver": true,
    "@aws-cdk/aws-ec2:uniqueImdsv2TemplateName": true,
    "@aws-cdk/aws-ecs:arnFormatIncludesClusterName": true,
    "@aws-cdk/aws-iam:minimizePolicies": true,
    "@aws-cdk/core:validateSnapshotRemovalPolicy": true,
    "@aws-cdk/aws-codepipeline:crossAccountKeyAliasStackSafeResourceName": true,
    "@aws-cdk/aws-s3:createDefaultLoggingPolicy": true,
    "@aws-cdk/aws-sns-subscriptions:restrictSqsDescryption": true,
    "@aws-cdk/aws-apigateway:disableCloudWatchRole": true,
    "@aws-cdk/core:enablePartitionLiterals": true,
    "@aws-cdk/aws-events:eventsTargetQueueSameAccount": true,
    "@aws-cdk/aws-iam:standardizedServicePrincipals": true,
    "@aws-cdk/aws-ecs:disableExplicitDeploymentControllerForCircuitBreaker": true,
    "@aws-cdk/aws-iam:importedRoleStackSafeDefaultPolicyName": true,
    "@aws-cdk/aws-s3:serverAccessLogsUseBucketPolicy": true,
    "@aws-cdk/aws-route53-patters:useCertificate": true,
    "@aws-cdk/customresources:installLatestAwsSdkDefault": false,
    "@aws-cdk/aws-rds:databaseProxyUniqueResourceName": true,
    "@aws-cdk/aws-codedeploy:removeAlarmsFromDeploymentGroup": true,
    "@aws-cdk/aws-apigateway:authorizerChangeDeploymentLogicalId": true,
    "@aws-cdk/aws-ec2:launchTemplateDefaultUserData": true,
    "@aws-cdk/aws-secretsmanager:useAttachedSecretResourcePolicyForSecretTargetAttachments": true,
    "@aws-cdk/aws-redshift:columnId": true,
    "@aws-cdk/aws-stepfunctions-tasks:enableLoggingConfiguration": true,
    "@aws-cdk/aws-ec2:restrictDefaultSecurityGroup": true,
    "@aws-cdk/aws-apigateway:requestValidatorUniqueId": true,
    "@aws-cdk/aws-kms:aliasNameRef": true,
    "@aws-cdk/aws-autoscaling:generateLaunchTemplateInsteadOfLaunchConfig": true,
    "@aws-cdk/core:includePrefixInUniqueNameGeneration": true,
    "@aws-cdk/aws-efs:denyAnonymousAccess": true,
    "@aws-cdk/aws-opensearchservice:enableOpensearchMultiAzWithStandby": true,
    "@aws-cdk/aws-lambda:useLatestRuntimeVersion": true,
    "@aws-cdk/aws-efs:mountTargetOrderInsensitiveLogicalId": true,
    "@aws-cdk/aws-rds:auroraClusterChangeScopeOfInstanceParameterGroupWithEachParameters": true,
    "@aws-cdk/aws-appsync:useArnForSourceApiAssociationIdentifier": true,
    "@aws-cdk/aws-rds:preventRenderingDeprecatedCredentials": true,
    "@aws-cdk/aws-codepipeline-actions:useNewDefaultBranchForSourceAction": true,
    "@aws-cdk/aws-ec2:uniqueImdsv2TemplateName": true,
    "@aws-cdk/aws-iam:managedPoliciesUseNameForArn": true,
    "@aws-cdk/aws-ecs:arnFormatIncludesClusterName": true,
    "@aws-cdk/aws-iam:importedRoleStackSafeDefaultPolicyName": true,
    "@aws-cdk/aws-s3:serverAccessLogsUseBucketPolicy": true,
    "@aws-cdk/aws-route53-patters:useCertificate": true,
    "@aws-cdk/customresources:installLatestAwsSdkDefault": false,
    "@aws-cdk/aws-rds:databaseProxyUniqueResourceName": true,
    "@aws-cdk/aws-codedeploy:removeAlarmsFromDeploymentGroup": true,
    "@aws-cdk/aws-apigateway:authorizerChangeDeploymentLogicalId": true,
    "@aws-cdk/aws-ec2:launchTemplateDefaultUserData": true,
    "@aws-cdk/aws-secretsmanager:useAttachedSecretResourcePolicyForSecretTargetAttachments": true,
    "@aws-cdk/aws-redshift:columnId": true,
    "@aws-cdk/aws-stepfunctions-tasks:enableLoggingConfiguration": true,
    "@aws-cdk/aws-ec2:restrictDefaultSecurityGroup": true,
    "@aws-cdk/aws-apigateway:requestValidatorUniqueId": true,
    "@aws-cdk/aws-kms:aliasNameRef": true,
    "@aws-cdk/aws-autoscaling:generateLaunchTemplateInsteadOfLaunchConfig": true,
    "@aws-cdk/core:includePrefixInUniqueNameGeneration": true,
    "@aws-cdk/aws-efs:denyAnonymousAccess": true,
    "@aws-cdk/aws-opensearchservice:enableOpensearchMultiAzWithStandby": true,
    "@aws-cdk/aws-lambda:useLatestRuntimeVersion": true,
    "@aws-cdk/aws-efs:mountTargetOrderInsensitiveLogicalId": true,
    "@aws-cdk/aws-rds:auroraClusterChangeScopeOfInstanceParameterGroupWithEachParameters": true,
    "@aws-cdk/aws-appsync:useArnForSourceApiAssociationIdentifier": true,
    "@aws-cdk/aws-rds:preventRenderingDeprecatedCredentials": true,
    "@aws-cdk/aws-codepipeline-actions:useNewDefaultBranchForSourceAction": true
  }
}
```

### Environment Variables

```python
# cdk/storygen_stack/config.py
import os

class Config:
    # Stack Configuration
    STACK_NAME = "RichmondStorylineGenerator"
    STACK_DESCRIPTION = "Richmond Storyline Generator - Conversational AI Story Platform"
    
    # Environment
    ENVIRONMENT = os.getenv("CDK_ENVIRONMENT", "dev")
    REGION = os.getenv("CDK_REGION", "us-east-1")
    
    # Resource Names
    BUCKET_NAME = f"storygen-assets-{ENVIRONMENT}"
    TABLE_NAME = f"storygen-sessions-{ENVIRONMENT}"
    API_NAME = f"storygen-api-{ENVIRONMENT}"
    
    # Lambda Configuration
    LAMBDA_TIMEOUT = 300  # 5 minutes
    LAMBDA_MEMORY = 1024  # 1GB
    
    # API Configuration
    API_THROTTLE_RATE = 100
    API_THROTTLE_BURST = 200
    
    # Tags
    TAGS = {
        "Project": "RichmondStorylineGenerator",
        "Environment": ENVIRONMENT,
        "ManagedBy": "CDK"
    }
```

---

## 🚀 Deployment

### Prerequisites

1. **AWS CLI Configuration**
```bash
aws configure
```

2. **CDK Bootstrap**
```bash
cd cdk
cdk bootstrap
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### Deployment Commands

```bash
# Deploy the stack
cdk deploy

# Deploy with specific parameters
cdk deploy --parameters Environment=prod

# Destroy the stack
cdk destroy

# View stack differences
cdk diff

# Synthesize CloudFormation template
cdk synth
```

### Secrets Management

Store sensitive configuration in AWS Secrets Manager:

```bash
# Store OpenAI API key
aws secretsmanager create-secret \
    --name "openai-api-key" \
    --secret-string "your-openai-api-key"

# Store Pinecone API key
aws secretsmanager create-secret \
    --name "pinecone-api-key" \
    --secret-string "your-pinecone-api-key"
```

---

## 📊 Monitoring & Logging

### CloudWatch Logs
- Lambda function logs are automatically captured
- Log groups follow the pattern: `/aws/lambda/storygen-*`
- Log retention: 30 days

### CloudWatch Metrics
- Lambda invocation metrics
- API Gateway request metrics
- DynamoDB read/write metrics
- S3 storage metrics

### X-Ray Tracing
Enable X-Ray tracing for distributed tracing:

```python
# Add to Lambda functions
import aws_xray_sdk.core as xray
xray.patch_all()
```

---

## 🔒 Security

### IAM Best Practices
- Principle of least privilege
- Use specific resource ARNs where possible
- Regular access reviews
- Enable CloudTrail for audit logging

### Network Security
- VPC configuration for Lambda functions (if needed)
- Security groups and NACLs
- Private subnets for database access

### Data Protection
- S3 bucket encryption (SSE-S3)
- DynamoDB encryption at rest
- Secrets Manager for sensitive data
- HTTPS-only API endpoints

---

## 💰 Cost Optimization

### Lambda Optimization
- Right-size memory allocation
- Optimize code execution time
- Use provisioned concurrency for consistent workloads

### Storage Optimization
- S3 lifecycle policies for temporary files
- DynamoDB on-demand billing for variable workloads
- CloudFront caching to reduce origin requests

### Monitoring Costs
- Set up billing alerts
- Monitor resource usage
- Regular cost reviews and optimization

---

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd cdk
          pip install -r requirements.txt
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Deploy CDK
        run: |
          cd cdk
          cdk deploy --require-approval never
```

---

## 🧪 Testing

### Unit Tests
```bash
# Run CDK unit tests
cd cdk
python -m pytest tests/

# Run Lambda function tests
cd lambdas/session_orchestrator
python -m pytest tests/
```

### Integration Tests
- Test API endpoints with real data
- Verify Lambda function integration
- Test error handling and edge cases

### Load Testing
- Use tools like Artillery or JMeter
- Test API Gateway throttling
- Monitor performance under load
