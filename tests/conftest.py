"""
pytest configuration and shared fixtures for all tests
"""
import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import boto3
from moto import mock_aws
import pinecone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app
from config import Config
from pinecone.vectorstore import init_vectorstore
from bedrock.bedrock_llm import get_bedrock_client


@pytest.fixture
def app():
    """Create and configure a test Flask application"""
    flask_app.config['TESTING'] = True
    flask_app.config['DEBUG'] = False
    return flask_app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test runner for CLI commands"""
    return app.test_cli_runner()


@pytest.fixture
def test_config(monkeypatch):
    """Create test configuration with mocked environment variables"""
    # Set test environment variables
    test_env = {
        "PINECONE_API_KEY": "test-pinecone-key",
        "AWS_ACCESS_KEY_ID": "test-aws-key",
        "AWS_SECRET_ACCESS_KEY": "test-aws-secret",
        "OPENAI_API_KEY": "test-openai-key",
        "AWS_REGION": "us-east-1",
        "PINECONE_ENVIRONMENT": "test-environment",
        "PINECONE_INDEX_NAME": "test-richmond-context",
        "FLASK_PORT": "5001",
        "FLASK_DEBUG": "false",
        "BEDROCK_MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0",
        "DEFAULT_TEMPERATURE": "0.7",
        "SHORT_POST_TOKENS": "1024",
        "LONG_POST_TOKENS": "2048",
        "BLOG_POST_TOKENS": "4096",
        "CHUNK_SIZE": "1000",
        "CHUNK_OVERLAP": "100"
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    # Create test configuration instance
    config = Config()
    
    # Create temporary directories for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        config.BASE_DIR = tmppath
        config.DATA_DIR = tmppath / "data"
        config.PROMPTS_DIR = tmppath / "prompts"
        
        # Create directories
        config.DATA_DIR.mkdir(exist_ok=True)
        config.PROMPTS_DIR.mkdir(exist_ok=True)
        
        # Create test prompt files
        story_prompt = config.PROMPTS_DIR / "story_prompt.txt"
        story_prompt.write_text("""
You are a storyteller for Richmond, Virginia. Generate a {{ style }} about:
{{ core_idea }}

Context:
{{ retrieved_chunks }}

Create an engaging story that captures Richmond's unique character.
""")
        
        enhanced_prompt = config.PROMPTS_DIR / "enhanced_story_prompt.txt"
        enhanced_prompt.write_text("""
You are an expert storyteller crafting narratives about Richmond, Virginia.

Style: {{ style }}
Core Idea: {{ core_idea }}

Richmond Context:
{{ retrieved_chunks }}

