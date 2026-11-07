"""
Analytics engine for collecting and analyzing user behavior and story metrics
Provides real-time insights and reporting capabilities
"""
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import logging
from dataclasses import dataclass, field
import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import statistics

from .models import Analytics, User, Story, StoryStatus
from .repositories import AnalyticsRepository, UserRepository, StoryRepository
from .cache import entity_cache, cache_decorator

logger = logging.getLogger('storygen.analytics')


@dataclass
class MetricDefinition:
    """Definition of a trackable metric"""
    name: str
    description: str
    unit: str
    aggregation: str = "sum"  # sum, avg, max, min, count
    category: str = "general"


class AnalyticsCollector:
    """Collects analytics events from various sources"""
    
    def __init__(self):
        self.repository = AnalyticsRepository()
        self.event_queue = asyncio.Queue(maxsize=1000)
        self.batch_size = 100
        self.flush_interval = 5  # seconds
        self._running = False
        
        # Define standard events
        self.standard_events = {
            # User events
            "user_login": {"category": "authentication", "value": 1},
            "user_logout": {"category": "authentication", "value": 1},
            "user_signup": {"category": "conversion", "value": 1},
            
            # Story events
            "story_started": {"category": "engagement", "value": 1},
            "story_generated": {"category": "conversion", "value": 1},
            "story_published": {"category": "conversion", "value": 1},
            "story_failed": {"category": "error", "value": 1},
            
            # Session events
            "session_started": {"category": "engagement", "value": 1},
            "session_completed": {"category": "conversion", "value": 1},
            "session_abandoned": {"category": "engagement", "value": 1},
            
            # Voice events
            "voice_input_started": {"category": "feature", "value": 1},
            "voice_input_completed": {"category": "feature", "value": 1},
            "voice_transcription_failed": {"category": "error", "value": 1},
            
            # API events
            "api_request": {"category": "performance", "value": 1},
            "api_error": {"category": "error", "value": 1},
            "api_timeout": {"category": "error", "value": 1},
            
            # Search events
            "vector_search": {"category": "feature", "value": 1},
            "content_retrieved": {"category": "feature", "value": 1},
            
            # Template events
            "template_used": {"category": "feature", "value": 1},
            "template_rated": {"category": "engagement", "value": 1}
        }
    
    def track_event(self, event_type: str, user_id: Optional[str] = None,
                   session_id: Optional[str] = None, properties: Dict[str, Any] = None,
                   value: Optional[float] = None):
        """Track an analytics event"""
        try:
            # Get event definition
            event_def = self.standard_events.get(event_type, {})
            
            # Create analytics event
            event = Analytics(
                user_id=user_id,
                session_id=session_id,
                event_type=event_type,
                event_category=event_def.get("category", "custom"),
                event_action=event_type,
                event_value=value or event_def.get("value"),
                properties=properties or {}
            )
            
            # Add to queue
            if not self.event_queue.full():
                self.event_queue.put_nowait(event)
            else:
                logger.warning(f"Analytics queue full, dropping event: {event_type}")
                
        except Exception as e:
            logger.error(f"Failed to track event {event_type}: {e}")
    
    def track_page_view(self, page: str, user_id: Optional[str] = None,
                       session_id: Optional[str] = None, properties: Dict[str, Any] = None):
        """Track page view"""
        self.track_event(
            "page_view",
            user_id=user_id,
            session_id=session_id,
            properties={
                "page": page,
                **(properties or {})
            }
        )
    
    def track_api_call(self, endpoint: str, method: str, status_code: int,
                      response_time: float, user_id: Optional[str] = None):
        """Track API call metrics"""
        self.track_event(
            "api_request",
            user_id=user_id,
            properties={
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "response_time": response_time,
                "success": 200 <= status_code < 300
            },
            value=response_time
        )
    
    def track_story_generation(self, story_id: str, user_id: str, session_id: str,
                             generation_time: float, token_count: int, style: str):
        """Track story generation metrics"""
        self.track_event(
            "story_generated",
            user_id=user_id,
            session_id=session_id,
            properties={
                "story_id": story_id,
                "generation_time": generation_time,
                "token_count": token_count,
                "style": style,
                "tokens_per_second": token_count / generation_time if generation_time > 0 else 0
            },
            value=generation_time
        )
    
    def track_error(self, error_type: str, error_message: str, 
                   user_id: Optional[str] = None, context: Dict[str, Any] = None):
        """Track error events"""
        self.track_event(
            f"{error_type}_error",
            user_id=user_id,
            properties={
                "error_type": error_type,
                "error_message": error_message[:500],  # Limit message length
                "context": context or {}
            }
        )
    
    async def start_collector(self):
        """Start the analytics collector background task"""
        self._running = True
        asyncio.create_task(self._process_events())
        logger.info("Analytics collector started")
    
    async def stop_collector(self):
        """Stop the analytics collector"""
        self._running = False
        # Flush remaining events
        await self._flush_events()
        logger.info("Analytics collector stopped")
    
    async def _process_events(self):
        """Process events from queue in batches"""
        while self._running:
            try:
                # Collect batch of events
                events = []
                deadline = datetime.utcnow() + timedelta(seconds=self.flush_interval)
                
                while len(events) < self.batch_size and datetime.utcnow() < deadline:
                    try:
                        timeout = (deadline - datetime.utcnow()).total_seconds()
                        if timeout > 0:
                            event = await asyncio.wait_for(
                                self.event_queue.get(), 
                                timeout=timeout
                            )
                            events.append(event)
                    except asyncio.TimeoutError:
                        break
                
                # Save batch if we have events
                if events:
                    saved = self.repository.save_batch(events)
                    logger.debug(f"Saved {saved} analytics events")
                    
            except Exception as e:
                logger.error(f"Error processing analytics events: {e}")
                await asyncio.sleep(1)
    
    async def _flush_events(self):
        """Flush all pending events"""
        events = []
        while not self.event_queue.empty():
            try:
                events.append(self.event_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        
        if events:
            self.repository.save_batch(events)
            logger.info(f"Flushed {len(events)} analytics events")


class AnalyticsProcessor:
    """Processes analytics data to generate insights"""
    
    def __init__(self):
        self.analytics_repo = AnalyticsRepository()
        self.user_repo = UserRepository()
        self.story_repo = StoryRepository()
    
    @cache_decorator.cached("analytics", 300)  # Cache for 5 minutes
    def get_dashboard_metrics(self, time_range: str = "24h") -> Dict[str, Any]:
        """Get high-level dashboard metrics"""
        end_time = datetime.utcnow()
        start_time = self._get_start_time(time_range)
        
        # Get all events in time range
        events = self._get_events_in_range(start_time, end_time)
        
        # Calculate metrics
        metrics = {
            "time_range": time_range,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "overview": self._calculate_overview_metrics(events),
            "user_metrics": self._calculate_user_metrics(events, start_time, end_time),
            "story_metrics": self._calculate_story_metrics(events, start_time, end_time),
            "performance_metrics": self._calculate_performance_metrics(events),
            "error_metrics": self._calculate_error_metrics(events),
            "trends": self._calculate_trends(events, time_range)
        }
        
        return metrics
    
    def _get_start_time(self, time_range: str) -> datetime:
        """Convert time range string to start datetime"""
        now = datetime.utcnow()
        
        if time_range == "1h":
            return now - timedelta(hours=1)
        elif time_range == "24h":
            return now - timedelta(days=1)
        elif time_range == "7d":
            return now - timedelta(days=7)
        elif time_range == "30d":
            return now - timedelta(days=30)
        elif time_range == "90d":
            return now - timedelta(days=90)
        else:
            return now - timedelta(days=1)
    
    def _get_events_in_range(self, start_time: datetime, end_time: datetime) -> List[Analytics]:
        """Get all events in time range (aggregated from all users)"""
        events = []
        
        # This is simplified - in production, you'd want a more efficient query
        # Could use DynamoDB streams or aggregate data periodically
        for event_type in ["story_generated", "session_started", "api_request"]:
            type_events = self.analytics_repo.get_events_by_type(
                event_type, start_time, end_time, limit=10000
            )
            events.extend(type_events)
        
        return events
    
    def _calculate_overview_metrics(self, events: List[Analytics]) -> Dict[str, Any]:
        """Calculate overview metrics"""
        total_events = len(events)
        unique_users = len(set(e.user_id for e in events if e.user_id))
        unique_sessions = len(set(e.session_id for e in events if e.session_id))
        
        # Event breakdown by category
        category_counts = Counter(e.event_category for e in events)
        
        return {
            "total_events": total_events,
            "unique_users": unique_users,
            "unique_sessions": unique_sessions,
            "events_per_user": total_events / unique_users if unique_users > 0 else 0,
            "events_per_session": total_events / unique_sessions if unique_sessions > 0 else 0,
            "event_categories": dict(category_counts)
        }
    
    def _calculate_user_metrics(self, events: List[Analytics], 
                               start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Calculate user-related metrics"""
        # Active users
        active_users = set(e.user_id for e in events if e.user_id)
        
        # New users (signups)
        signup_events = [e for e in events if e.event_type == "user_signup"]
        new_users = len(signup_events)
        
        # User engagement
        user_event_counts = defaultdict(int)
        for event in events:
            if event.user_id:
                user_event_counts[event.user_id] += 1
        
        engagement_scores = list(user_event_counts.values())
        
        return {
            "active_users": len(active_users),
            "new_users": new_users,
            "returning_users": len(active_users) - new_users,
            "avg_events_per_user": statistics.mean(engagement_scores) if engagement_scores else 0,
            "median_events_per_user": statistics.median(engagement_scores) if engagement_scores else 0,
            "highly_engaged_users": sum(1 for count in engagement_scores if count > 10)
        }
    
    def _calculate_story_metrics(self, events: List[Analytics],
                                start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Calculate story-related metrics"""
        # Story generation events
        story_events = [e for e in events if e.event_type == "story_generated"]
        stories_generated = len(story_events)
        
        # Generation times
        generation_times = [
            e.properties.get("generation_time", 0) 
            for e in story_events
        ]
        
        # Token counts
        token_counts = [
            e.properties.get("token_count", 0)
            for e in story_events
        ]
        
        # Styles
        style_counts = Counter(
            e.properties.get("style", "unknown")
            for e in story_events
        )
        
        # Published stories
        published_events = [e for e in events if e.event_type == "story_published"]
        
        return {
            "stories_generated": stories_generated,
            "stories_published": len(published_events),
            "publish_rate": len(published_events) / stories_generated if stories_generated > 0 else 0,
            "avg_generation_time": statistics.mean(generation_times) if generation_times else 0,
            "median_generation_time": statistics.median(generation_times) if generation_times else 0,
            "total_tokens_generated": sum(token_counts),
            "avg_tokens_per_story": statistics.mean(token_counts) if token_counts else 0,
            "story_styles": dict(style_counts),
            "generation_rate": stories_generated / ((end_time - start_time).total_seconds() / 3600)  # per hour
        }
    
    def _calculate_performance_metrics(self, events: List[Analytics]) -> Dict[str, Any]:
        """Calculate performance metrics"""
        # API performance
        api_events = [e for e in events if e.event_type == "api_request"]
        
        response_times = [
            e.properties.get("response_time", 0)
            for e in api_events
        ]
        
        # Success rates by endpoint
        endpoint_stats = defaultdict(lambda: {"total": 0, "success": 0, "response_times": []})
        
        for event in api_events:
            endpoint = event.properties.get("endpoint", "unknown")
            endpoint_stats[endpoint]["total"] += 1
            if event.properties.get("success", False):
                endpoint_stats[endpoint]["success"] += 1
            endpoint_stats[endpoint]["response_times"].append(
                event.properties.get("response_time", 0)
            )
        
        # Calculate endpoint metrics
        endpoint_metrics = {}
        for endpoint, stats in endpoint_stats.items():
            endpoint_metrics[endpoint] = {
                "requests": stats["total"],
                "success_rate": stats["success"] / stats["total"] if stats["total"] > 0 else 0,
                "avg_response_time": statistics.mean(stats["response_times"]) if stats["response_times"] else 0,
                "p95_response_time": np.percentile(stats["response_times"], 95) if stats["response_times"] else 0
            }
        
        return {
            "total_api_requests": len(api_events),
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "median_response_time": statistics.median(response_times) if response_times else 0,
            "p95_response_time": np.percentile(response_times, 95) if response_times else 0,
            "p99_response_time": np.percentile(response_times, 99) if response_times else 0,
            "endpoints": endpoint_metrics
        }
    
    def _calculate_error_metrics(self, events: List[Analytics]) -> Dict[str, Any]:
        """Calculate error metrics"""
        error_events = [e for e in events if e.event_category == "error"]
        
        # Error types
        error_types = Counter(e.event_type for e in error_events)
        
        # Error rate
        total_events = len(events)
        error_rate = len(error_events) / total_events if total_events > 0 else 0
        
        # Recent errors
        recent_errors = sorted(
            error_events,
            key=lambda e: e.timestamp,
            reverse=True
        )[:10]
        
        return {
            "total_errors": len(error_events),
            "error_rate": error_rate,
            "error_types": dict(error_types),
            "recent_errors": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "type": e.event_type,
                    "message": e.properties.get("error_message", ""),
                    "user_id": e.user_id
                }
                for e in recent_errors
            ]
        }
    
    def _calculate_trends(self, events: List[Analytics], time_range: str) -> Dict[str, Any]:
        """Calculate trend data for charts"""
        # Determine appropriate interval
        if time_range in ["1h", "24h"]:
            interval = "hour"
        elif time_range in ["7d", "30d"]:
            interval = "day"
        else:
            interval = "week"
        
        # Group events by interval
        interval_data = defaultdict(lambda: {
            "events": 0,
            "users": set(),
            "stories": 0,
            "errors": 0
        })
        
        for event in events:
            if interval == "hour":
                key = event.timestamp.strftime("%Y-%m-%d %H:00")
            elif interval == "day":
                key = event.timestamp.strftime("%Y-%m-%d")
            else:
                key = event.timestamp.strftime("%Y-W%U")
            
            interval_data[key]["events"] += 1
            if event.user_id:
                interval_data[key]["users"].add(event.user_id)
            if event.event_type == "story_generated":
                interval_data[key]["stories"] += 1
            if event.event_category == "error":
                interval_data[key]["errors"] += 1
        
        # Convert to list format for charts
        trend_data = []
        for timestamp, data in sorted(interval_data.items()):
            trend_data.append({
                "timestamp": timestamp,
                "events": data["events"],
                "users": len(data["users"]),
                "stories": data["stories"],
                "errors": data["errors"]
            })
        
        return {
            "interval": interval,
            "data": trend_data
        }
    
    def get_user_analytics(self, user_id: str, time_range: str = "30d") -> Dict[str, Any]:
        """Get analytics for a specific user"""
        end_time = datetime.utcnow()
        start_time = self._get_start_time(time_range)
        
        # Get user events
        events = self.analytics_repo.get_user_events(user_id, start_time, end_time)
        
        # Get user's stories
        stories = self.story_repo.get_user_stories(user_id)
        
        # Calculate user metrics
        return {
            "user_id": user_id,
            "time_range": time_range,
            "total_events": len(events),
            "event_types": dict(Counter(e.event_type for e in events)),
            "stories": {
                "total": len(stories),
                "published": sum(1 for s in stories if s.status == StoryStatus.PUBLISHED),
                "avg_word_count": statistics.mean([s.metrics["word_count"] for s in stories]) if stories else 0,
                "total_words": sum(s.metrics["word_count"] for s in stories)
            },
            "activity_timeline": self._generate_activity_timeline(events),
            "engagement_score": self._calculate_engagement_score(events, stories)
        }
    
    def _generate_activity_timeline(self, events: List[Analytics]) -> List[Dict[str, Any]]:
        """Generate user activity timeline"""
        timeline = []
        
        for event in sorted(events, key=lambda e: e.timestamp, reverse=True)[:50]:
            timeline.append({
                "timestamp": event.timestamp.isoformat(),
                "event": event.event_type,
                "category": event.event_category,
                "properties": event.properties
            })
        
        return timeline
    
    def _calculate_engagement_score(self, events: List[Analytics], 
                                   stories: List[Story]) -> float:
        """Calculate user engagement score (0-100)"""
        score = 0
        
        # Event frequency (max 30 points)
        event_score = min(len(events) / 10, 30)
        score += event_score
        
        # Story creation (max 30 points)
        story_score = min(len(stories) * 3, 30)
        score += story_score
        
        # Story publishing (max 20 points)
        published = sum(1 for s in stories if s.status == StoryStatus.PUBLISHED)
        publish_score = min(published * 4, 20)
        score += publish_score
        
        # Feature usage (max 20 points)
        feature_events = ["voice_input_completed", "template_used", "story_shared"]
        features_used = sum(1 for e in events if e.event_type in feature_events)
        feature_score = min(features_used * 2, 20)
        score += feature_score
        
        return round(score, 1)
    
    def get_funnel_analysis(self, funnel_name: str, time_range: str = "7d") -> Dict[str, Any]:
        """Analyze conversion funnel"""
        funnels = {
            "story_creation": [
                "session_started",
                "story_started",
                "story_generated",
                "story_published"
            ],
            "user_onboarding": [
                "user_signup",
                "session_started",
                "story_started",
                "story_generated"
            ],
            "voice_flow": [
                "voice_input_started",
                "voice_input_completed",
                "story_generated"
            ]
        }
        
        if funnel_name not in funnels:
            return {"error": f"Unknown funnel: {funnel_name}"}
        
        funnel_steps = funnels[funnel_name]
        end_time = datetime.utcnow()
        start_time = self._get_start_time(time_range)
        
        # Get all relevant events
        step_counts = {}
        conversion_rates = {}
        
        for i, step in enumerate(funnel_steps):
            events = self.analytics_repo.get_events_by_type(step, start_time, end_time)
            step_counts[step] = len(events)
            
            if i > 0:
                prev_count = step_counts[funnel_steps[i-1]]
                if prev_count > 0:
                    conversion_rates[f"{funnel_steps[i-1]}_to_{step}"] = len(events) / prev_count
                else:
                    conversion_rates[f"{funnel_steps[i-1]}_to_{step}"] = 0
        
        # Overall conversion rate
        if step_counts[funnel_steps[0]] > 0:
            overall_conversion = step_counts[funnel_steps[-1]] / step_counts[funnel_steps[0]]
        else:
            overall_conversion = 0
        
        return {
            "funnel_name": funnel_name,
            "time_range": time_range,
            "steps": funnel_steps,
            "step_counts": step_counts,
            "conversion_rates": conversion_rates,
            "overall_conversion": overall_conversion,
            "drop_off_points": self._identify_drop_off_points(conversion_rates)
        }
    
    def _identify_drop_off_points(self, conversion_rates: Dict[str, float]) -> List[Dict[str, Any]]:
        """Identify major drop-off points in funnel"""
        drop_offs = []
        
        for transition, rate in conversion_rates.items():
            if rate < 0.5:  # Less than 50% conversion
                drop_offs.append({
                    "transition": transition,
                    "conversion_rate": rate,
                    "severity": "high" if rate < 0.2 else "medium"
                })
        
        return sorted(drop_offs, key=lambda x: x["conversion_rate"])


