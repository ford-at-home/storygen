"""
Production Monitoring for Richmond Storyline Generator
Real-time monitoring and alerting for production environment
"""

import time
import logging
import json
import os
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import aiohttp
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import redis
import boto3
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


# Metrics
UPTIME_GAUGE = Gauge('system_uptime_seconds', 'System uptime in seconds')
ERROR_COUNTER = Counter('errors_total', 'Total number of errors', ['error_type', 'component'])
ALERT_COUNTER = Counter('alerts_sent_total', 'Total number of alerts sent', ['alert_type', 'severity'])
API_AVAILABILITY = Gauge('api_availability_percent', 'API availability percentage')
RESPONSE_TIME_P95 = Gauge('response_time_p95_seconds', 'Response time 95th percentile')
ACTIVE_USERS = Gauge('active_users_total', 'Number of active users')
STORY_GENERATION_RATE = Gauge('story_generation_rate_per_minute', 'Story generation rate per minute')


@dataclass
class AlertConfig:
    """Alert configuration"""
    slack_webhook: Optional[str] = None
    slack_channel: str = "#alerts"
    email_recipients: List[str] = field(default_factory=list)
    pagerduty_key: Optional[str] = None
    
    # Alert thresholds
    error_rate_threshold: float = 0.05  # 5% error rate
    response_time_threshold: float = 2.0  # 2 seconds
    availability_threshold: float = 0.99  # 99% availability
    memory_usage_threshold: float = 0.9  # 90% memory usage
    
    # Alert cooldowns (avoid spam)
    alert_cooldown_minutes: int = 15
    
    # Severity levels
    severity_levels = {
        'low': {'emoji': '⚠️', 'color': 'warning'},
        'medium': {'emoji': '🔶', 'color': 'warning'}, 
        'high': {'emoji': '🔴', 'color': 'danger'},
        'critical': {'emoji': '🚨', 'color': 'danger'}
    }


@dataclass
class MonitoringConfig:
    """Production monitoring configuration"""
    # Check intervals
    health_check_interval: int = 30  # seconds
    metrics_collection_interval: int = 60  # seconds
    alert_check_interval: int = 120  # seconds
    
    # Endpoints to monitor
    base_url: str = "http://localhost:8080"
    health_endpoint: str = "/api/health"
    metrics_endpoint: str = "/metrics"
    
    # Storage
    redis_url: str = "redis://localhost:6379"
    metrics_retention_days: int = 30
    
    # AWS CloudWatch integration
    enable_cloudwatch: bool = True
    cloudwatch_namespace: str = "StoryGen/Production"
    
    # Alert configuration
    alerts: AlertConfig = field(default_factory=AlertConfig)


