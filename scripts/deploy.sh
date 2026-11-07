#!/bin/bash
# Production deployment script for StoryGen

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENTS=("dev" "staging" "prod")
AWS_REGION=${AWS_REGION:-"us-east-1"}
PROJECT_NAME="storygen"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

usage() {
    echo "Usage: $0 <environment> <action>"
    echo ""
    echo "Environments: ${ENVIRONMENTS[*]}"
    echo "Actions:"
    echo "  deploy-infra    - Deploy CDK infrastructure"
    echo "  deploy-app      - Deploy application"
    echo "  deploy-all      - Deploy infrastructure and application"
    echo "  status          - Check deployment status"
    echo "  rollback        - Rollback to previous version"
    echo "  validate        - Validate deployment"
    echo ""
    echo "Examples:"
    echo "  $0 prod deploy-all"
    echo "  $0 staging status"
    exit 1
}

validate_environment() {
    local env=$1
    if [[ ! " ${ENVIRONMENTS[@]} " =~ " ${env} " ]]; then
        log_error "Invalid environment: $env"
    fi
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
    fi
    
    # Check CDK
    if ! command -v cdk &> /dev/null; then
        log_error "AWS CDK is not installed"
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured"
    fi
    
    log_info "Prerequisites check passed"
}

deploy_infrastructure() {
    local env=$1
    log_info "Deploying infrastructure for $env..."
    
    cd infrastructure/cdk
    
    # Set environment variables
    export CDK_ENV=$env
    export CDK_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    export CDK_REGION=$AWS_REGION
    
    # Deploy stacks in order
    local stacks=(
        "StoryGen-VPC-$env"
        "StoryGen-Security-$env"
        "StoryGen-Database-$env"
        "StoryGen-Storage-$env"
        "StoryGen-Compute-$env"
        "StoryGen-Monitoring-$env"
        "StoryGen-CDN-$env"
    )
    
    if [[ "$env" == "prod" ]]; then
        stacks+=("StoryGen-CICD-$env")
    fi
    
    for stack in "${stacks[@]}"; do
        log_info "Deploying $stack..."
        cdk deploy $stack --require-approval never || log_error "Failed to deploy $stack"
    done
    
    cd ../..
    log_info "Infrastructure deployment completed"
}

build_and_push_image() {
    local env=$1
    log_info "Building and pushing Docker image..."
    
    # Get ECR repository URI
    local ecr_repo=$(aws cloudformation describe-stacks \
        --stack-name StoryGen-CICD-$env \
        --query "Stacks[0].Outputs[?OutputKey=='ECRRepositoryURI'].OutputValue" \
        --output text 2>/dev/null || echo "")
    
    if [[ -z "$ecr_repo" ]]; then
        ecr_repo="$CDK_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME"
    fi
    
    # Build image
    log_info "Building Docker image..."
    docker build -t $PROJECT_NAME:latest .
    
    # Tag image
    local git_sha=$(git rev-parse --short HEAD)
    docker tag $PROJECT_NAME:latest $ecr_repo:latest
    docker tag $PROJECT_NAME:latest $ecr_repo:$git_sha
    
    # Login to ECR
    log_info "Logging into ECR..."
    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin $ecr_repo
    
    # Push image
    log_info "Pushing image to ECR..."
    docker push $ecr_repo:latest
    docker push $ecr_repo:$git_sha
    
    log_info "Image pushed successfully"
    echo $ecr_repo:$git_sha
}

deploy_application() {
    local env=$1
    log_info "Deploying application for $env..."
    
    # Build and push image
    local image_uri=$(build_and_push_image $env)
    
    # Update ECS service
    local cluster_name="$PROJECT_NAME-$env"
    local service_name="$PROJECT_NAME-$env"
    
    log_info "Updating ECS service with new image..."
    aws ecs update-service \
        --cluster $cluster_name \
        --service $service_name \
        --force-new-deployment \
        --region $AWS_REGION
    
    # Wait for deployment to complete
    log_info "Waiting for deployment to stabilize..."
    aws ecs wait services-stable \
        --cluster $cluster_name \
        --services $service_name \
        --region $AWS_REGION
    
    log_info "Application deployment completed"
}

