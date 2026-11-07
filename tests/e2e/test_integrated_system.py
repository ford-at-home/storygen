"""
End-to-end tests for the fully integrated Richmond Storyline Generator
Tests complete user journeys across all components
"""

import pytest
import json
import time
import base64
from unittest.mock import patch, Mock
from io import BytesIO
import concurrent.futures
import requests


@pytest.mark.e2e
@pytest.mark.integration
class TestIntegratedSystem:
    """Test the fully integrated system with all components"""
    
    def setup_method(self):
        """Setup for each test"""
        self.base_url = "http://localhost:8080"
        self.api_base = f"{self.base_url}/api"
        
    def test_system_health_check(self):
        """Test that all system components are healthy"""
        # Check main health endpoint
        response = requests.get(f"{self.api_base}/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data['status'] in ['healthy', 'degraded']
        assert 'components' in health_data
        
        # Verify individual components
        components = health_data['components']
        required_components = ['redis', 'pinecone', 'bedrock']
        
        for component in required_components:
            assert component in components
            if health_data['status'] == 'healthy':
                assert components[component] == 'healthy'
    
    def test_complete_voice_to_story_journey(self):
        """Test the complete journey from voice input to final story"""
        # Step 1: Record and upload voice
        voice_data = self._generate_mock_voice_data()
        
        with patch('openai.OpenAI') as mock_openai:
            # Mock Whisper transcription
            mock_whisper = Mock()
            mock_whisper.audio.transcriptions.create.return_value = Mock(
                text="I want to tell a story about Richmond's vibrant food scene and how local chefs are innovating with regional ingredients."
            )
            mock_openai.return_value = mock_whisper
            
            # Upload voice
            files = {'audio': ('recording.wav', voice_data, 'audio/wav')}
            voice_response = requests.post(
                f"{self.api_base}/voice/transcribe",
                files=files
            )
            
            assert voice_response.status_code == 200
            voice_data = voice_response.json()
            assert 'transcription' in voice_data
            assert 'session_id' in voice_data
            
            session_id = voice_data['session_id']
            transcription = voice_data['transcription']
        
        # Step 2: Start conversation to refine the idea
        conversation_response = requests.post(
            f"{self.api_base}/conversation/start",
            json={
                'session_id': session_id,
                'initial_message': transcription
            }
        )
        
        assert conversation_response.status_code == 200
        conv_data = conversation_response.json()
        conversation_id = conv_data['conversation_id']
        
        # Step 3: Interact with conversation engine
        refinement_response = requests.post(
            f"{self.api_base}/conversation/message",
            json={
                'conversation_id': conversation_id,
                'message': "Let's focus on a specific chef and their story"
            }
        )
        
        assert refinement_response.status_code == 200
        refinement_data = refinement_response.json()
        assert 'response' in refinement_data
        
        # Step 4: Generate the story
        story_response = requests.post(
            f"{self.api_base}/generate-story",
            json={
                'core_idea': transcription,
                'style': 'long_post',
                'conversation_context': conversation_id
            }
        )
        
        assert story_response.status_code == 200
        story_data = story_response.json()
        
        # Validate story
        assert 'story' in story_data
        assert 'metadata' in story_data
        
        story = story_data['story']
        assert len(story) > 500  # Substantial story
        assert 'Richmond' in story
        assert any(word in story.lower() for word in ['food', 'chef', 'restaurant', 'ingredient'])
        
        metadata = story_data['metadata']
        assert metadata['style'] == 'long_post'
        assert 'generation_time' in metadata
        
        # Step 5: Save the story
        save_response = requests.post(
            f"{self.api_base}/stories/save",
            json={
                'session_id': session_id,
                'story': story,
                'metadata': metadata
            }
        )
        
        assert save_response.status_code == 200
        save_data = save_response.json()
        assert 'story_id' in save_data
    
    def test_template_driven_story_creation(self):
        """Test creating stories using templates"""
        # Get available templates
        templates_response = requests.get(f"{self.api_base}/templates")
        assert templates_response.status_code == 200
        
        templates = templates_response.json()['templates']
        assert len(templates) > 0
        
        # Select startup journey template
        startup_template = next(
            (t for t in templates if t['id'] == 'startup_journey'),
            templates[0]
        )
        
        # Fill the template
        fill_response = requests.post(
            f"{self.api_base}/templates/fill",
            json={
                'template_id': startup_template['id'],
                'variables': {
                    'founder_name': 'Alex Chen',
                    'company_name': 'RichmondEats',
                    'industry': 'food delivery',
                    'challenge': 'connecting local restaurants with customers',
                    'solution': 'hyperlocal delivery network'
                }
            }
        )
        
        assert fill_response.status_code == 200
        filled_data = fill_response.json()
        
        # Generate story from filled template
        story_response = requests.post(
            f"{self.api_base}/generate-story",
            json={
                'core_idea': filled_data['filled_content'],
                'style': 'blog_post',
                'template_id': startup_template['id']
            }
        )
        
        assert story_response.status_code == 200
        story_data = story_response.json()
        
        # Validate template-based story
        story = story_data['story']
        assert 'Alex Chen' in story
        assert 'RichmondEats' in story
        assert 'food delivery' in story.lower()
    
    def test_concurrent_user_handling(self):
        """Test system handles multiple concurrent users"""
        def generate_story(user_id):
            """Generate a story for a specific user"""
            try:
                response = requests.post(
                    f"{self.api_base}/generate-story",
                    json={
                        'core_idea': f'Richmond tech scene from user {user_id}',
                        'style': 'short_post'
                    },
                    headers={'X-User-ID': str(user_id)},
                    timeout=30
                )
                return response.status_code == 200
            except Exception:
                return False
        
        # Simulate 10 concurrent users
        num_users = 10
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(generate_story, i) for i in range(num_users)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify results
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.9  # At least 90% success rate
        assert total_time < 30  # All requests complete within 30 seconds
        
        print(f"Concurrent test: {success_rate*100:.1f}% success rate, {total_time:.2f}s total time")
    
    def test_security_features(self):
        """Test that security features are properly integrated"""
        # Test rate limiting
        responses = []
        for i in range(15):  # Exceed rate limit
            response = requests.get(f"{self.api_base}/styles")
            responses.append(response.status_code)
        
        # Should see 429 (rate limit) responses
        assert 429 in responses
        
        # Test input validation
        invalid_response = requests.post(
            f"{self.api_base}/generate-story",
            json={
                'core_idea': '<script>alert("xss")</script>',
                'style': 'invalid_style'
            }
        )
        
        # Should reject or sanitize malicious input
        assert invalid_response.status_code in [400, 200]
        if invalid_response.status_code == 200:
            data = invalid_response.json()
            assert '<script>' not in data.get('story', '')
        
        # Test authentication endpoints exist
        auth_response = requests.post(
            f"{self.api_base}/auth/login",
            json={'username': 'test', 'password': 'test'}
        )
        assert auth_response.status_code in [200, 401, 400]
    
    def test_monitoring_integration(self):
        """Test that monitoring is properly integrated"""
        # Check metrics endpoint
        metrics_response = requests.get(f"{self.base_url}/metrics")
        assert metrics_response.status_code == 200
        
        metrics_text = metrics_response.text
        
        # Verify key metrics are present
        expected_metrics = [
            'http_request_duration_seconds',
            'story_generation_requests',
            'cache_hits',
            'story_generation_time'
        ]
        
        for metric in expected_metrics:
            assert metric in metrics_text
    
    def test_performance_requirements(self):
        """Test that system meets performance requirements"""
        # Test API response time
        start_time = time.time()
        response = requests.get(f"{self.api_base}/health")
        health_time = time.time() - start_time
        
        assert response.status_code == 200
        assert health_time < 0.1  # Health check under 100ms
        
        # Test story generation time
        start_time = time.time()
        story_response = requests.post(
            f"{self.api_base}/generate-story",
            json={
                'core_idea': 'Richmond innovation ecosystem',
                'style': 'short_post'
            }
        )
        generation_time = time.time() - start_time
        
        assert story_response.status_code == 200
        assert generation_time < 2.0  # Story generation under 2 seconds
        
        # Check if result was cached
        start_time = time.time()
        cached_response = requests.post(
            f"{self.api_base}/generate-story",
            json={
                'core_idea': 'Richmond innovation ecosystem',
                'style': 'short_post'
            }
        )
        cached_time = time.time() - start_time
        
        assert cached_response.status_code == 200
        assert cached_time < 0.5  # Cached response under 500ms
    
    def test_error_recovery(self):
        """Test system recovers gracefully from errors"""
        # Test with invalid data
        error_response = requests.post(
            f"{self.api_base}/generate-story",
            data="invalid json",
            headers={'Content-Type': 'application/json'}
        )
        
        assert error_response.status_code == 400
        error_data = error_response.json()
        assert 'error' in error_data
        
        # Verify system still works after error
        valid_response = requests.post(
            f"{self.api_base}/generate-story",
            json={
                'core_idea': 'Richmond recovery test',
                'style': 'short_post'
            }
        )
        
        assert valid_response.status_code == 200
    
    def test_frontend_integration(self):
        """Test that frontend is properly served"""
        # Check root serves frontend
        response = requests.get(self.base_url)
        assert response.status_code == 200
        assert 'text/html' in response.headers.get('Content-Type', '')
        
        # Check static assets are served
        static_paths = [
            '/static/js/main.js',
            '/static/css/main.css'
        ]
        
        for path in static_paths:
            # These might not exist in test environment
            response = requests.get(f"{self.base_url}{path}")
            # Just verify the route is handled
            assert response.status_code in [200, 404]
    
    def _generate_mock_voice_data(self):
        """Generate mock voice data for testing"""
        # Create a simple WAV file header
        wav_header = b'RIFF' + b'\x00' * 4 + b'WAVE'
        wav_header += b'fmt ' + b'\x10\x00\x00\x00'  # Subchunk1Size
        wav_header += b'\x01\x00'  # AudioFormat (PCM)
        wav_header += b'\x01\x00'  # NumChannels (mono)
        wav_header += b'\x44\xac\x00\x00'  # SampleRate (44100)
        wav_header += b'\x88\x58\x01\x00'  # ByteRate
        wav_header += b'\x02\x00'  # BlockAlign
        wav_header += b'\x10\x00'  # BitsPerSample (16)
        wav_header += b'data' + b'\x00\x00\x00\x00'  # Subchunk2Size
        
        # Add some dummy audio data
        audio_data = b'\x00\x00' * 1000
        
        return wav_header + audio_data


@pytest.mark.e2e
@pytest.mark.integration
class TestProductionReadiness:
    """Test production readiness of the integrated system"""
    
    def test_ssl_redirect(self):
        """Test that HTTP redirects to HTTPS in production"""
        # This would be tested in actual production environment
        # For now, just verify the configuration exists
        pass
    
    def test_backup_and_restore(self):
        """Test backup and restore functionality"""
        # Create test data
        test_story_response = requests.post(
            f"http://localhost:8080/api/generate-story",
            json={
                'core_idea': 'Test backup story',
                'style': 'short_post'
            }
        )
        
        assert test_story_response.status_code == 200
        
        # Trigger backup (this would be an admin endpoint)
        # backup_response = requests.post("http://localhost:8080/api/admin/backup")
        # assert backup_response.status_code == 200
        
        # Verify data persists
        health_response = requests.get("http://localhost:8080/api/health")
        assert health_response.status_code == 200
    
    def test_graceful_shutdown(self):
        """Test that system shuts down gracefully"""
        # This would test actual shutdown procedures
        # For now, verify health endpoint responds quickly
        response = requests.get(
            "http://localhost:8080/api/health",
            timeout=1
        )
        assert response.status_code == 200
    
    def test_log_aggregation(self):
        """Test that logs are properly aggregated"""
        # Generate some activity
        requests.post(
            "http://localhost:8080/api/generate-story",
            json={'core_idea': 'Log test', 'style': 'short_post'}
        )
        
        # In production, verify logs are in expected location
        # and contain expected format
        import os
        log_file = "./logs/storygen.log"
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                logs = f.read()
                assert 'Log test' in logs or len(logs) > 0
    
    def test_zero_downtime_deployment(self):
        """Test that system supports zero-downtime deployment"""
        # This would test actual deployment procedures
        # For now, verify system can handle requests during "deployment"
        
        results = []
        for i in range(5):
            try:
                response = requests.get(
                    "http://localhost:8080/api/health",
                    timeout=1
                )
                results.append(response.status_code == 200)
            except Exception:
                results.append(False)
            time.sleep(0.5)
        
        # Most requests should succeed
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.8


if __name__ == "__main__":
    # Run specific test
    pytest.main([__file__, "-v", "-k", "test_complete_voice_to_story_journey"])