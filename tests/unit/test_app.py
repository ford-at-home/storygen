"""
Unit tests for the main Flask application
"""
import pytest
import json
from unittest.mock import patch, Mock
from app import app, request_stats


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check_returns_200(self, client):
        """Test that health check returns 200 status"""
        response = client.get('/health')
        assert response.status_code == 200
    
    def test_health_check_response_format(self, client):
        """Test health check response format"""
        response = client.get('/health')
        data = json.loads(response.data)
        
        assert 'status' in data
        assert data['status'] == 'healthy'
        assert 'service' in data
        assert data['service'] == 'richmond-storyline-generator'
        assert 'version' in data
        assert 'timestamp' in data
        assert isinstance(data['timestamp'], float)


class TestRootEndpoint:
    """Test root documentation endpoint"""
    
    def test_root_returns_200(self, client):
        """Test that root endpoint returns 200"""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_root_response_format(self, client):
        """Test root endpoint response format"""
        response = client.get('/')
        data = json.loads(response.data)
        
        assert 'service' in data
        assert 'version' in data
        assert 'endpoints' in data
        assert isinstance(data['endpoints'], dict)
        assert '/generate-story' in data['endpoints']
        assert 'example' in data


class TestStylesEndpoint:
    """Test styles endpoint"""
    
    def test_styles_returns_200(self, client):
        """Test that styles endpoint returns 200"""
        response = client.get('/styles')
        assert response.status_code == 200
    
    def test_styles_response_format(self, client):
        """Test styles endpoint response format"""
        response = client.get('/styles')
        data = json.loads(response.data)
        
        assert 'styles' in data
        assert isinstance(data['styles'], list)
        assert len(data['styles']) == 3
        
        # Check each style
        for style in data['styles']:
            assert 'id' in style
            assert 'name' in style
            assert 'description' in style
            assert 'max_tokens' in style
            assert style['id'] in ['short_post', 'long_post', 'blog_post']


class TestStatsEndpoint:
    """Test statistics endpoint"""
    
    def test_stats_returns_200(self, client):
        """Test that stats endpoint returns 200"""
        response = client.get('/stats')
        assert response.status_code == 200
    
    def test_stats_initial_values(self, client):
        """Test initial statistics values"""
        response = client.get('/stats')
        data = json.loads(response.data)
        
        assert data['total_requests'] == 0
        assert data['successful_requests'] == 0
        assert data['failed_requests'] == 0
        assert data['average_response_time'] == 0


