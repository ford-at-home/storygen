"""Compute Stack for Richmond Storyline Generator"""

from aws_cdk import (
    Stack,
    Duration,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elbv2,
    aws_autoscaling as autoscaling,
    aws_logs as logs,
    aws_servicediscovery as sd,
    aws_elasticache as elasticache,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_secretsmanager as secrets,
    CfnOutput,
)
from constructs import Construct
import json


class ComputeStack(Stack):
    """Creates ECS cluster, services, load balancer, and Redis cache"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.Vpc,
        security_groups: dict,
        database_table: dynamodb.Table,
        s3_bucket: s3.Bucket,
        env_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create ECS Cluster
        self.cluster = ecs.Cluster(
            self,
            "Cluster",
            vpc=vpc,
            cluster_name=f"storygen-{env_name}",
            container_insights=True,
            enable_fargate_capacity_providers=True,
        )

        # Service Discovery namespace
        namespace = sd.PrivateDnsNamespace(
            self,
            "ServiceDiscovery",
            name=f"storygen.{env_name}.local",
            vpc=vpc,
        )

        # Redis Cache Cluster
        cache_subnet_group = elasticache.CfnSubnetGroup(
            self,
            "CacheSubnetGroup",
            description="Subnet group for Redis cache",
            subnet_ids=[subnet.subnet_id for subnet in vpc.private_subnets],
        )

        self.redis_cluster = elasticache.CfnReplicationGroup(
            self,
            "RedisCluster",
            replication_group_id=f"storygen-{env_name}",
            replication_group_description="Redis cache for StoryGen",
            engine="redis",
            cache_node_type="cache.r6g.large" if env_name == "prod" else "cache.t3.micro",
            num_node_groups=3 if env_name == "prod" else 1,
            replicas_per_node_group=2 if env_name == "prod" else 0,
            automatic_failover_enabled=env_name == "prod",
            multi_az_enabled=env_name == "prod",
            at_rest_encryption_enabled=True,
            transit_encryption_enabled=True,
            cache_subnet_group_name=cache_subnet_group.ref,
            security_group_ids=[security_groups["cache"].security_group_id],
            snapshot_retention_limit=7 if env_name == "prod" else 1,
            snapshot_window="03:00-05:00",
            preferred_maintenance_window="sun:05:00-sun:07:00",
        )

        # Create secrets for API keys
        api_secrets = secrets.Secret(
            self,
            "APISecrets",
            description="API keys for StoryGen",
            secret_object_value={
                "PINECONE_API_KEY": secrets.SecretValue.unsafe_plain_text("{{resolve:secretsmanager:pinecone-api-key:SecretString:key}}"),
                "OPENAI_API_KEY": secrets.SecretValue.unsafe_plain_text("{{resolve:secretsmanager:openai-api-key:SecretString:key}}"),
            },
        )

        # Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDefinition",
            memory_limit_mib=4096 if env_name == "prod" else 2048,
            cpu=2048 if env_name == "prod" else 1024,
            task_role=iam.Role.from_role_arn(
                self, "ImportedTaskRole", 
                f"arn:aws:iam::{self.account}:role/{env_name}-task-role"
            ),
            execution_role=iam.Role.from_role_arn(
                self, "ImportedExecutionRole",
                f"arn:aws:iam::{self.account}:role/{env_name}-task-execution-role"
            ),
        )

        # Log configuration
        log_group = logs.LogGroup(
            self,
            "LogGroup",
            log_group_name=f"/ecs/storygen-{env_name}",
            retention=logs.RetentionDays.THIRTY_DAYS if env_name == "prod" else logs.RetentionDays.SEVEN_DAYS,
        )

        # Container definition
        container = task_definition.add_container(
            "app",
            image=ecs.ContainerImage.from_registry(
                f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/storygen:latest"
            ),
            memory_limit_mib=4096 if env_name == "prod" else 2048,
            cpu=2048 if env_name == "prod" else 1024,
            environment={
                "PORT": "8080",
                "FLASK_ENV": env_name,
                "AWS_REGION": self.region,
                "DYNAMODB_TABLE": database_table.table_name,
                "S3_BUCKET": s3_bucket.bucket_name,
                "REDIS_ENDPOINT": self.redis_cluster.attr_primary_end_point_address,
                "REDIS_PORT": self.redis_cluster.attr_primary_end_point_port,
                "LOG_LEVEL": "INFO" if env_name == "prod" else "DEBUG",
            },
            secrets={
                "PINECONE_API_KEY": ecs.Secret.from_secrets_manager(api_secrets, "PINECONE_API_KEY"),
                "OPENAI_API_KEY": ecs.Secret.from_secrets_manager(api_secrets, "OPENAI_API_KEY"),
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="storygen",
                log_group=log_group,
            ),
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(10),
                retries=3,
                start_period=Duration.seconds(60),
            ),
        )

        container.add_port_mappings(
            ecs.PortMapping(
                container_port=8080,
                protocol=ecs.Protocol.TCP,
            )
        )

        # Application Load Balancer
        self.alb = elbv2.ApplicationLoadBalancer(
            self,
            "ALB",
            vpc=vpc,
            internet_facing=True,
            security_group=security_groups["alb"],
            load_balancer_name=f"storygen-{env_name}",
            deletion_protection=env_name == "prod",
        )

        # ALB target group
        target_group = elbv2.ApplicationTargetGroup(
            self,
            "TargetGroup",
            vpc=vpc,
            port=8080,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/health",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(10),
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
            ),
            deregistration_delay=Duration.seconds(30),
            stickiness_cookie_duration=Duration.hours(1),
        )

        # HTTPS listener (requires certificate)
        listener = self.alb.add_listener(
            "HTTPSListener",
            port=443,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            certificates=[
                elbv2.ListenerCertificate.from_arn(
                    f"arn:aws:acm:{self.region}:{self.account}:certificate/your-cert-id"
                )
            ],
            default_target_groups=[target_group],
        )

        # HTTP to HTTPS redirect
        self.alb.add_listener(
            "HTTPListener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            default_action=elbv2.ListenerAction.redirect(
                port="443",
                protocol=elbv2.ApplicationProtocol.HTTPS,
                permanent=True,
            ),
        )

        # ECS Service
        self.service = ecs.FargateService(
            self,
            "Service",
            cluster=self.cluster,
            task_definition=task_definition,
            desired_count=3 if env_name == "prod" else 1,
            service_name=f"storygen-{env_name}",
            security_groups=[security_groups["app"]],
            assign_public_ip=False,
            platform_version=ecs.FargatePlatformVersion.LATEST,
            deployment_configuration=ecs.DeploymentConfiguration(
                maximum_percent=200,
                minimum_healthy_percent=100 if env_name == "prod" else 50,
                deployment_circuit_breaker=ecs.DeploymentCircuitBreaker(
                    rollback=True,
                ),
            ),
            enable_ecs_managed_tags=True,
            propagate_tags=ecs.PropagatedTagSource.SERVICE,
            enable_execute_command=env_name != "prod",  # Enable for debugging in non-prod
            cloud_map_options=ecs.CloudMapOptions(
                name="api",
                cloud_map_namespace=namespace,
                dns_record_type=sd.DnsRecordType.A,
            ),
        )

        # Attach to target group
        self.service.attach_to_application_target_group(target_group)

        # Auto-scaling configuration
        scaling = self.service.auto_scale_task_count(
            min_capacity=3 if env_name == "prod" else 1,
            max_capacity=50 if env_name == "prod" else 10,
        )

        # CPU-based scaling
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(300),
            scale_out_cooldown=Duration.seconds(60),
        )

        # Memory-based scaling
        scaling.scale_on_memory_utilization(
            "MemoryScaling",
            target_utilization_percent=80,
            scale_in_cooldown=Duration.seconds(300),
            scale_out_cooldown=Duration.seconds(60),
        )

        # Request count scaling
        scaling.scale_on_request_count(
            "RequestCountScaling",
            requests_per_target=1000,
            target_group=target_group,
            scale_in_cooldown=Duration.seconds(300),
            scale_out_cooldown=Duration.seconds(60),
        )

        # Outputs
        CfnOutput(
            self,
            "ALBEndpoint",
            value=f"https://{self.alb.load_balancer_dns_name}",
            export_name=f"{env_name}-alb-endpoint",
        )

        CfnOutput(
            self,
            "ClusterName",
            value=self.cluster.cluster_name,
            export_name=f"{env_name}-cluster-name",
        )

        CfnOutput(
            self,
            "ServiceName",
            value=self.service.service_name,
            export_name=f"{env_name}-service-name",
        )

        CfnOutput(
            self,
            "RedisEndpoint",
            value=self.redis_cluster.attr_primary_end_point_address,
            export_name=f"{env_name}-redis-endpoint",
        )