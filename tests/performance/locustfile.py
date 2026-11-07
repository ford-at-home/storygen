"""
Locust load testing configuration for Richmond StoryGen
"""
from locust import HttpUser, task, between
import random
import json


class StoryGenUser(HttpUser):
    """Simulated user behavior for load testing"""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """Initialize user session"""
        # Could add authentication here if needed
        self.story_ideas = [
            "Richmond tech professionals returning from Silicon Valley",
            "The transformation of Scott's Addition into a tech hub",
            "Local entrepreneurs building community-focused startups",
            "Richmond's food scene inspiring tech innovation",
            "The intersection of history and technology in RVA",
            "VCU graduates launching successful startups",
            "Remote workers choosing Richmond for quality of life",
            "The growth of Richmond's startup ecosystem",
            "How the James River shapes Richmond's tech culture",
            "Richmond's creative class driving innovation"
        ]
        
        self.styles = ["short_post", "long_post", "blog_post"]
    
    @task(3)
    def generate_story(self):
        """Generate a story - most common operation"""
        story_idea = random.choice(self.story_ideas)
        style = random.choice(self.styles)
        
        with self.client.post(
            "/generate-story",
            json={
                "core_idea": story_idea,
                "style": style
            },
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "story" in data and len(data["story"]) > 100:
                    response.success()
                else:
                    response.failure("Invalid story response")
            else:
                response.failure(f"Got status code {response.status_code}")
    
    @task(2)
    def check_health(self):
        """Check API health"""
        self.client.get("/health")
    
    @task(1)
    def get_styles(self):
        """Get available styles"""
        self.client.get("/styles")
    
    @task(1)
    def get_stats(self):
        """Get API statistics"""
        self.client.get("/stats")
    
    @task(1)
    def browse_docs(self):
        """Browse API documentation"""
        self.client.get("/")


class PowerUser(HttpUser):
    """Power user with more intensive usage patterns"""
    
    wait_time = between(0.5, 2)  # Shorter wait times
    
    def on_start(self):
        """Initialize power user session"""
        self.conversation_id = None
        self.session_id = f"power-user-{random.randint(1000, 9999)}"
    
    @task(5)
    def generate_multiple_stories(self):
        """Generate multiple stories in succession"""
        for _ in range(3):
            style = random.choice(["short_post", "long_post", "blog_post"])
            self.client.post(
                "/generate-story",
                json={
                    "core_idea": f"Richmond innovation story {random.randint(1, 100)}",
                    "style": style
                }
            )
    
    @task(3)
    def start_conversation(self):
        """Start a conversation flow"""
        response = self.client.post(
            "/conversation/start",
            json={
                "session_id": self.session_id,
                "initial_message": "I want to write about Richmond's tech scene"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.conversation_id = data.get("conversation_id")
    
    @task(2)
    def continue_conversation(self):
        """Continue existing conversation"""
        if self.conversation_id:
            self.client.post(
                "/conversation/message",
                json={
                    "conversation_id": self.conversation_id,
                    "message": "Tell me more about startup success stories"
                }
            )
    
    @task(1)
    def batch_generation(self):
        """Test batch story generation"""
        stories = [
            {
                "core_idea": f"Richmond story {i}",
                "style": random.choice(["short_post", "long_post"])
            }
            for i in range(5)
        ]
        
        self.client.post(
            "/stories/batch",
            json={
                "stories": stories,
                "parallel": True
            }
        )


class MobileUser(HttpUser):
    """Mobile user with different behavior patterns"""
    
    wait_time = between(2, 8)  # Longer wait times
    
    @task(4)
    def quick_story_generation(self):
        """Generate short stories suitable for mobile"""
        self.client.post(
            "/generate-story",
            json={
                "core_idea": "Quick Richmond tech update",
                "style": "short_post"  # Always short for mobile
            },
            headers={
                "User-Agent": "Mobile App 1.0"
            }
        )
    
    @task(2)
    def voice_transcription(self):
        """Simulate voice input"""
        # Simulate voice transcription endpoint
        self.client.post(
            "/voice/transcribe",
            files={
                "audio": ("recording.wav", b"fake audio data", "audio/wav")
            }
        )
    
    @task(1)
    def check_connection(self):
        """Frequent health checks on mobile"""
        self.client.get("/health")


class AdminUser(HttpUser):
    """Admin user checking system metrics"""
    
    wait_time = between(5, 10)
    
    def on_start(self):
        """Admin authentication"""
        # Would include admin auth token
        self.headers = {
            "Authorization": "Bearer admin-token"
        }
    
    @task(3)
    def check_system_stats(self):
        """Monitor system statistics"""
        self.client.get("/stats", headers=self.headers)
        self.client.get("/admin/metrics", headers=self.headers)
    
    @task(1)
    def check_cache_status(self):
        """Check cache performance"""
        self.client.get("/admin/cache/stats", headers=self.headers)
    
    @task(1)
    def run_health_checks(self):
        """Comprehensive health checks"""
        endpoints = ["/health", "/health/db", "/health/cache", "/health/external"]
        for endpoint in endpoints:
            self.client.get(endpoint, headers=self.headers)