class TestGenerateStoryEndpoint:
    """Test story generation endpoint"""
    
    @patch('app.retrieve_context')
    @patch('app.generate_story')
    def test_generate_story_success(self, mock_generate, mock_retrieve, client, sample_story_request):
        """Test successful story generation"""
        # Setup mocks
        mock_retrieve.return_value = "Richmond tech context"
        mock_generate.return_value = "A compelling story about Richmond tech scene."
        
        # Make request
        response = client.post('/generate-story',
                             json=sample_story_request,
                             content_type='application/json')
        
        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'story' in data
        assert 'metadata' in data
        assert data['story'] == "A compelling story about Richmond tech scene."
        
        # Verify metadata
        metadata = data['metadata']
        assert 'request_id' in metadata
        assert 'style' in metadata
        assert metadata['style'] == 'short_post'
        assert 'response_time' in metadata
        assert 'context_retrieved' in metadata
        assert metadata['context_retrieved'] is True
        
        # Verify mocks called correctly
        mock_retrieve.assert_called_once_with(sample_story_request['core_idea'])
        mock_generate.assert_called_once_with(
            sample_story_request['core_idea'],
            "Richmond tech context",
            'short_post'
        )
    
    def test_generate_story_missing_core_idea(self, client):
        """Test story generation with missing core_idea"""
        response = client.post('/generate-story',
                             json={},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'details' in data
        assert 'core_idea' in data['details']
    
    def test_generate_story_short_core_idea(self, client):
        """Test story generation with too short core_idea"""
        response = client.post('/generate-story',
                             json={"core_idea": "short"},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Validation error' in data['error']
    
    def test_generate_story_invalid_style(self, client):
        """Test story generation with invalid style"""
        response = client.post('/generate-story',
                             json={
                                 "core_idea": "Richmond tech scene is thriving",
                                 "style": "invalid_style"
                             },
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Validation error' in data['error']
    
    @patch('app.retrieve_context')
    @patch('app.generate_story')
    def test_generate_story_default_style(self, mock_generate, mock_retrieve, client):
        """Test story generation with default style"""
        mock_retrieve.return_value = "Context"
        mock_generate.return_value = "Story"
        
        response = client.post('/generate-story',
                             json={"core_idea": "Richmond startups are growing"},
                             content_type='application/json')
        
        assert response.status_code == 200
        # Verify default style was used
        mock_generate.assert_called_with(
            "Richmond startups are growing",
            "Context",
            "short_post"  # Default style
        )
    
    @patch('app.retrieve_context')
    @patch('app.generate_story')
    def test_generate_story_no_context_found(self, mock_generate, mock_retrieve, client):
        """Test story generation when no context is found"""
        mock_retrieve.return_value = ""
        mock_generate.return_value = "Story without specific context"
        
        response = client.post('/generate-story',
                             json={"core_idea": "Richmond innovation"},
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['metadata']['context_retrieved'] is False
        
        # Verify default context message was used
        mock_generate.assert_called_with(
            "Richmond innovation",
            "No specific Richmond context found for this topic.",
            "short_post"
        )
    
    @patch('app.retrieve_context')
    def test_generate_story_retrieve_context_error(self, mock_retrieve, client):
        """Test story generation when context retrieval fails"""
        mock_retrieve.side_effect = Exception("Vector DB error")
        
        response = client.post('/generate-story',
                             json={"core_idea": "Richmond tech scene"},
                             content_type='application/json')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('app.retrieve_context')
    @patch('app.generate_story')
    def test_generate_story_generation_error(self, mock_generate, mock_retrieve, client):
        """Test story generation when LLM fails"""
        mock_retrieve.return_value = "Context"
        mock_generate.side_effect = Exception("LLM error")
        
        response = client.post('/generate-story',
                             json={"core_idea": "Richmond tech scene"},
                             content_type='application/json')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('app.retrieve_context')
    @patch('app.generate_story')
    def test_generate_story_updates_stats(self, mock_generate, mock_retrieve, client, sample_story_request):
        """Test that story generation updates statistics"""
        mock_retrieve.return_value = "Context"
        mock_generate.return_value = "Story"
        
        # Check initial stats
        stats_response = client.get('/stats')
        initial_stats = json.loads(stats_response.data)
        assert initial_stats['total_requests'] == 0
        
        # Generate story
        response = client.post('/generate-story',
                             json=sample_story_request,
                             content_type='application/json')
        assert response.status_code == 200
        
        # Check updated stats
        stats_response = client.get('/stats')
        updated_stats = json.loads(stats_response.data)
        assert updated_stats['total_requests'] == 1
        assert updated_stats['successful_requests'] == 1
        assert updated_stats['failed_requests'] == 0
        assert updated_stats['average_response_time'] > 0


class TestErrorHandlers:
    """Test error handlers"""
    
    def test_404_handler(self, client):
        """Test 404 error handler"""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Endpoint not found'
    
    def test_405_handler(self, client):
        """Test 405 method not allowed handler"""
        response = client.put('/health')  # Health only accepts GET
        assert response.status_code == 405
        data = json.loads(response.data)
        assert 'error' in data
        assert data['error'] == 'Method not allowed'
    
    def test_no_json_data(self, client):
        """Test request with no JSON data"""
        response = client.post('/generate-story',
                             data='not json',
                             content_type='text/plain')
        assert response.status_code == 400


class TestSecurityHeaders:
    """Test security headers"""
    
    def test_security_headers_present(self, client, security_headers):
        """Test that security headers are present in responses"""
        response = client.get('/health')
        
        for header, value in security_headers.items():
            assert header in response.headers
            assert response.headers[header] == value


class TestCORS:
    """Test CORS configuration"""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present for allowed origins"""
        response = client.get('/health', 
                            headers={'Origin': 'http://localhost:3000'})
        
        assert 'Access-Control-Allow-Origin' in response.headers
        assert response.headers['Access-Control-Allow-Origin'] == 'http://localhost:3000'
    
    def test_cors_preflight(self, client):
        """Test CORS preflight request"""
        response = client.options('/generate-story',
                                headers={
                                    'Origin': 'http://localhost:3000',
                                    'Access-Control-Request-Method': 'POST',
                                    'Access-Control-Request-Headers': 'Content-Type'
                                })
        
        assert response.status_code == 200
        assert 'Access-Control-Allow-Methods' in response.headers


class TestRequestValidation:
    """Test request validation"""
    
    def test_max_content_length(self, client):
        """Test that large requests are rejected"""
        # Create data larger than 25MB limit
        large_data = 'x' * (26 * 1024 * 1024)
        
        response = client.post('/generate-story',
                             data=large_data,
                             content_type='application/octet-stream')
        
        assert response.status_code == 413  # Request Entity Too Large
    
    def test_json_content_type_required(self, client):
        """Test that JSON content type is enforced"""
        response = client.post('/generate-story',
                             data='{"core_idea": "test"}',
                             content_type='text/plain')
        
        assert response.status_code == 400