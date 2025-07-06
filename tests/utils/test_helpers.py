"""
Test helper utilities and shared testing functions
"""
import time
import json
import hashlib
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import jwt
from faker import Faker
from dataclasses import dataclass, asdict


fake = Faker()


@dataclass
class TestUser:
    """Test user data class"""
    id: str
    email: str
    role: str = "user"
    api_key: Optional[str] = None
    token: Optional[str] = None


@dataclass
class TestStory:
    """Test story data class"""
    id: str
    core_idea: str
    style: str
    content: str
    author_id: str
    created_at: datetime
    metadata: Dict[str, Any]


class TestDataGenerator:
    """Generate test data for various scenarios"""
    
    @staticmethod
    def generate_user(role: str = "user") -> TestUser:
        """Generate a test user"""
        user_id = fake.uuid4()
        email = fake.email()
        api_key = TestDataGenerator.generate_api_key()
        token = TestDataGenerator.generate_jwt_token(user_id, role)
        
        return TestUser(
            id=user_id,
            email=email,
            role=role,
            api_key=api_key,
            token=token
        )
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a test API key"""
        prefix = "sk_test_"
        random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        return f"{prefix}{random_part}"
    
    @staticmethod
    def generate_jwt_token(user_id: str, role: str = "user", 
                          expires_in: int = 3600) -> str:
        """Generate a test JWT token"""
        payload = {
            "user_id": user_id,
            "role": role,
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, "test-secret", algorithm="HS256")
    
    @staticmethod
    def generate_story_idea() -> str:
        """Generate a realistic Richmond story idea"""
        templates = [
            "Richmond's {industry} scene is transforming with {innovation}",
            "Local {profession} are building {solution} to address {problem}",
            "{neighborhood} is becoming Richmond's hub for {activity}",
            "How Richmond's {culture} influences its {business} community",
            "The story of {company} and their impact on Richmond's {sector}"
        ]
        
        variables = {
            "industry": ["tech", "food", "arts", "startup", "healthcare"],
            "innovation": ["AI solutions", "sustainable practices", "community programs", "creative spaces"],
            "profession": ["entrepreneurs", "artists", "developers", "chefs", "educators"],
            "solution": ["platforms", "applications", "initiatives", "networks", "systems"],
            "problem": ["urban challenges", "education gaps", "healthcare access", "economic inequality"],
            "neighborhood": ["Scott's Addition", "Carytown", "The Fan", "Church Hill", "Manchester"],
            "activity": ["innovation", "creativity", "entrepreneurship", "cultural events", "tech meetups"],
            "culture": ["music scene", "food culture", "historic preservation", "river city identity"],
            "business": ["startup", "restaurant", "creative", "technology", "social impact"],
            "company": ["TechRVA", "StartupVA", "RVA Labs", "River City Ventures", "Richmond Innovates"],
            "sector": ["economy", "community", "education system", "cultural landscape", "tech ecosystem"]
        }
        
        template = random.choice(templates)
        for var, options in variables.items():
            if f"{{{var}}}" in template:
                template = template.replace(f"{{{var}}}", random.choice(options))
        
        return template
    
    @staticmethod
    def generate_story_content(style: str = "short_post") -> str:
        """Generate story content based on style"""
        base_content = fake.paragraph(nb_sentences=5)
        
        if style == "short_post":
            return base_content
        elif style == "long_post":
            return "\n\n".join([fake.paragraph(nb_sentences=5) for _ in range(3)])
        elif style == "blog_post":
            sections = []
            for i in range(5):
                section_title = fake.sentence(nb_words=4).rstrip('.')
                section_content = "\n\n".join([fake.paragraph(nb_sentences=4) for _ in range(2)])
                sections.append(f"## {section_title}\n\n{section_content}")
            return "\n\n".join(sections)
        
        return base_content
    
    @staticmethod
    def generate_richmond_context() -> List[str]:
        """Generate Richmond-specific context snippets"""
        contexts = [
            "Richmond's tech ecosystem has grown 40% in the past five years, attracting talent from major coastal cities.",
            "Scott's Addition has transformed from an industrial district to Richmond's innovation hub, hosting over 50 tech companies.",
            "The Greater Richmond Partnership reports that tech jobs in the region pay an average of $85,000 annually.",
            "Local success stories include Snagajob, CarLotz, and CoStar Group, proving Richmond can nurture unicorn companies.",
            "Richmond's quality of life, with its vibrant arts scene and outdoor activities, attracts remote workers and entrepreneurs.",
            "The city's universities, including VCU and University of Richmond, produce over 5,000 STEM graduates annually.",
            "Richmond's cost of living is 30% lower than Northern Virginia, making it attractive for startups.",
            "The James River and extensive park system provide work-life balance that tech professionals seek.",
            "Historic neighborhoods like The Fan and Church Hill offer unique character not found in typical tech hubs.",
            "Richmond's food scene, recognized nationally, creates networking opportunities and community connections."
        ]
        
        return random.sample(contexts, k=random.randint(3, 5))


class TestMetrics:
    """Calculate and track test metrics"""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.status_codes: List[int] = []
        self.errors: List[str] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def start(self):
        """Start metrics collection"""
        self.start_time = time.time()
    
    def stop(self):
        """Stop metrics collection"""
        self.end_time = time.time()
    
    def add_request(self, response_time: float, status_code: int, error: Optional[str] = None):
        """Add a request to metrics"""
        self.response_times.append(response_time)
        self.status_codes.append(status_code)
        if error:
            self.errors.append(error)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        if not self.response_times:
            return {"error": "No data collected"}
        
        import statistics
        
        success_count = sum(1 for code in self.status_codes if 200 <= code < 300)
        total_count = len(self.status_codes)
        
        return {
            "total_requests": total_count,
            "successful_requests": success_count,
            "failed_requests": total_count - success_count,
            "success_rate": success_count / total_count if total_count > 0 else 0,
            "avg_response_time": statistics.mean(self.response_times),
            "min_response_time": min(self.response_times),
            "max_response_time": max(self.response_times),
            "p50_response_time": statistics.median(self.response_times),
            "p95_response_time": statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) > 20 else max(self.response_times),
            "p99_response_time": statistics.quantiles(self.response_times, n=100)[98] if len(self.response_times) > 100 else max(self.response_times),
            "total_errors": len(self.errors),
            "duration": self.end_time - self.start_time if self.end_time and self.start_time else None,
            "requests_per_second": total_count / (self.end_time - self.start_time) if self.end_time and self.start_time else None
        }


class TestValidator:
    """Validate test responses and data"""
    
    @staticmethod
    def validate_story_response(response_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate story generation response"""
        errors = []
        
        # Check required fields
        if "story" not in response_data:
            errors.append("Missing 'story' field")
        elif not isinstance(response_data["story"], str):
            errors.append("'story' field must be a string")
        elif len(response_data["story"]) < 10:
            errors.append("Story content too short")
        
        # Check metadata
        if "metadata" in response_data:
            metadata = response_data["metadata"]
            required_metadata = ["request_id", "style", "response_time"]
            for field in required_metadata:
                if field not in metadata:
                    errors.append(f"Missing metadata field: {field}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_api_response(response, expected_status: int = 200) -> Tuple[bool, List[str]]:
        """Validate API response"""
        errors = []
        
        # Check status code
        if response.status_code != expected_status:
            errors.append(f"Expected status {expected_status}, got {response.status_code}")
        
        # Check content type
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            errors.append(f"Expected JSON content type, got {content_type}")
        
        # Try to parse JSON
        try:
            response_data = response.json()
        except:
            errors.append("Response is not valid JSON")
            return False, errors
        
        # Check for error structure in error responses
        if response.status_code >= 400:
            if "error" not in response_data:
                errors.append("Error response missing 'error' field")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_security_headers(headers: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Validate security headers"""
        errors = []
        required_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block'
        }
        
        for header, expected_value in required_headers.items():
            if header not in headers:
                errors.append(f"Missing security header: {header}")
            elif headers[header] != expected_value:
                errors.append(f"Invalid {header}: expected '{expected_value}', got '{headers[header]}'")
        
        return len(errors) == 0, errors


class MockDataBuilder:
    """Build complex mock data structures"""
    
    @staticmethod
    def build_conversation_history(turns: int = 5) -> List[Dict[str, Any]]:
        """Build mock conversation history"""
        history = []
        for i in range(turns):
            history.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": fake.sentence(),
                "timestamp": (datetime.utcnow() - timedelta(minutes=turns-i)).isoformat()
            })
        return history
    
    @staticmethod
    def build_vector_search_results(count: int = 5) -> List[Dict[str, Any]]:
        """Build mock vector search results"""
        results = []
        for i in range(count):
            results.append({
                "id": fake.uuid4(),
                "content": TestDataGenerator.generate_richmond_context()[0],
                "score": random.uniform(0.7, 0.95),
                "metadata": {
                    "source": random.choice(["richmond_tech.md", "richmond_culture.md", "richmond_economy.md"]),
                    "chunk_id": i,
                    "timestamp": fake.date_time_this_year().isoformat()
                }
            })
        return sorted(results, key=lambda x: x["score"], reverse=True)
    
    @staticmethod
    def build_batch_request(count: int = 10) -> Dict[str, Any]:
        """Build batch story generation request"""
        stories = []
        for _ in range(count):
            stories.append({
                "core_idea": TestDataGenerator.generate_story_idea(),
                "style": random.choice(["short_post", "long_post", "blog_post"]),
                "metadata": {
                    "batch_id": fake.uuid4(),
                    "priority": random.choice(["high", "medium", "low"])
                }
            })
        
        return {
            "stories": stories,
            "parallel": True,
            "webhook_url": fake.url()
        }


def create_test_file(filename: str, content: str, directory: str = "/tmp") -> str:
    """Create a test file and return its path"""
    import os
    filepath = os.path.join(directory, filename)
    with open(filepath, 'w') as f:
        f.write(content)
    return filepath


def generate_test_audio_data(duration_seconds: float = 3.0, sample_rate: int = 44100) -> bytes:
    """Generate test audio data in WAV format"""
    import struct
    import math
    
    # Generate sine wave
    frequency = 440  # A4 note
    samples = []
    for i in range(int(sample_rate * duration_seconds)):
        sample = math.sin(2 * math.pi * frequency * i / sample_rate)
        samples.append(int(sample * 32767))  # Convert to 16-bit
    
    # Create WAV header
    num_samples = len(samples)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    
    wav_header = struct.pack(
        '<4sI4s4sIHHIIHH',
        b'RIFF',
        36 + num_samples * 2,  # File size - 8
        b'WAVE',
        b'fmt ',
        16,  # Subchunk1Size
        1,   # AudioFormat (PCM)
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample
    )
    
    wav_data_header = struct.pack('<4sI', b'data', num_samples * 2)
    
    # Pack samples
    wav_samples = b''.join(struct.pack('<h', sample) for sample in samples)
    
    return wav_header + wav_data_header + wav_samples


def calculate_content_hash(content: str) -> str:
    """Calculate hash of content for comparison"""
    return hashlib.sha256(content.encode()).hexdigest()


def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1) -> bool:
    """Wait for a condition to become true"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    return False


class APITester:
    """Helper class for API testing"""
    
    def __init__(self, client):
        self.client = client
        self.metrics = TestMetrics()
    
    def test_endpoint(self, method: str, endpoint: str, 
                     data: Optional[Dict] = None,
                     headers: Optional[Dict] = None,
                     expected_status: int = 200) -> Dict[str, Any]:
        """Test an endpoint and collect metrics"""
        headers = headers or {}
        if data and 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        
        start_time = time.time()
        
        if method.upper() == 'GET':
            response = self.client.get(endpoint, headers=headers)
        elif method.upper() == 'POST':
            response = self.client.post(endpoint, json=data, headers=headers)
        elif method.upper() == 'PUT':
            response = self.client.put(endpoint, json=data, headers=headers)
        elif method.upper() == 'DELETE':
            response = self.client.delete(endpoint, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response_time = time.time() - start_time
        
        # Collect metrics
        self.metrics.add_request(response_time, response.status_code)
        
        # Validate response
        is_valid, errors = TestValidator.validate_api_response(response, expected_status)
        
        return {
            "response": response,
            "response_time": response_time,
            "is_valid": is_valid,
            "errors": errors,
            "data": response.json() if response.status_code < 500 else None
        }