class ProductionMonitor:
    """Main production monitoring class"""
    
    def __init__(self, config: Optional[MonitoringConfig] = None):
        self.config = config or MonitoringConfig()
        self.redis_client = redis.from_url(self.config.redis_url)
        self.start_time = time.time()
        self.alert_history: Dict[str, datetime] = {}
        
        # Initialize AWS CloudWatch if enabled
        if self.config.enable_cloudwatch:
            self.cloudwatch = boto3.client('cloudwatch')
        
        # Initialize Slack client if configured
        if self.config.alerts.slack_webhook:
            self.slack_token = os.getenv('SLACK_BOT_TOKEN')
            if self.slack_token:
                self.slack_client = WebClient(token=self.slack_token)
        
        # Metrics storage
        self.metrics_buffer: List[Dict[str, Any]] = []
    
    async def start_monitoring(self):
        """Start all monitoring tasks"""
        logger.info("🚀 Starting production monitoring...")
        
        # Create monitoring tasks
        tasks = [
            self._health_check_loop(),
            self._metrics_collection_loop(),
            self._alert_check_loop(),
            self._uptime_tracker_loop()
        ]
        
        # Run all tasks concurrently
        await asyncio.gather(*tasks)
    
    async def _health_check_loop(self):
        """Continuously check system health"""
        while True:
            try:
                await self._check_health()
            except Exception as e:
                logger.error(f"Health check error: {e}")
                ERROR_COUNTER.labels(error_type='health_check', component='monitor').inc()
            
            await asyncio.sleep(self.config.health_check_interval)
    
    async def _check_health(self):
        """Check system health status"""
        async with aiohttp.ClientSession() as session:
            health_url = f"{self.config.base_url}{self.config.health_endpoint}"
            
            try:
                start_time = time.time()
                async with session.get(health_url, timeout=5) as response:
                    response_time = time.time() - start_time
                    health_data = await response.json()
                    
                    # Update metrics
                    if response.status == 200:
                        API_AVAILABILITY.set(1.0)
                        self._record_metric('health_check_success', 1)
                    else:
                        API_AVAILABILITY.set(0.0)
                        self._record_metric('health_check_failure', 1)
                        await self._send_alert(
                            'Health Check Failed',
                            f'Health endpoint returned status {response.status}',
                            'high'
                        )
                    
                    # Check component health
                    if 'components' in health_data:
                        for component, status in health_data['components'].items():
                            if status != 'healthy':
                                await self._send_alert(
                                    f'{component.title()} Unhealthy',
                                    f'{component} is reporting status: {status}',
                                    'medium'
                                )
                    
                    # Record response time
                    self._record_metric('health_check_response_time', response_time)
                    
            except asyncio.TimeoutError:
                API_AVAILABILITY.set(0.0)
                await self._send_alert(
                    'Health Check Timeout',
                    'Health endpoint did not respond within 5 seconds',
                    'high'
                )
            except Exception as e:
                API_AVAILABILITY.set(0.0)
                await self._send_alert(
                    'Health Check Error',
                    f'Failed to check health: {str(e)}',
                    'critical'
                )
    
    async def _metrics_collection_loop(self):
        """Continuously collect system metrics"""
        while True:
            try:
                await self._collect_metrics()
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                ERROR_COUNTER.labels(error_type='metrics_collection', component='monitor').inc()
            
            await asyncio.sleep(self.config.metrics_collection_interval)
    
    async def _collect_metrics(self):
        """Collect various system metrics"""
        # Collect Prometheus metrics
        async with aiohttp.ClientSession() as session:
            metrics_url = f"{self.config.base_url}{self.config.metrics_endpoint}"
            
            try:
                async with session.get(metrics_url, timeout=10) as response:
                    if response.status == 200:
                        metrics_text = await response.text()
                        self._parse_prometheus_metrics(metrics_text)
            except Exception as e:
                logger.error(f"Failed to collect Prometheus metrics: {e}")
        
        # Collect system metrics
        system_metrics = self._get_system_metrics()
        
        # Store metrics
        timestamp = datetime.utcnow()
        metrics_data = {
            'timestamp': timestamp.isoformat(),
            'system': system_metrics,
            'custom': self._get_custom_metrics()
        }
        
        # Store in Redis
        self.redis_client.zadd(
            'metrics:production',
            {json.dumps(metrics_data): timestamp.timestamp()}
        )
        
        # Send to CloudWatch if enabled
        if self.config.enable_cloudwatch:
            await self._send_to_cloudwatch(metrics_data)
        
        # Clean up old metrics
        cutoff_time = (timestamp - timedelta(days=self.config.metrics_retention_days)).timestamp()
        self.redis_client.zremrangebyscore('metrics:production', 0, cutoff_time)
    
    def _parse_prometheus_metrics(self, metrics_text: str):
        """Parse Prometheus metrics text format"""
        for line in metrics_text.split('\n'):
            if line.startswith('#') or not line:
                continue
            
            try:
                # Simple parsing - would use prometheus_client.parser in production
                parts = line.split(' ')
                if len(parts) >= 2:
                    metric_name = parts[0].split('{')[0]
                    metric_value = float(parts[1])
                    
                    # Update specific gauges
                    if 'response_time_p95' in metric_name:
                        RESPONSE_TIME_P95.set(metric_value)
                    elif 'story_generation_rate' in metric_name:
                        STORY_GENERATION_RATE.set(metric_value)
                    elif 'active_users' in metric_name:
                        ACTIVE_USERS.set(metric_value)
                        
            except Exception as e:
                logger.debug(f"Failed to parse metric line: {line}, error: {e}")
    
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics"""
        import psutil
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network stats
            net_io = psutil.net_io_counters()
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / 1024 / 1024,
                'disk_percent': disk.percent,
                'network_bytes_sent': net_io.bytes_sent,
                'network_bytes_recv': net_io.bytes_recv
            }
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}
    
    def _get_custom_metrics(self) -> Dict[str, Any]:
        """Get application-specific metrics"""
        try:
            # Get from Redis
            metrics = {
                'total_stories_generated': self.redis_client.get('metrics:total_stories') or 0,
                'active_sessions': self.redis_client.scard('sessions:active'),
                'cache_hit_rate': self._calculate_cache_hit_rate(),
                'error_rate': self._calculate_error_rate()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get custom metrics: {e}")
            return {}
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        hits = int(self.redis_client.get('metrics:cache_hits') or 0)
        misses = int(self.redis_client.get('metrics:cache_misses') or 0)
        
        total = hits + misses
        if total == 0:
            return 0.0
        
        return hits / total
    
    def _calculate_error_rate(self) -> float:
        """Calculate error rate"""
        # Get recent requests and errors
        now = time.time()
        window_start = now - 300  # 5 minute window
        
        total_requests = self.redis_client.zcount('requests:timestamps', window_start, now)
        total_errors = self.redis_client.zcount('errors:timestamps', window_start, now)
        
        if total_requests == 0:
            return 0.0
        
        return total_errors / total_requests
    
    async def _alert_check_loop(self):
        """Continuously check for alert conditions"""
        while True:
            try:
                await self._check_alerts()
            except Exception as e:
                logger.error(f"Alert check error: {e}")
                ERROR_COUNTER.labels(error_type='alert_check', component='monitor').inc()
            
            await asyncio.sleep(self.config.alert_check_interval)
    
    async def _check_alerts(self):
        """Check various alert conditions"""
        # Get current metrics
        system_metrics = self._get_system_metrics()
        custom_metrics = self._get_custom_metrics()
        
        # Check error rate
        error_rate = custom_metrics.get('error_rate', 0)
        if error_rate > self.config.alerts.error_rate_threshold:
            await self._send_alert(
                'High Error Rate',
                f'Error rate is {error_rate:.2%} (threshold: {self.config.alerts.error_rate_threshold:.2%})',
                'high'
            )
        
        # Check response time
        p95_response_time = RESPONSE_TIME_P95._value.get()
        if p95_response_time > self.config.alerts.response_time_threshold:
            await self._send_alert(
                'Slow Response Times',
                f'P95 response time is {p95_response_time:.2f}s (threshold: {self.config.alerts.response_time_threshold}s)',
                'medium'
            )
        
        # Check memory usage
        memory_percent = system_metrics.get('memory_percent', 0)
        if memory_percent > self.config.alerts.memory_usage_threshold * 100:
            await self._send_alert(
                'High Memory Usage',
                f'Memory usage is {memory_percent:.1f}% (threshold: {self.config.alerts.memory_usage_threshold * 100:.0f}%)',
                'high'
            )
        
        # Check API availability
        availability = API_AVAILABILITY._value.get()
        if availability < self.config.alerts.availability_threshold:
            await self._send_alert(
                'Low API Availability',
                f'API availability is {availability:.2%} (threshold: {self.config.alerts.availability_threshold:.2%})',
                'critical'
            )
    
    async def _send_alert(self, title: str, message: str, severity: str = 'medium'):
        """Send alert through configured channels"""
        # Check cooldown
        alert_key = f"{title}:{severity}"
        if alert_key in self.alert_history:
            last_alert = self.alert_history[alert_key]
            cooldown_end = last_alert + timedelta(minutes=self.config.alerts.alert_cooldown_minutes)
            if datetime.utcnow() < cooldown_end:
                return  # Still in cooldown
        
        # Update alert history
        self.alert_history[alert_key] = datetime.utcnow()
        ALERT_COUNTER.labels(alert_type=title, severity=severity).inc()
        
        # Log alert
        logger.warning(f"ALERT [{severity.upper()}]: {title} - {message}")
        
        # Send to Slack
        if self.config.alerts.slack_webhook:
            await self._send_slack_alert(title, message, severity)
        
        # Send email
        if self.config.alerts.email_recipients:
            await self._send_email_alert(title, message, severity)
        
        # Send to PagerDuty for critical alerts
        if severity == 'critical' and self.config.alerts.pagerduty_key:
            await self._send_pagerduty_alert(title, message)
    
    async def _send_slack_alert(self, title: str, message: str, severity: str):
        """Send alert to Slack"""
        severity_info = self.config.alerts.severity_levels.get(severity, {})
        emoji = severity_info.get('emoji', '⚠️')
        color = severity_info.get('color', 'warning')
        
        slack_message = {
            'channel': self.config.alerts.slack_channel,
            'attachments': [{
                'color': color,
                'title': f"{emoji} {title}",
                'text': message,
                'fields': [
                    {
                        'title': 'Severity',
                        'value': severity.upper(),
                        'short': True
                    },
                    {
                        'title': 'Time',
                        'value': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                        'short': True
                    }
                ],
                'footer': 'Richmond StoryGen Monitor',
                'ts': int(time.time())
            }]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.alerts.slack_webhook,
                    json=slack_message
                ) as response:
                    if response.status != 200:
                        logger.error(f"Failed to send Slack alert: {response.status}")
        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")
    
    async def _send_email_alert(self, title: str, message: str, severity: str):
        """Send email alert (would use SES in production)"""
        # Placeholder for email sending
        logger.info(f"Would send email alert to {self.config.alerts.email_recipients}")
    
    async def _send_pagerduty_alert(self, title: str, message: str):
        """Send alert to PagerDuty"""
        # Placeholder for PagerDuty integration
        logger.info(f"Would send PagerDuty alert: {title}")
    
    async def _uptime_tracker_loop(self):
        """Track system uptime"""
        while True:
            uptime = time.time() - self.start_time
            UPTIME_GAUGE.set(uptime)
            await asyncio.sleep(60)  # Update every minute
    
    async def _send_to_cloudwatch(self, metrics_data: Dict[str, Any]):
        """Send metrics to AWS CloudWatch"""
        if not self.config.enable_cloudwatch:
            return
        
        try:
            # Prepare CloudWatch metrics
            metric_data = []
            
            # System metrics
            for metric_name, value in metrics_data['system'].items():
                if isinstance(value, (int, float)):
                    metric_data.append({
                        'MetricName': metric_name,
                        'Value': value,
                        'Unit': 'None',
                        'Timestamp': datetime.utcnow()
                    })
            
            # Custom metrics
            for metric_name, value in metrics_data['custom'].items():
                if isinstance(value, (int, float)):
                    metric_data.append({
                        'MetricName': metric_name,
                        'Value': value,
                        'Unit': 'None',
                        'Timestamp': datetime.utcnow()
                    })
            
            # Send to CloudWatch
            if metric_data:
                self.cloudwatch.put_metric_data(
                    Namespace=self.config.cloudwatch_namespace,
                    MetricData=metric_data
                )
                
        except Exception as e:
            logger.error(f"Failed to send metrics to CloudWatch: {e}")
    
    def _record_metric(self, metric_name: str, value: float):
        """Record a metric value"""
        # Store in buffer for batch processing
        self.metrics_buffer.append({
            'name': metric_name,
            'value': value,
            'timestamp': time.time()
        })
        
        # Flush buffer if it gets too large
        if len(self.metrics_buffer) > 100:
            self._flush_metrics_buffer()
    
    def _flush_metrics_buffer(self):
        """Flush metrics buffer to storage"""
        if not self.metrics_buffer:
            return
        
        # Store in Redis
        pipeline = self.redis_client.pipeline()
        
        for metric in self.metrics_buffer:
            key = f"metrics:{metric['name']}"
            pipeline.zadd(key, {str(metric['value']): metric['timestamp']})
        
        pipeline.execute()
        self.metrics_buffer.clear()
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get current monitoring status report"""
        uptime = time.time() - self.start_time
        
        return {
            'monitoring_status': 'active',
            'uptime_seconds': uptime,
            'uptime_human': self._format_uptime(uptime),
            'current_metrics': {
                'api_availability': API_AVAILABILITY._value.get(),
                'response_time_p95': RESPONSE_TIME_P95._value.get(),
                'active_users': ACTIVE_USERS._value.get(),
                'story_generation_rate': STORY_GENERATION_RATE._value.get(),
                'error_rate': self._calculate_error_rate()
            },
            'recent_alerts': len(self.alert_history),
            'system_metrics': self._get_system_metrics()
        }
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return ' '.join(parts) or '0m'


async def main():
    """Main monitoring entry point"""
    # Configure from environment
    config = MonitoringConfig()
    
    # Override with environment variables
    config.base_url = os.getenv('MONITOR_BASE_URL', config.base_url)
    config.alerts.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
    config.alerts.pagerduty_key = os.getenv('PAGERDUTY_KEY')
    
    # Create and start monitor
    monitor = ProductionMonitor(config)
    
    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        raise


if __name__ == "__main__":
    # Run monitoring
    asyncio.run(main())