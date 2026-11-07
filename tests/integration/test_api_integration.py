"""
Integration tests for the complete API flow
"""
import pytest
import json
import time
from unittest.mock import patch, Mock
from app import app


@pytest.mark.integration
class TestAPIIntegration:
    """Test complete API integration flows"""
    
    @patch('pinecone.vectorstore.init_vectorstore')
    @patch('bedrock.bedrock_llm.get_bedrock_client')
    def test_complete_story_generation_flow(self, mock_bedrock_client, mock_init_store, client, test_config):
        """Test complete story generation flow from request to response"""
        # Setup mocks for vector store
        mock_store = Mock()
        mock_docs = [
            Mock(page_content="Richmond's tech scene is experiencing rapid growth."),
            Mock(page_content="Scott's Addition has transformed into an innovation hub."),
            Mock(page_content="Local entrepreneurs are building community-focused startups.")
        ]
        mock_store.similarity_search.return_value = mock_docs
        mock_init_store.return_value = mock_store
        
        # Setup mocks for Bedrock
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: json.dumps({
                'completion': """Richmond's tech renaissance is a story of homecoming and innovation. 
                
Tech professionals who once sought opportunities in Silicon Valley and Seattle are returning 
to Richmond, bringing with them years of experience and a vision for building something 
meaningful in their hometown.

Scott's Addition exemplifies this transformation - what was once an industrial district 
now buzzes with startups, coworking spaces, and tech meetups. The community here isn't 
just about building companies; it's about building a sustainable tech ecosystem that 
reflects Richmond's values of authenticity and community connection.

These returning professionals aren't trying to replicate coastal tech culture. Instead, 
they're creating something uniquely Richmond - startups that prioritize work-life balance, 
community impact, and sustainable growth over the typical venture capital rat race."""
            }).encode())
        }
        mock_bedrock_client.return_value = mock_bedrock
        
        # Make request
        request_data = {
            "core_idea": "Richmond tech professionals returning from coastal cities to build startups",
            "style": "long_post"
        }
        
        start_time = time.time()
        response = client.post('/generate-story',
                             json=request_data,
                             content_type='application/json')
        end_time = time.time()
        
        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Check story content
        assert 'story' in data
        story = data['story']
        assert "Richmond" in story
        assert "tech" in story
        assert "Scott's Addition" in story
        assert len(story) > 500  # Long post should be substantial
        
        # Check metadata
        assert 'metadata' in data
        metadata = data['metadata']
        assert metadata['style'] == 'long_post'
        assert metadata['context_retrieved'] is True
        assert 'request_id' in metadata
        assert 'response_time' in metadata
        
        # Verify response time is reasonable
        assert (end_time - start_time) < 5.0  # Should complete within 5 seconds
        
        # Verify mocks were called correctly
        mock_init_store.assert_called_once()
        mock_store.similarity_search.assert_called_once_with(request_data['core_idea'], k=5)
        mock_bedrock.invoke_model.assert_called_once()
        
        # Check Bedrock invocation
        bedrock_call = mock_bedrock.invoke_model.call_args[1]
        assert bedrock_call['modelId'] == test_config.BEDROCK_MODEL_ID
        body = json.loads(bedrock_call['body'])
        assert body['max_tokens'] == test_config.TOKEN_LIMITS['long_post']
        assert body['temperature'] == test_config.DEFAULT_TEMPERATURE
    
    @patch('pinecone.vectorstore.init_vectorstore')
    @patch('bedrock.bedrock_llm.get_bedrock_client')
    def test_multiple_concurrent_requests(self, mock_bedrock_client, mock_init_store, client):
        """Test handling multiple concurrent requests"""
        # Setup mocks
        mock_store = Mock()
        mock_store.similarity_search.return_value = [Mock(page_content="Context")]
        mock_init_store.return_value = mock_store
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: b'{"completion": "Story"}')
        }
        mock_bedrock_client.return_value = mock_bedrock
        
        # Make multiple requests
        requests_data = [
            {"core_idea": "Richmond food scene evolution", "style": "short_post"},
            {"core_idea": "Richmond startup ecosystem growth", "style": "long_post"},
            {"core_idea": "Richmond arts and tech intersection", "style": "blog_post"}
        ]
        
        responses = []
        for data in requests_data:
            response = client.post('/generate-story',
                                 json=data,
                                 content_type='application/json')
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'story' in data
            assert 'metadata' in data
        
        # Check stats endpoint
        stats_response = client.get('/stats')
        stats = json.loads(stats_response.data)
        assert stats['total_requests'] == 3
        assert stats['successful_requests'] == 3
        assert stats['failed_requests'] == 0
    
    @patch('pinecone.vectorstore.init_vectorstore')
    def test_error_recovery_flow(self, mock_init_store, client):
        """Test API recovery from errors"""
        # First request fails due to vector store error
        mock_init_store.side_effect = Exception("Vector DB connection failed")
        
        response1 = client.post('/generate-story',
                              json={"core_idea": "Test idea one"},
                              content_type='application/json')
        
        assert response1.status_code == 500
        error_data = json.loads(response1.data)
        assert 'error' in error_data
        
        # Fix the mock for next request
        mock_store = Mock()
        mock_store.similarity_search.return_value = []
        mock_init_store.side_effect = None
        mock_init_store.return_value = mock_store
        
        # Health check should still work
        health_response = client.get('/health')
        assert health_response.status_code == 200
        
        # Stats should show the failure
        stats_response = client.get('/stats')
        stats = json.loads(stats_response.data)
        assert stats['failed_requests'] == 1
    
    def test_api_documentation_flow(self, client):
        """Test API documentation and discovery flow"""
        # Start at root
        root_response = client.get('/')
        assert root_response.status_code == 200
        root_data = json.loads(root_response.data)
        
        # Discover available endpoints
        endpoints = root_data['endpoints']
        
        # Test each documented endpoint
        # Health check
        assert '/health' in endpoints
        health_response = client.get('/health')
        assert health_response.status_code == 200
        
        # Styles
        assert '/styles' in endpoints
        styles_response = client.get('/styles')
        assert styles_response.status_code == 200
        styles_data = json.loads(styles_response.data)
        assert len(styles_data['styles']) == 3
        
        # Stats
        assert '/stats' in endpoints
        stats_response = client.get('/stats')
        assert stats_response.status_code == 200
    
    @patch('pinecone.vectorstore.init_vectorstore')
    @patch('bedrock.bedrock_llm.get_bedrock_client')
    def test_different_style_outputs(self, mock_bedrock_client, mock_init_store, client):
        """Test that different styles produce appropriately sized outputs"""
        # Setup mocks
        mock_store = Mock()
        mock_store.similarity_search.return_value = [Mock(page_content="Richmond context")]
        mock_init_store.return_value = mock_store
        
        # Mock different length responses based on style
        def mock_invoke_model(**kwargs):
            body = json.loads(kwargs['body'])
            max_tokens = body['max_tokens']
            
            if max_tokens == 1024:  # short_post
                story = "Short Richmond story. " * 20  # ~400 chars
            elif max_tokens == 2048:  # long_post
                story = "Medium Richmond story with more details. " * 40  # ~1600 chars
            else:  # blog_post
                story = "Long Richmond blog post with extensive content. " * 80  # ~3600 chars
            
            return {
                'body': Mock(read=lambda: json.dumps({'completion': story}).encode())
            }
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.side_effect = mock_invoke_model
        mock_bedrock_client.return_value = mock_bedrock
        
        # Test each style
        styles_to_test = [
            ("short_post", 200, 600),
            ("long_post", 1400, 1800),
            ("blog_post", 3400, 3800)
        ]
        
        for style, min_length, max_length in styles_to_test:
            response = client.post('/generate-story',
                                 json={
                                     "core_idea": f"Test {style} story",
                                     "style": style
                                 },
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            story_length = len(data['story'])
            assert min_length <= story_length <= max_length, f"{style} story length {story_length} not in range {min_length}-{max_length}"


@pytest.mark.integration
class TestAPIValidationIntegration:
    """Test API validation in integration scenarios"""
    
    def test_validation_edge_cases(self, client):
        """Test various validation edge cases"""
        test_cases = [
            # Empty request
            ({}, 400, "Validation error"),
            
            # Null values
            ({"core_idea": None, "style": "short_post"}, 400, "Validation error"),
            
            # Wrong types
            ({"core_idea": 12345, "style": "short_post"}, 400, "Validation error"),
            ({"core_idea": "Valid idea", "style": 123}, 400, "Validation error"),
            
            # Boundary values
            ({"core_idea": "x" * 10}, 200, None),  # Exactly 10 chars - should pass
            ({"core_idea": "x" * 9}, 400, "at least 10 characters"),  # 9 chars - should fail
            
            # Special characters
            ({"core_idea": "Richmond's \"tech\" scene & <innovation>!"}, 200, None),
            
            # Unicode
            ({"core_idea": "Richmond café José María's restaurant"}, 200, None),
            
            # Very long input
            ({"core_idea": "x" * 10000}, 200, None),  # Should handle long input
        ]
        
        for request_data, expected_status, expected_error in test_cases:
            with patch('pinecone.vectorstore.init_vectorstore'), \
                 patch('bedrock.bedrock_llm.get_bedrock_client'):
                
                response = client.post('/generate-story',
                                     json=request_data,
                                     content_type='application/json')
                
                assert response.status_code == expected_status, f"Failed for {request_data}"
                
                if expected_error:
                    data = json.loads(response.data)
                    assert expected_error in json.dumps(data)


@pytest.mark.integration
class TestAPISecurityIntegration:
    """Test API security in integration scenarios"""
    
    def test_security_headers_on_all_endpoints(self, client, security_headers):
        """Test that security headers are present on all endpoints"""
        endpoints = ['/', '/health', '/stats', '/styles', '/generate-story']
        
        for endpoint in endpoints:
            if endpoint == '/generate-story':
                response = client.post(endpoint, json={})
            else:
                response = client.get(endpoint)
            
            for header, value in security_headers.items():
                assert header in response.headers
                assert response.headers[header] == value
    
    def test_cors_integration(self, client):
        """Test CORS works correctly across endpoints"""
        allowed_origins = ['http://localhost:3000', 'http://localhost:8080']
        
        for origin in allowed_origins:
            # Test preflight
            response = client.options('/generate-story',
                                    headers={
                                        'Origin': origin,
                                        'Access-Control-Request-Method': 'POST',
                                        'Access-Control-Request-Headers': 'Content-Type'
                                    })
            
            assert response.status_code == 200
            assert response.headers.get('Access-Control-Allow-Origin') == origin
            
            # Test actual request
            response = client.post('/generate-story',
                                 json={"core_idea": "test"},
                                 headers={'Origin': origin})
            
            assert 'Access-Control-Allow-Origin' in response.headers
    
    def test_content_type_enforcement(self, client):
        """Test that content type is properly enforced"""
        # Non-JSON content type should fail
        response = client.post('/generate-story',
                             data='{"core_idea": "test"}',
                             content_type='text/plain')
        
        assert response.status_code == 400
    
    def test_method_not_allowed_security(self, client):
        """Test that unsupported methods are properly rejected"""
        unsupported_methods = ['PUT', 'DELETE', 'PATCH']
        
        for method in unsupported_methods:
            response = client.open('/generate-story', method=method)
            assert response.status_code == 405
            data = json.loads(response.data)
            assert 'Method not allowed' in data['error']