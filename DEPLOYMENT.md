# Richmond Storyline Generator - Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Richmond Storyline Generator to production using AWS infrastructure. The system is designed for high availability, scalability, and security.

## Architecture Summary

- **Container Orchestration**: AWS ECS Fargate
- **Load Balancing**: Application Load Balancer with WAF
- **Database**: DynamoDB with on-demand scaling
- **Cache**: ElastiCache Redis cluster
- **CDN**: CloudFront with edge caching
- **Monitoring**: CloudWatch, Prometheus, Grafana
- **CI/CD**: GitHub Actions with CodePipeline

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Domain Name** configured in Route53
3. **SSL Certificate** in AWS Certificate Manager
4. **GitHub Repository** with actions enabled
5. **API Keys**:
   - Pinecone API Key
   - OpenAI API Key
   - AWS Access Keys

## Deployment Steps

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/your-org/storygen.git
cd storygen

# Install AWS CDK
npm install -g aws-cdk

# Install Python dependencies
cd infrastructure/cdk
pip install -r requirements.txt

# Configure AWS credentials
aws configure
```

### 2. Create Secrets in AWS Secrets Manager

```bash
# Create API key secrets
aws secretsmanager create-secret \
  --name pinecone-api-key \
  --secret-string '{"key":"your-pinecone-api-key"}'

aws secretsmanager create-secret \
  --name openai-api-key \
  --secret-string '{"key":"your-openai-api-key"}'

# Create GitHub token for CI/CD
aws secretsmanager create-secret \
  --name github-token \
  --secret-string "your-github-personal-access-token"
```

### 3. Initialize DynamoDB Tables

```bash
# Create production tables
python infrastructure/migrations/dynamodb_schema.py \
  --env prod \
  --region us-east-1 \
  --action create
```

### 4. Deploy Infrastructure with CDK

```bash
# Navigate to CDK directory
cd infrastructure/cdk

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy all stacks
export CDK_ENV=prod
export CDK_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_REGION=us-east-1

# Deploy in order
cdk deploy StoryGen-VPC-prod
cdk deploy StoryGen-Security-prod
cdk deploy StoryGen-Database-prod
cdk deploy StoryGen-Storage-prod
cdk deploy StoryGen-Compute-prod
cdk deploy StoryGen-Monitoring-prod
cdk deploy StoryGen-CDN-prod
cdk deploy StoryGen-CICD-prod
```

### 5. Build and Push Initial Docker Image

```bash
# Build Docker image
docker build -t storygen:latest .

# Tag for ECR
export ECR_REPO=$(aws cloudformation describe-stacks \
  --stack-name StoryGen-CICD-prod \
  --query "Stacks[0].Outputs[?OutputKey=='ECRRepositoryURI'].OutputValue" \
  --output text)

docker tag storygen:latest $ECR_REPO:latest

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_REPO

# Push image
docker push $ECR_REPO:latest
```

### 6. Configure GitHub Actions

Create the following secrets in your GitHub repository settings:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `PINECONE_API_KEY`
- `OPENAI_API_KEY`
- `SLACK_WEBHOOK` (for notifications)

### 7. Deploy Application

The CI/CD pipeline will automatically deploy on push to main branch. For manual deployment:

```bash
# Trigger deployment
git tag v1.0.0
git push origin v1.0.0
```

### 8. Configure Monitoring

```bash
# Access Grafana
export GRAFANA_URL=$(aws cloudformation describe-stacks \
  --stack-name StoryGen-Compute-prod \
  --query "Stacks[0].Outputs[?OutputKey=='GrafanaURL'].OutputValue" \
  --output text)

echo "Grafana URL: $GRAFANA_URL"
# Default credentials: admin/admin (change immediately)
```

### 9. Set Up Alerts

Configure SNS subscriptions for critical alerts:

```bash
# Subscribe to alerts
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:YOUR_ACCOUNT:storygen-alerts-prod \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## Post-Deployment Checklist

- [ ] Verify all health checks are passing
- [ ] Test API endpoints through CloudFront
- [ ] Confirm monitoring dashboards are receiving data
- [ ] Verify auto-scaling policies are active
- [ ] Test disaster recovery procedures
- [ ] Configure backup retention policies
- [ ] Set up PagerDuty integration for critical alerts
- [ ] Document runbooks for common operations

## Environment-Specific Configuration

### Development
```bash
export CDK_ENV=dev
# Reduced capacity, no HA
```

### Staging
```bash
export CDK_ENV=staging
# Production-like but smaller scale
```

### Production
```bash
export CDK_ENV=prod
# Full HA, auto-scaling, monitoring
```

## Rollback Procedures

