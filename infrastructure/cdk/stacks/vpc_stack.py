"""VPC Stack for Richmond Storyline Generator"""

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    CfnOutput,
)
from constructs import Construct


class VPCStack(Stack):
    """Creates VPC with public/private subnets across multiple AZs"""

    def __init__(
        self, scope: Construct, construct_id: str, env_name: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create VPC with high availability
        self.vpc = ec2.Vpc(
            self,
            "VPC",
            max_azs=3,  # Use 3 AZs for high availability
            cidr="10.0.0.0/16",
            nat_gateways=2 if env_name == "prod" else 1,  # HA NAT for production
            subnet_configuration=[
                # Public subnets for ALB
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                # Private subnets for application
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                # Isolated subnets for databases
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        # VPC Flow Logs for security and debugging
        self.vpc.add_flow_log(
            "FlowLog",
            destination=ec2.FlowLogDestination.to_cloud_watch_logs(),
            traffic_type=ec2.FlowLogTrafficType.ALL,
        )

        # VPC Endpoints for AWS services (cost optimization)
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        self.vpc.add_gateway_endpoint(
            "DynamoDBEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
        )

        # Interface endpoints for other services
        self.vpc.add_interface_endpoint(
            "ECREndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR,
        )

        self.vpc.add_interface_endpoint(
            "ECRDockerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER,
        )

        self.vpc.add_interface_endpoint(
            "CloudWatchLogsEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
        )

        self.vpc.add_interface_endpoint(
            "SecretsManagerEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER,
        )

        # Outputs
        CfnOutput(
            self,
            "VPCId",
            value=self.vpc.vpc_id,
            export_name=f"{env_name}-vpc-id",
        )

        CfnOutput(
            self,
            "VPCCidr",
            value=self.vpc.vpc_cidr_block,
            export_name=f"{env_name}-vpc-cidr",
        )