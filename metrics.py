"""
Production metrics collection for StoryGen
Integrates with Prometheus, CloudWatch, and StatsD
"""

import time
import functools
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import boto3
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry
from flask import Response, request
import statsd
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricsConfig:
    """Configuration for metrics collection"""
    statsd_host: str = "localhost"
    statsd_port: int = 9125
    statsd_prefix: str = "storygen"
    cloudwatch_namespace: str = "StoryGen"
    cloudwatch_enabled: bool = True
    prometheus_enabled: bool = True


class StoryGenMetrics:
    """Centralized metrics collection for StoryGen"""
    
    def __init__(self, config: MetricsConfig):
        self.config = config
        
        # Initialize StatsD client
        self.statsd = statsd.StatsClient(
            host=config.statsd_host,
            port=config.statsd_port,
            prefix=config.statsd_prefix
        )
        
        # Initialize CloudWatch client
        if config.cloudwatch_enabled:
            self.cloudwatch = boto3.client('cloudwatch')
        else:
            self.cloudwatch = None
            
        # Prometheus metrics
        if config.prometheus_enabled:
            self._init_prometheus_metrics()
            
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics"""
        # Request metrics
        self.requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status']
        )
        
        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0)
        )
        
        # Story generation metrics
        self.story_generation_total = Counter(
            'story_generation_total',
            'Total story generation requests',
            ['style', 'status']
        )
        
        self.story_generation_duration = Histogram(
            'story_generation_duration_seconds',
            'Story generation duration in seconds',
            ['style'],
            buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
        )
        
        # Model metrics
        self.model_requests = Counter(
            'model_requests_total',
            'Total requests to AI models',
            ['model', 'operation', 'status']
        )
        
        self.model_latency = Histogram(
            'model_latency_seconds',
            'AI model response latency',
            ['model', 'operation'],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache_type']
        )
        
        self.cache_misses = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['cache_type']
        )
        
        # Error metrics
        self.errors_total = Counter(
            'errors_total',
            'Total errors',
            ['error_type', 'endpoint']
        )
        
        # System metrics
        self.active_connections = Gauge(
            'active_connections',
            'Number of active connections'
        )
        
        self.queue_size = Gauge(
            'queue_size',
            'Size of processing queue',
            ['queue_name']
        )
        
    def track_request(self, method: str, endpoint: str, status: int, duration: float):
        """Track HTTP request metrics"""
        # Prometheus
        if self.config.prometheus_enabled:
            self.requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=str(status)
            ).inc()
            
            self.request_duration.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
        # StatsD
        self.statsd.incr(f'request.{method.lower()}.{status}')
        self.statsd.timing(f'request.duration.{endpoint.replace("/", ".")}', duration * 1000)
        
        # CloudWatch
        if self.cloudwatch:
            self._put_cloudwatch_metric(
                'RequestCount',
                1,
                unit='Count',
                dimensions=[
                    {'Name': 'Method', 'Value': method},
                    {'Name': 'Endpoint', 'Value': endpoint},
                    {'Name': 'StatusCode', 'Value': str(status)}
                ]
            )
            
            self._put_cloudwatch_metric(
                'RequestDuration',
                duration * 1000,
                unit='Milliseconds',
                dimensions=[
                    {'Name': 'Method', 'Value': method},
                    {'Name': 'Endpoint', 'Value': endpoint}
                ]
            )
            
    def track_story_generation(self, style: str, duration: float, success: bool = True):
        """Track story generation metrics"""
        status = 'success' if success else 'failure'
        
        # Prometheus
        if self.config.prometheus_enabled:
            self.story_generation_total.labels(
                style=style,
                status=status
            ).inc()
            
            if success:
                self.story_generation_duration.labels(
                    style=style
                ).observe(duration)
                
        # StatsD
        self.statsd.incr(f'story.{style}.{status}')
        if success:
            self.statsd.timing(f'story.duration.{style}', duration * 1000)
            
        # CloudWatch
        if self.cloudwatch:
            self._put_cloudwatch_metric(
                'StoryGenerationCount',
                1,
                unit='Count',
                dimensions=[
                    {'Name': 'Style', 'Value': style},
                    {'Name': 'Status', 'Value': status}
                ]
            )
            
            if success:
                self._put_cloudwatch_metric(
                    'StoryGenerationDuration',
                    duration * 1000,
                    unit='Milliseconds',
                    dimensions=[
                        {'Name': 'Style', 'Value': style}
                    ]
                )
                
    def track_model_request(self, model: str, operation: str, duration: float, success: bool = True):
        """Track AI model request metrics"""
        status = 'success' if success else 'failure'
        
        # Prometheus
        if self.config.prometheus_enabled:
            self.model_requests.labels(
                model=model,
                operation=operation,
                status=status
            ).inc()
            
            if success:
                self.model_latency.labels(
                    model=model,
                    operation=operation
                ).observe(duration)
                
        # StatsD
        self.statsd.incr(f'model.{model}.{operation}.{status}')
        if success:
            self.statsd.timing(f'model.latency.{model}.{operation}', duration * 1000)
            
    def track_cache(self, cache_type: str, hit: bool):
        """Track cache metrics"""
        # Prometheus
        if self.config.prometheus_enabled:
            if hit:
                self.cache_hits.labels(cache_type=cache_type).inc()
            else:
                self.cache_misses.labels(cache_type=cache_type).inc()
                
        # StatsD
        metric_name = f'cache.{cache_type}.{"hit" if hit else "miss"}'
        self.statsd.incr(metric_name)
        
    def track_error(self, error_type: str, endpoint: str):
        """Track error metrics"""
        # Prometheus
        if self.config.prometheus_enabled:
            self.errors_total.labels(
                error_type=error_type,
                endpoint=endpoint
            ).inc()
            
        # StatsD
        self.statsd.incr(f'error.{error_type}.{endpoint.replace("/", ".")}')
        
        # CloudWatch
        if self.cloudwatch:
            self._put_cloudwatch_metric(
                'ErrorCount',
                1,
                unit='Count',
                dimensions=[
                    {'Name': 'ErrorType', 'Value': error_type},
                    {'Name': 'Endpoint', 'Value': endpoint}
                ]
            )
            
    def set_active_connections(self, count: int):
        """Set active connections gauge"""
        if self.config.prometheus_enabled:
            self.active_connections.set(count)
        self.statsd.gauge('connections.active', count)
        
    def set_queue_size(self, queue_name: str, size: int):
        """Set queue size gauge"""
        if self.config.prometheus_enabled:
            self.queue_size.labels(queue_name=queue_name).set(size)
        self.statsd.gauge(f'queue.{queue_name}.size', size)
        
    def _put_cloudwatch_metric(self, metric_name: str, value: float, unit: str = 'None', 
                              dimensions: Optional[list] = None):
        """Send metric to CloudWatch"""
        if not self.cloudwatch:
            return
            
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
            
            if dimensions:
                metric_data['Dimensions'] = dimensions
                
            self.cloudwatch.put_metric_data(
                Namespace=self.config.cloudwatch_namespace,
                MetricData=[metric_data]
            )
        except Exception as e:
            logger.error(f"Failed to send CloudWatch metric: {e}")
            
    def get_prometheus_metrics(self) -> Response:
        """Return Prometheus metrics in text format"""
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


# Flask decorators for automatic metric tracking
def track_request_metrics(metrics: StoryGenMetrics):
    """Decorator to track request metrics"""
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                response = f(*args, **kwargs)
                status = response[1] if isinstance(response, tuple) else 200
                return response
            except Exception as e:
                status = 500
                raise
            finally:
                duration = time.time() - start_time
                endpoint = request.endpoint or request.path
                metrics.track_request(
                    method=request.method,
                    endpoint=endpoint,
                    status=status,
                    duration=duration
                )
                
        return wrapper
    return decorator


def track_story_generation_metrics(metrics: StoryGenMetrics):
    """Decorator to track story generation metrics"""
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            style = kwargs.get('style', 'unknown')
            
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time
                metrics.track_story_generation(style, duration, success=True)
                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics.track_story_generation(style, duration, success=False)
                raise
                
        return wrapper
    return decorator


# Initialize global metrics instance
metrics_config = MetricsConfig(
    statsd_host="statsd",
    cloudwatch_enabled=True,
    prometheus_enabled=True
)
metrics = StoryGenMetrics(metrics_config)