### Automatic Rollback
The deployment pipeline includes automatic rollback on:
- Failed health checks
- Deployment alarms
- Manual intervention

### Manual Rollback
```bash
# Via CodeDeploy
aws deploy stop-deployment \
  --deployment-id <deployment-id> \
  --auto-rollback-enabled

# Via ECS
aws ecs update-service \
  --cluster storygen-prod \
  --service storygen-prod \
  --task-definition <previous-task-def-arn>
```

## Scaling Configuration

### Auto-Scaling Triggers
- **CPU**: Scale out at 70%, scale in at 30%
- **Memory**: Scale out at 80%, scale in at 40%
- **Request Count**: Scale out at 1000 req/target
- **Min Tasks**: 3 (production), 1 (dev/staging)
- **Max Tasks**: 50 (production), 10 (dev/staging)

### Manual Scaling
```bash
# Scale ECS service
aws ecs update-service \
  --cluster storygen-prod \
  --service storygen-prod \
  --desired-count 10

# Scale DynamoDB
aws dynamodb update-table \
  --table-name storygen-prod \
  --provisioned-throughput ReadCapacityUnits=100,WriteCapacityUnits=100
```

## Security Considerations

1. **Network Security**:
   - All traffic flows through WAF
   - VPC with private subnets for compute
   - Security groups with least privilege
   - VPC endpoints for AWS services

2. **Data Security**:
   - Encryption at rest (DynamoDB, S3)
   - Encryption in transit (TLS 1.2+)
   - Secrets in AWS Secrets Manager
   - IAM roles with minimal permissions

3. **Application Security**:
   - Regular dependency updates
   - Container scanning in ECR
   - OWASP Top 10 protections via WAF
   - Rate limiting on API endpoints

## Monitoring and Alerts

### Key Metrics
- **Availability**: Target 99.9%
- **Response Time**: P95 < 3 seconds
- **Error Rate**: < 0.1%
- **CPU/Memory**: < 80%

### Alert Channels
- **Email**: General alerts
- **Slack**: Team notifications
- **PagerDuty**: Critical incidents

### Log Aggregation
- Application logs: CloudWatch Logs
- Access logs: S3 + Athena
- Metrics: CloudWatch + Prometheus

## Cost Optimization

1. **Use Spot Instances** for non-critical workloads
2. **Enable S3 Intelligent-Tiering** for storage
3. **Reserved Capacity** for baseline compute
4. **Auto-scaling** to match demand
5. **CloudFront caching** to reduce origin requests

## Disaster Recovery

### Backup Strategy
- **DynamoDB**: Point-in-time recovery enabled
- **S3**: Cross-region replication for critical data
- **Code**: Multi-region ECR replication
- **Config**: Infrastructure as Code in Git

### RTO/RPO Targets
- **RTO**: 1 hour
- **RPO**: 5 minutes

### DR Procedures
1. Automated backups every 6 hours
2. Cross-region replication for critical components
3. Automated failover for multi-AZ resources
4. Runbooks for manual interventions

## Maintenance Windows

- **Scheduled**: Sunday 2-4 AM EST
- **Emergency**: As needed with notification
- **Updates**: Blue/green deployments with no downtime

## Support Contacts

- **On-Call**: Use PagerDuty escalation
- **AWS Support**: Premium support tier
- **Internal**: #storygen-ops Slack channel

## Troubleshooting

### Common Issues

1. **High Response Times**
   - Check Redis cache hit rate
   - Verify Bedrock API quotas
   - Review CloudFront cache headers

2. **Deployment Failures**
   - Check container health checks
   - Verify secrets are accessible
   - Review CloudFormation events

3. **Database Issues**
   - Monitor DynamoDB throttling
   - Check GSI utilization
   - Verify backup status

### Useful Commands

```bash
# View ECS service logs
aws logs tail /ecs/storygen-prod --follow

# Check service health
aws ecs describe-services \
  --cluster storygen-prod \
  --services storygen-prod

# View recent deployments
aws deploy list-deployments \
  --application-name storygen-prod

# Check CloudWatch alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix storygen-prod
```

## Performance Tuning

1. **Application Level**:
   - Enable Redis query caching
   - Optimize Pinecone queries
   - Batch DynamoDB operations

2. **Infrastructure Level**:
   - Right-size container resources
   - Optimize ALB target groups
   - Tune Redis cluster size

3. **CDN Level**:
   - Maximize cache hit ratio
   - Optimize cache headers
   - Use CloudFront compression

## Compliance and Auditing

- **Logging**: All API calls logged with request IDs
- **Audit Trail**: CloudTrail enabled for all services
- **Compliance**: SOC2 ready architecture
- **Data Residency**: US-East-1 primary region

Remember to always test changes in staging before applying to production!