check_deployment_status() {
    local env=$1
    log_info "Checking deployment status for $env..."
    
    # Check ECS service status
    local cluster_name="$PROJECT_NAME-$env"
    local service_name="$PROJECT_NAME-$env"
    
    aws ecs describe-services \
        --cluster $cluster_name \
        --services $service_name \
        --region $AWS_REGION \
        --query "services[0].{Status:status,DesiredCount:desiredCount,RunningCount:runningCount,PendingCount:pendingCount}" \
        --output table
    
    # Check recent deployments
    log_info "Recent deployments:"
    aws ecs describe-services \
        --cluster $cluster_name \
        --services $service_name \
        --region $AWS_REGION \
        --query "services[0].deployments[*].{Status:status,TaskDef:taskDefinition,DesiredCount:desiredCount,RunningCount:runningCount,CreatedAt:createdAt}" \
        --output table
    
    # Check ALB health
    local alb_name="$PROJECT_NAME-$env"
    log_info "Load balancer target health:"
    aws elbv2 describe-target-health \
        --target-group-arn $(aws elbv2 describe-target-groups \
            --names $alb_name-tg \
            --query "TargetGroups[0].TargetGroupArn" \
            --output text 2>/dev/null || echo "not-found") \
        --query "TargetHealthDescriptions[*].{Target:Target.Id,Health:TargetHealth.State}" \
        --output table 2>/dev/null || echo "Target group not found"
}

rollback_deployment() {
    local env=$1
    log_info "Rolling back deployment for $env..."
    
    # Get current and previous task definitions
    local cluster_name="$PROJECT_NAME-$env"
    local service_name="$PROJECT_NAME-$env"
    
    local current_task_def=$(aws ecs describe-services \
        --cluster $cluster_name \
        --services $service_name \
        --region $AWS_REGION \
        --query "services[0].taskDefinition" \
        --output text)
    
    # Extract task definition family and revision
    local task_family=$(echo $current_task_def | sed 's/.*\///' | sed 's/:[0-9]*$//')
    local current_revision=$(echo $current_task_def | sed 's/.*://')
    local previous_revision=$((current_revision - 1))
    
    if [[ $previous_revision -lt 1 ]]; then
        log_error "No previous revision to rollback to"
    fi
    
    local previous_task_def="$task_family:$previous_revision"
    
    log_info "Rolling back from $current_task_def to $previous_task_def..."
    
    # Update service with previous task definition
    aws ecs update-service \
        --cluster $cluster_name \
        --service $service_name \
        --task-definition $previous_task_def \
        --region $AWS_REGION
    
    # Wait for rollback to complete
    log_info "Waiting for rollback to stabilize..."
    aws ecs wait services-stable \
        --cluster $cluster_name \
        --services $service_name \
        --region $AWS_REGION
    
    log_info "Rollback completed"
}

validate_deployment() {
    local env=$1
    log_info "Validating deployment for $env..."
    
    # Get ALB endpoint
    local alb_endpoint=$(aws cloudformation describe-stacks \
        --stack-name StoryGen-Compute-$env \
        --query "Stacks[0].Outputs[?OutputKey=='ALBEndpoint'].OutputValue" \
        --output text)
    
    # Health check
    log_info "Checking health endpoint..."
    local health_response=$(curl -s -o /dev/null -w "%{http_code}" $alb_endpoint/health)
    
    if [[ $health_response -eq 200 ]]; then
        log_info "Health check passed"
    else
        log_error "Health check failed with status: $health_response"
    fi
    
    # API check
    log_info "Checking API endpoint..."
    local api_response=$(curl -s $alb_endpoint/api/styles | jq -r '.styles | length' 2>/dev/null || echo "0")
    
    if [[ $api_response -gt 0 ]]; then
        log_info "API check passed"
    else
        log_warn "API check failed or returned no data"
    fi
    
    # Check CloudWatch alarms
    log_info "Checking CloudWatch alarms..."
    aws cloudwatch describe-alarms \
        --alarm-name-prefix "$PROJECT_NAME-$env" \
        --state-value ALARM \
        --query "MetricAlarms[*].{AlarmName:AlarmName,StateReason:StateReason}" \
        --output table
    
    log_info "Deployment validation completed"
}

# Main script
if [[ $# -ne 2 ]]; then
    usage
fi

ENVIRONMENT=$1
ACTION=$2

validate_environment $ENVIRONMENT
check_prerequisites

case $ACTION in
    deploy-infra)
        deploy_infrastructure $ENVIRONMENT
        ;;
    deploy-app)
        deploy_application $ENVIRONMENT
        ;;
    deploy-all)
        deploy_infrastructure $ENVIRONMENT
        deploy_application $ENVIRONMENT
        validate_deployment $ENVIRONMENT
        ;;
    status)
        check_deployment_status $ENVIRONMENT
        ;;
    rollback)
        rollback_deployment $ENVIRONMENT
        ;;
    validate)
        validate_deployment $ENVIRONMENT
        ;;
    *)
        usage
        ;;
esac

log_info "Operation completed successfully"