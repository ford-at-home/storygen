"""
Unit tests for conversation API
"""
import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime


class TestConversationAPI:
    """Test conversation endpoints"""
    
    @patch('conversation_engine.ConversationEngine')
    def test_start_conversation_success(self, mock_engine, client):
        """Test starting a new conversation"""
        # Setup mock
        mock_instance = Mock()
        mock_instance.start_conversation.return_value = {
            "conversation_id": "conv-123",
            "session_id": "session-456",
            "created_at": datetime.utcnow().isoformat(),
            "status": "active"
        }
        mock_engine.return_value = mock_instance
        
        # Make request
        response = client.post('/conversation/start',
                             json={
                                 "session_id": "session-456",
                                 "initial_message": "Tell me about Richmond tech"
                             },
                             content_type='application/json')
        
        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["conversation_id"] == "conv-123"
        assert data["session_id"] == "session-456"
        assert data["status"] == "active"
        
        # Verify mock called correctly
        mock_instance.start_conversation.assert_called_once_with(
            session_id="session-456",
            initial_message="Tell me about Richmond tech"
        )
    
    @patch('conversation_engine.ConversationEngine')
    def test_send_message_success(self, mock_engine, client):
        """Test sending a message in conversation"""
        # Setup mock
        mock_instance = Mock()
        mock_instance.process_message.return_value = {
            "response": "Richmond has a growing tech scene...",
            "suggestions": ["Tell me more about startups", "What about coworking spaces?"],
            "context_used": ["Richmond tech growth stats", "Local success stories"]
        }
        mock_engine.return_value = mock_instance
        
        # Make request
        response = client.post('/conversation/message',
                             json={
                                 "conversation_id": "conv-123",
                                 "message": "What makes it special?"
                             },
                             content_type='application/json')
        
        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "response" in data
        assert "suggestions" in data
        assert len(data["suggestions"]) == 2
        assert "context_used" in data
    
    def test_send_message_missing_conversation_id(self, client):
        """Test sending message without conversation ID"""
        response = client.post('/conversation/message',
                             json={"message": "Hello"},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "conversation_id" in str(data["error"])
    
    @patch('conversation_engine.ConversationEngine')
    def test_get_conversation_history(self, mock_engine, client):
        """Test retrieving conversation history"""
        # Setup mock
        mock_instance = Mock()
        mock_instance.get_history.return_value = {
            "conversation_id": "conv-123",
            "messages": [
                {
                    "role": "user",
                    "content": "Tell me about Richmond",
                    "timestamp": "2024-01-01T10:00:00Z"
                },
                {
                    "role": "assistant",
                    "content": "Richmond is Virginia's capital...",
                    "timestamp": "2024-01-01T10:00:05Z"
                }
            ],
            "metadata": {
                "total_messages": 2,
                "duration": "5s",
                "topics": ["Richmond", "Virginia"]
            }
        }
        mock_engine.return_value = mock_instance
        
        # Make request
        response = client.get('/conversation/conv-123/history')
        
        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"
        assert data["metadata"]["total_messages"] == 2
    
    @patch('conversation_engine.ConversationEngine')
    def test_end_conversation(self, mock_engine, client):
        """Test ending a conversation"""
        # Setup mock
        mock_instance = Mock()
        mock_instance.end_conversation.return_value = {
            "conversation_id": "conv-123",
            "status": "ended",
            "summary": "Discussed Richmond's tech scene and startup ecosystem",
            "key_points": [
                "Growing tech hub",
                "Affordable compared to other cities",
                "Strong community support"
            ]
        }
        mock_engine.return_value = mock_instance
        
        # Make request
        response = client.post('/conversation/conv-123/end',
                             content_type='application/json')
        
        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ended"
        assert "summary" in data
        assert len(data["key_points"]) == 3
    
    @patch('conversation_engine.ConversationEngine')
    def test_conversation_feedback(self, mock_engine, client):
        """Test submitting conversation feedback"""
        # Setup mock
        mock_instance = Mock()
        mock_instance.add_feedback.return_value = {
            "feedback_id": "feedback-789",
            "status": "recorded"
        }
        mock_engine.return_value = mock_instance
        
        # Make request
        response = client.post('/conversation/conv-123/feedback',
                             json={
                                 "rating": 5,
                                 "helpful": True,
                                 "comments": "Very informative!"
                             },
                             content_type='application/json')
        
        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "recorded"
        assert "feedback_id" in data
    
    @patch('conversation_engine.ConversationEngine')
    def test_export_conversation(self, mock_engine, client):
        """Test exporting conversation data"""
        # Setup mock
        mock_instance = Mock()
        mock_instance.export_conversation.return_value = {
            "conversation_id": "conv-123",
            "export_format": "json",
            "content": {
                "messages": [],
                "metadata": {},
                "analysis": {}
            }
        }
        mock_engine.return_value = mock_instance
        
        # Make request
        response = client.get('/conversation/conv-123/export?format=json')
        
        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["export_format"] == "json"
        assert "content" in data
    
    def test_conversation_rate_limiting(self, client):
        """Test rate limiting on conversation endpoints"""
        # Make many rapid requests
        responses = []
        for i in range(50):
            response = client.post('/conversation/start',
                                 json={
                                     "session_id": f"session-{i}",
                                     "initial_message": "Test"
                                 },
                                 content_type='application/json')
            responses.append(response.status_code)
        
        # Should include some rate limited responses
        rate_limited = any(status == 429 for status in responses)
        assert rate_limited, "Conversation endpoints should be rate limited"
    
    @patch('conversation_engine.ConversationEngine')
    def test_conversation_context_injection(self, mock_engine, client):
        """Test adding context to conversation"""
        # Setup mock
        mock_instance = Mock()
        mock_instance.add_context.return_value = {
            "status": "context_added",
            "context_id": "ctx-123"
        }
        mock_engine.return_value = mock_instance
        
        # Make request
        response = client.post('/conversation/conv-123/context',
                             json={
                                 "context_type": "user_preference",
                                 "data": {
                                     "topics": ["startups", "innovation"],
                                     "style": "conversational"
                                 }
                             },
                             content_type='application/json')
        
        # Verify response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "context_added"
        assert "context_id" in data