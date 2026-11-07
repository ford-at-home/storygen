"""Monitoring Stack for Richmond Storyline Generator"""

from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cloudwatch,
    aws_sns as sns,
    aws_cloudwatch_actions as cw_actions,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
    CfnOutput,
)
from constructs import Construct


class MonitoringStack(Stack):
    """Creates CloudWatch dashboards, alarms, and alerting"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        cluster: ecs.Cluster,
        service: ecs.FargateService,
        alb: elbv2.ApplicationLoadBalancer,
        env_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SNS Topic for alerts
        self.alert_topic = sns.Topic(
            self,
            "AlertTopic",
            display_name=f"StoryGen {env_name} Alerts",
            topic_name=f"storygen-alerts-{env_name}",
        )

        # Add email subscription (replace with actual email)
        self.alert_topic.add_subscription(
            sns.subscriptions.EmailSubscription("alerts@storygen.com")
        )

        # Critical alerts topic (for PagerDuty integration)
        self.critical_topic = sns.Topic(
            self,
            "CriticalTopic",
            display_name=f"StoryGen {env_name} Critical Alerts",
            topic_name=f"storygen-critical-{env_name}",
        )

        # CloudWatch Dashboard
        dashboard = cloudwatch.Dashboard(
            self,
            "Dashboard",
            dashboard_name=f"storygen-{env_name}",
            period_override=cloudwatch.PeriodOverride.AUTO,
        )

        # ALB Metrics
        alb_requests = cloudwatch.Metric(
            namespace="AWS/ApplicationELB",
            metric_name="RequestCount",
            dimensions_map={
                "LoadBalancer": alb.load_balancer_full_name,
            },
            statistic="Sum",
        )

        alb_response_time = cloudwatch.Metric(
            namespace="AWS/ApplicationELB",
            metric_name="TargetResponseTime",
            dimensions_map={
                "LoadBalancer": alb.load_balancer_full_name,
            },
            statistic="Average",
        )

        alb_healthy_hosts = cloudwatch.Metric(
            namespace="AWS/ApplicationELB",
            metric_name="HealthyHostCount",
            dimensions_map={
                "LoadBalancer": alb.load_balancer_full_name,
            },
            statistic="Average",
        )

        # ECS Metrics
        ecs_cpu = service.metric_cpu_utilization(
            period=Duration.minutes(5),
            statistic="Average",
        )

        ecs_memory = service.metric_memory_utilization(
            period=Duration.minutes(5),
            statistic="Average",
        )

        # Custom application metrics
        app_story_generation = cloudwatch.Metric(
            namespace="StoryGen",
            metric_name="StoryGenerationCount",
            dimensions_map={"Environment": env_name},
            statistic="Sum",
        )

        app_story_latency = cloudwatch.Metric(
            namespace="StoryGen",
            metric_name="StoryGenerationLatency",
            dimensions_map={"Environment": env_name},
            statistic="Average",
        )

        app_error_rate = cloudwatch.Metric(
            namespace="StoryGen",
            metric_name="ErrorRate",
            dimensions_map={"Environment": env_name},
            statistic="Average",
        )

        # Dashboard Layout
        dashboard.add_widgets(
            # Row 1: Overview
            cloudwatch.GraphWidget(
                title="Request Rate",
                left=[alb_requests],
                width=8,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="Response Time",
                left=[alb_response_time],
                width=8,
                height=6,
            ),
            cloudwatch.SingleValueWidget(
                title="Healthy Hosts",
                metrics=[alb_healthy_hosts],
                width=8,
                height=6,
            ),
        )

        dashboard.add_widgets(
            # Row 2: ECS Metrics
            cloudwatch.GraphWidget(
                title="ECS CPU Utilization",
                left=[ecs_cpu],
                width=12,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="ECS Memory Utilization",
                left=[ecs_memory],
                width=12,
                height=6,
            ),
        )

        dashboard.add_widgets(
            # Row 3: Application Metrics
            cloudwatch.GraphWidget(
                title="Story Generation Rate",
                left=[app_story_generation],
                width=8,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="Story Generation Latency",
                left=[app_story_latency],
                width=8,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="Error Rate",
                left=[app_error_rate],
                width=8,
                height=6,
            ),
        )

        # Alarms
        # High CPU alarm
        cpu_alarm = cloudwatch.Alarm(
            self,
            "HighCPUAlarm",
            metric=ecs_cpu,
            threshold=80,
            evaluation_periods=2,
            alarm_description="ECS CPU utilization is too high",
            alarm_name=f"storygen-{env_name}-high-cpu",
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        cpu_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))

        # High memory alarm
        memory_alarm = cloudwatch.Alarm(
            self,
            "HighMemoryAlarm",
            metric=ecs_memory,
            threshold=85,
            evaluation_periods=2,
            alarm_description="ECS memory utilization is too high",
            alarm_name=f"storygen-{env_name}-high-memory",
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        memory_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))

        # Unhealthy hosts alarm
        unhealthy_alarm = cloudwatch.Alarm(
            self,
            "UnhealthyHostsAlarm",
            metric=alb_healthy_hosts,
            threshold=1 if env_name != "prod" else 2,
            evaluation_periods=2,
            alarm_description="Not enough healthy hosts",
            alarm_name=f"storygen-{env_name}-unhealthy-hosts",
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.BREACHING,
        )
        unhealthy_alarm.add_alarm_action(cw_actions.SnsAction(self.critical_topic))

        # High response time alarm
        response_time_alarm = cloudwatch.Alarm(
            self,
            "HighResponseTimeAlarm",
            metric=alb_response_time,
            threshold=3000,  # 3 seconds
            evaluation_periods=3,
            alarm_description="Response time is too high",
            alarm_name=f"storygen-{env_name}-high-response-time",
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        response_time_alarm.add_alarm_action(cw_actions.SnsAction(self.alert_topic))

        # High error rate alarm
        error_rate_alarm = cloudwatch.Alarm(
            self,
            "HighErrorRateAlarm",
            metric=app_error_rate,
            threshold=5,  # 5% error rate
            evaluation_periods=2,
            alarm_description="Application error rate is too high",
            alarm_name=f"storygen-{env_name}-high-error-rate",
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        error_rate_alarm.add_alarm_action(cw_actions.SnsAction(self.critical_topic))

        # Log insights queries
        insights_queries = [
            logs.QueryDefinition(
                self,
                "ErrorQuery",
                query_definition_name=f"storygen-{env_name}-errors",
                query_string="""
                fields @timestamp, @message
                | filter @message like /ERROR/
                | sort @timestamp desc
                | limit 100
                """,
                log_groups=[f"/ecs/storygen-{env_name}"],
            ),
            logs.QueryDefinition(
                self,
                "SlowRequestsQuery",
                query_definition_name=f"storygen-{env_name}-slow-requests",
                query_string="""
                fields @timestamp, duration, path
                | filter duration > 3000
                | sort duration desc
                | limit 100
                """,
                log_groups=[f"/ecs/storygen-{env_name}"],
            ),
            logs.QueryDefinition(
                self,
                "TopEndpointsQuery",
                query_definition_name=f"storygen-{env_name}-top-endpoints",
                query_string="""
                fields path
                | stats count() by path
                | sort count desc
                | limit 20
                """,
                log_groups=[f"/ecs/storygen-{env_name}"],
            ),
        ]

        # Synthetic monitoring (CloudWatch Synthetics)
        if env_name == "prod":
            # This would create synthetic canaries for production
            # Requires additional setup with Lambda functions
            pass

        # Outputs
        CfnOutput(
            self,
            "DashboardURL",
            value=f"https://console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={dashboard.dashboard_name}",
            export_name=f"{env_name}-dashboard-url",
        )

        CfnOutput(
            self,
            "AlertTopicArn",
            value=self.alert_topic.topic_arn,
            export_name=f"{env_name}-alert-topic-arn",
        )

        CfnOutput(
            self,
            "CriticalTopicArn",
            value=self.critical_topic.topic_arn,
            export_name=f"{env_name}-critical-topic-arn",
        )