Create a compelling, authentic story that:
- Captures Richmond's unique blend of history and innovation
- Includes specific local details and references
- Reflects the community's voice and values
- Engages readers with vivid descriptions
""")
        
        yield config


@pytest.fixture
def mock_pinecone(monkeypatch):
    """Mock Pinecone vector store"""
    mock_index = Mock()
    mock_index.query.return_value = {
        'matches': [
            {
                'id': 'doc1',
                'score': 0.95,
                'metadata': {
                    'text': 'Richmond tech scene is thriving with new startups.'
                }
            },
            {
                'id': 'doc2',
                'score': 0.89,
                'metadata': {
                    'text': 'Scott\'s Addition has become Richmond\'s innovation district.'
                }
            },
            {
                'id': 'doc3',
                'score': 0.85,
                'metadata': {
                    'text': 'Richmond entrepreneurs are building community-focused businesses.'
                }
            }
        ]
    }
    
    mock_pinecone_init = Mock()
    mock_pinecone_index = Mock(return_value=mock_index)
    
    monkeypatch.setattr('pinecone.init', mock_pinecone_init)
    monkeypatch.setattr('pinecone.Index', mock_pinecone_index)
    
    return mock_index


@pytest.fixture
def mock_bedrock():
    """Mock AWS Bedrock client"""
    with mock_aws():
        # Create mock Bedrock client
        client = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Mock the invoke_model response
        def mock_invoke_model(**kwargs):
            return {
                'body': Mock(read=lambda: b'{"completion": "This is a test story about Richmond tech scene."}'),
                'contentType': 'application/json'
            }
        
        client.invoke_model = mock_invoke_model
        yield client


@pytest.fixture
def mock_bedrock_embeddings(monkeypatch):
    """Mock Bedrock embeddings"""
    class MockEmbeddings:
        def embed_documents(self, texts):
            # Return mock embeddings (1536-dimensional vectors)
            return [[0.1] * 1536 for _ in texts]
        
        def embed_query(self, text):
            # Return mock query embedding
            return [0.1] * 1536
    
    mock_embeddings = MockEmbeddings()
    monkeypatch.setattr('langchain.embeddings.BedrockEmbeddings', lambda **kwargs: mock_embeddings)
    return mock_embeddings


@pytest.fixture
def mock_openai(monkeypatch):
    """Mock OpenAI Whisper API for voice transcription"""
    class MockWhisper:
        class Audio:
            class Transcriptions:
                def create(self, **kwargs):
                    return Mock(text="This is a transcribed voice message about Richmond tech community.")
            
            transcriptions = Transcriptions()
        
        audio = Audio()
    
    mock_client = MockWhisper()
    monkeypatch.setattr('openai.OpenAI', lambda **kwargs: mock_client)
    return mock_client


@pytest.fixture
def sample_story_request():
    """Sample story generation request data"""
    return {
        "core_idea": "Richmond tech professionals are returning from coastal cities to build innovative startups",
        "style": "short_post"
    }


@pytest.fixture
def sample_conversation_request():
    """Sample conversation request data"""
    return {
        "session_id": "test-session-123",
        "message": "Tell me about Richmond's tech scene",
        "context": {
            "previous_messages": [],
            "user_preferences": {
                "style": "conversational",
                "topics": ["technology", "entrepreneurship"]
            }
        }
    }


@pytest.fixture
def sample_voice_data():
    """Sample voice recording data (WAV format header)"""
    # Create a minimal valid WAV file header
    wav_header = b'RIFF' + b'\x00' * 4 + b'WAVE' + b'fmt ' + b'\x10\x00\x00\x00'
    wav_header += b'\x01\x00\x02\x00' + b'\x44\xac\x00\x00' + b'\x10\xb1\x02\x00'
    wav_header += b'\x04\x00\x10\x00' + b'data' + b'\x00' * 4
    # Add some audio data
    audio_data = b'\x00\x01' * 1000
    return wav_header + audio_data


@pytest.fixture
def auth_headers():
    """Sample authentication headers"""
    return {
        "Authorization": "Bearer test-token-123",
        "Content-Type": "application/json"
    }


@pytest.fixture(autouse=True)
def reset_request_stats():
    """Reset request statistics before each test"""
    from app import request_stats
    request_stats.update({
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "average_response_time": 0
    })


@pytest.fixture
def performance_monitor():
    """Monitor performance metrics during tests"""
    import time
    import psutil
    import threading
    
    class PerformanceMonitor:
        def __init__(self):
            self.metrics = {
                "cpu_percent": [],
                "memory_percent": [],
                "response_times": [],
                "active_threads": []
            }
            self.monitoring = False
            self.monitor_thread = None
        
        def start(self):
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor)
            self.monitor_thread.start()
        
        def stop(self):
            self.monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join()
        
        def _monitor(self):
            while self.monitoring:
                self.metrics["cpu_percent"].append(psutil.cpu_percent(interval=0.1))
                self.metrics["memory_percent"].append(psutil.virtual_memory().percent)
                self.metrics["active_threads"].append(threading.active_count())
                time.sleep(0.1)
        
        def add_response_time(self, time):
            self.metrics["response_times"].append(time)
        
        def get_summary(self):
            def safe_avg(lst):
                return sum(lst) / len(lst) if lst else 0
            
            return {
                "avg_cpu_percent": safe_avg(self.metrics["cpu_percent"]),
                "max_cpu_percent": max(self.metrics["cpu_percent"]) if self.metrics["cpu_percent"] else 0,
                "avg_memory_percent": safe_avg(self.metrics["memory_percent"]),
                "max_memory_percent": max(self.metrics["memory_percent"]) if self.metrics["memory_percent"] else 0,
                "avg_response_time": safe_avg(self.metrics["response_times"]),
                "max_response_time": max(self.metrics["response_times"]) if self.metrics["response_times"] else 0,
                "avg_threads": safe_avg(self.metrics["active_threads"]),
                "max_threads": max(self.metrics["active_threads"]) if self.metrics["active_threads"] else 0
            }
    
    monitor = PerformanceMonitor()
    yield monitor
    monitor.stop()


@pytest.fixture
def security_headers():
    """Expected security headers for responses"""
    return {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block'
    }


# Markers for test categorization
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "requires_api_keys: Tests requiring real API keys")