class ReportGenerator:
    """Generate analytics reports"""
    
    def __init__(self, processor: AnalyticsProcessor):
        self.processor = processor
    
    def generate_daily_report(self) -> Dict[str, Any]:
        """Generate daily analytics report"""
        metrics = self.processor.get_dashboard_metrics("24h")
        
        report = {
            "report_type": "daily",
            "generated_at": datetime.utcnow().isoformat(),
            "summary": self._generate_summary(metrics),
            "metrics": metrics,
            "insights": self._generate_insights(metrics),
            "recommendations": self._generate_recommendations(metrics)
        }
        
        return report
    
    def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate weekly analytics report"""
        current_week = self.processor.get_dashboard_metrics("7d")
        previous_week_end = datetime.utcnow() - timedelta(days=7)
        previous_week_start = previous_week_end - timedelta(days=7)
        
        # Get previous week data for comparison
        # (simplified - would need custom date range support)
        
        report = {
            "report_type": "weekly",
            "generated_at": datetime.utcnow().isoformat(),
            "current_week": current_week,
            "week_over_week_changes": self._calculate_wow_changes(current_week),
            "top_users": self._get_top_users(current_week),
            "popular_content": self._get_popular_content(),
            "performance_summary": self._generate_performance_summary(current_week)
        }
        
        return report
    
    def _generate_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary"""
        return {
            "active_users": metrics["user_metrics"]["active_users"],
            "stories_generated": metrics["story_metrics"]["stories_generated"],
            "avg_response_time": round(metrics["performance_metrics"]["avg_response_time"], 2),
            "error_rate": round(metrics["error_metrics"]["error_rate"] * 100, 2),
            "key_highlight": self._get_key_highlight(metrics)
        }
    
    def _generate_insights(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate actionable insights from metrics"""
        insights = []
        
        # User engagement insights
        if metrics["user_metrics"]["new_users"] > metrics["user_metrics"]["returning_users"]:
            insights.append("New user acquisition is strong, focus on retention strategies")
        
        # Story generation insights
        publish_rate = metrics["story_metrics"]["publish_rate"]
        if publish_rate < 0.5:
            insights.append(f"Only {publish_rate*100:.1f}% of generated stories are published - investigate barriers")
        
        # Performance insights
        p95_response = metrics["performance_metrics"]["p95_response_time"]
        if p95_response > 2.0:
            insights.append(f"P95 response time is {p95_response:.2f}s - consider performance optimization")
        
        # Error insights
        if metrics["error_metrics"]["error_rate"] > 0.05:
            insights.append("Error rate exceeds 5% - review error logs and implement fixes")
        
        return insights
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate recommendations based on metrics"""
        recommendations = []
        
        # Check story styles usage
        story_styles = metrics["story_metrics"]["story_styles"]
        if len(story_styles) == 1:
            recommendations.append({
                "category": "feature_adoption",
                "recommendation": "Users are only using one story style - promote other styles",
                "priority": "medium"
            })
        
        # Check API performance
        slow_endpoints = [
            endpoint for endpoint, stats in metrics["performance_metrics"]["endpoints"].items()
            if stats["avg_response_time"] > 1.0
        ]
        if slow_endpoints:
            recommendations.append({
                "category": "performance",
                "recommendation": f"Optimize slow endpoints: {', '.join(slow_endpoints)}",
                "priority": "high"
            })
        
        # Check user engagement
        avg_events = metrics["user_metrics"]["avg_events_per_user"]
        if avg_events < 5:
            recommendations.append({
                "category": "engagement",
                "recommendation": "Low user engagement - implement engagement features",
                "priority": "high"
            })
        
        return recommendations
    
    def _calculate_wow_changes(self, current_week: Dict[str, Any]) -> Dict[str, float]:
        """Calculate week-over-week changes (simplified)"""
        # This would compare with previous week data
        return {
            "users": 15.2,  # % change
            "stories": 22.5,
            "errors": -8.3,
            "avg_response_time": -5.1
        }
    
    def _get_top_users(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get top users by activity (would query from events)"""
        # Simplified version
        return [
            {"user_id": "user123", "events": 152, "stories": 12},
            {"user_id": "user456", "events": 98, "stories": 8},
            {"user_id": "user789", "events": 87, "stories": 6}
        ]
    
    def _get_popular_content(self) -> List[Dict[str, Any]]:
        """Get popular content themes (would analyze from stories)"""
        # Simplified version
        return [
            {"theme": "tech startups", "count": 45},
            {"theme": "community events", "count": 38},
            {"theme": "local business", "count": 32}
        ]
    
    def _generate_performance_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate performance summary"""
        return {
            "uptime": 99.9,  # Would calculate from monitoring
            "avg_response_time": metrics["performance_metrics"]["avg_response_time"],
            "peak_load": {
                "timestamp": "2024-01-15T14:30:00Z",
                "requests_per_minute": 450
            },
            "resource_usage": {
                "cpu_avg": 45.2,
                "memory_avg": 62.8,
                "storage_used_gb": 12.4
            }
        }
    
    def _get_key_highlight(self, metrics: Dict[str, Any]) -> str:
        """Get key highlight for summary"""
        stories = metrics["story_metrics"]["stories_generated"]
        users = metrics["user_metrics"]["active_users"]
        
        if stories > 100:
            return f"Record high: {stories} stories generated!"
        elif users > 50:
            return f"Strong engagement: {users} active users"
        else:
            return "Steady growth in user engagement"


# Global analytics instance
analytics_collector = AnalyticsCollector()
analytics_processor = AnalyticsProcessor()
report_generator = ReportGenerator(analytics_processor)


# Convenience functions for tracking
def track_event(event_type: str, **kwargs):
    """Track an analytics event"""
    analytics_collector.track_event(event_type, **kwargs)


def track_api_call(endpoint: str, method: str, status_code: int, response_time: float, **kwargs):
    """Track API call"""
    analytics_collector.track_api_call(endpoint, method, status_code, response_time, **kwargs)


def get_analytics_dashboard(time_range: str = "24h") -> Dict[str, Any]:
    """Get analytics dashboard data"""
    return analytics_processor.get_dashboard_metrics(time_range)


def generate_report(report_type: str = "daily") -> Dict[str, Any]:
    """Generate analytics report"""
    if report_type == "daily":
        return report_generator.generate_daily_report()
    elif report_type == "weekly":
        return report_generator.generate_weekly_report()
    else:
        return {"error": f"Unknown report type: {report_type}"}