"""
End-to-end tests for complete user flows
"""
import pytest
import json
import time
import base64
from unittest.mock import patch, Mock
from io import BytesIO


@pytest.mark.e2e
class TestCompleteUserFlows:
    """Test complete end-to-end user flows"""
    
    @patch('pinecone.vectorstore.init_vectorstore')
    @patch('bedrock.bedrock_llm.get_bedrock_client')
    @patch('openai.OpenAI')
    def test_voice_to_story_flow(self, mock_openai, mock_bedrock_client, mock_init_store, client, sample_voice_data):
        """Test complete flow from voice recording to story generation"""
        # Setup OpenAI mock for transcription
        mock_whisper = Mock()
        mock_whisper.audio.transcriptions.create.return_value = Mock(
            text="I want to share a story about Richmond's growing tech community and how professionals are returning from Silicon Valley to build startups here."
        )
        mock_openai.return_value = mock_whisper
        
        # Setup vector store mock
        mock_store = Mock()
        mock_docs = [
            Mock(page_content="Richmond's tech ecosystem is attracting talent from major tech hubs."),
            Mock(page_content="Former Silicon Valley engineers are launching Richmond startups."),
            Mock(page_content="The city's quality of life draws tech professionals home.")
        ]
        mock_store.similarity_search.return_value = mock_docs
        mock_init_store.return_value = mock_store
        
        # Setup Bedrock mock
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: json.dumps({
                'completion': """The Return: Richmond's Tech Homecoming

                Sarah Chen spent five years in Silicon Valley, working at companies whose names 
                everyone recognizes. But last fall, she packed up her Palo Alto apartment and 
                drove back to Richmond, the city she'd left behind after college.

                "I realized I was building products for problems I didn't care about," she explains 
                from her new office in Scott's Addition. "In Richmond, I can build something that 
                actually impacts my community."

                Sarah isn't alone. Richmond is experiencing a quiet tech migration as professionals 
                return from coastal cities, bringing Silicon Valley experience but leaving behind 
                its culture of endless hustle. They're creating a different kind of tech scene - 
                one that values work-life balance, community connection, and sustainable growth.

                Her startup, which connects local farms with Richmond restaurants through a 
                streamlined ordering platform, already has 30 partner farms and 50 restaurants. 
                It's the kind of business that makes sense here - practical, community-focused, 
                and deeply rooted in Richmond's culture.

                "We're not trying to be the next unicorn," Sarah says. "We're trying to make 
                Richmond better. And that's exactly why I came home." """
            }).encode())
        }
        mock_bedrock_client.return_value = mock_bedrock
        
        # Step 1: Upload voice recording
        voice_response = client.post('/voice/transcribe',
                                   data={
                                       'audio': (BytesIO(sample_voice_data), 'recording.wav')
                                   },
                                   content_type='multipart/form-data')
        
        assert voice_response.status_code == 200
        voice_data = json.loads(voice_response.data)
        assert 'transcription' in voice_data
        assert 'session_id' in voice_data
        
        session_id = voice_data['session_id']
        transcription = voice_data['transcription']
        
        # Step 2: Start conversation with transcribed text
        conversation_response = client.post('/conversation/start',
                                          json={
                                              'session_id': session_id,
                                              'initial_message': transcription
                                          },
                                          content_type='application/json')
        
        assert conversation_response.status_code == 200
        conv_data = json.loads(conversation_response.data)
        assert 'conversation_id' in conv_data
        
        # Step 3: Refine the idea through conversation
        refine_response = client.post('/conversation/message',
                                    json={
                                        'conversation_id': conv_data['conversation_id'],
                                        'message': "Focus on the personal journey of someone returning"
                                    },
                                    content_type='application/json')
        
        assert refine_response.status_code == 200
        
        # Step 4: Generate the final story
        story_response = client.post('/generate-story',
                                   json={
                                       'core_idea': transcription,
                                       'style': 'long_post',
                                       'conversation_context': conv_data['conversation_id']
                                   },
                                   content_type='application/json')
        
        assert story_response.status_code == 200
        story_data = json.loads(story_response.data)
        
        # Verify the complete flow produced a cohesive story
        story = story_data['story']
        assert len(story) > 1000  # Substantial story
        assert "Richmond" in story
        assert "tech" in story.lower()
        assert "Silicon Valley" in story
        
        # Verify personalization from conversation
        assert "Sarah Chen" in story or "personal" in story.lower()
    
    @patch('pinecone.vectorstore.init_vectorstore')
    @patch('bedrock.bedrock_llm.get_bedrock_client')
    def test_template_based_story_flow(self, mock_bedrock_client, mock_init_store, client):
        """Test story generation using templates"""
        # Setup mocks
        mock_store = Mock()
        mock_store.similarity_search.return_value = [
            Mock(page_content="Richmond startup ecosystem facts")
        ]
        mock_init_store.return_value = mock_store
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: b'{"completion": "Templated startup story"}')
        }
        mock_bedrock_client.return_value = mock_bedrock
        
        # Step 1: Get available templates
        templates_response = client.get('/templates')
        assert templates_response.status_code == 200
        templates = json.loads(templates_response.data)['templates']
        
        # Step 2: Select a template
        startup_template = next(t for t in templates if t['id'] == 'startup_journey')
        
        # Step 3: Fill template variables
        filled_template = client.post('/templates/fill',
                                    json={
                                        'template_id': startup_template['id'],
                                        'variables': {
                                            'founder_name': 'Maria Rodriguez',
                                            'company_name': 'RVA TechWorks',
                                            'industry': 'edtech',
                                            'challenge': 'connecting students with mentors'
                                        }
                                    },
                                    content_type='application/json')
        
        assert filled_template.status_code == 200
        filled_data = json.loads(filled_template.data)
        
        # Step 4: Generate story from filled template
        story_response = client.post('/generate-story',
                                   json={
                                       'core_idea': filled_data['filled_content'],
                                       'style': 'blog_post',
                                       'template_id': startup_template['id']
                                   },
                                   content_type='application/json')
        
        assert story_response.status_code == 200
        story_data = json.loads(story_response.data)
        assert 'story' in story_data
        assert story_data['metadata']['template_used'] == 'startup_journey'
    
    @patch('pinecone.vectorstore.init_vectorstore')
    @patch('bedrock.bedrock_llm.get_bedrock_client')
    def test_multi_user_collaboration_flow(self, mock_bedrock_client, mock_init_store, client):
        """Test multiple users collaborating on a story"""
        # Setup mocks
        mock_store = Mock()
        mock_store.similarity_search.return_value = [Mock(page_content="Richmond context")]
        mock_init_store.return_value = mock_store
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: b'{"completion": "Collaborative story"}')
        }
        mock_bedrock_client.return_value = mock_bedrock
        
        # User 1: Create initial story draft
        user1_response = client.post('/stories/create',
                                   json={
                                       'core_idea': 'Richmond food tech innovation',
                                       'style': 'blog_post',
                                       'author': 'user1@example.com'
                                   },
                                   headers={'Authorization': 'Bearer user1-token'},
                                   content_type='application/json')
        
        assert user1_response.status_code == 200
        story_id = json.loads(user1_response.data)['story_id']
        
        # User 2: Add comments/suggestions
        user2_comment = client.post(f'/stories/{story_id}/comments',
                                  json={
                                      'comment': 'Can we add more about local restaurants?',
                                      'author': 'user2@example.com'
                                  },
                                  headers={'Authorization': 'Bearer user2-token'},
                                  content_type='application/json')
        
        assert user2_comment.status_code == 200
        
        # User 1: Revise based on feedback
        revision_response = client.post(f'/stories/{story_id}/revise',
                                      json={
                                          'additional_context': 'Include Brenner Pass and Longoven',
                                          'incorporate_feedback': True
                                      },
                                      headers={'Authorization': 'Bearer user1-token'},
                                      content_type='application/json')
        
        assert revision_response.status_code == 200
        
        # Both users: Approve final version
        for token in ['user1-token', 'user2-token']:
            approve_response = client.post(f'/stories/{story_id}/approve',
                                         headers={'Authorization': f'Bearer {token}'},
                                         content_type='application/json')
            assert approve_response.status_code == 200
        
        # Publish the story
        publish_response = client.post(f'/stories/{story_id}/publish',
                                     headers={'Authorization': 'Bearer user1-token'},
                                     content_type='application/json')
        
        assert publish_response.status_code == 200
        published_data = json.loads(publish_response.data)
        assert published_data['status'] == 'published'
        assert len(published_data['collaborators']) == 2


@pytest.mark.e2e
class TestPerformanceUserFlows:
    """Test performance aspects of user flows"""
    
    @patch('pinecone.vectorstore.init_vectorstore')
    @patch('bedrock.bedrock_llm.get_bedrock_client')
    def test_batch_story_generation(self, mock_bedrock_client, mock_init_store, client):
        """Test batch generation of multiple stories"""
        # Setup mocks
        mock_store = Mock()
        mock_store.similarity_search.return_value = [Mock(page_content="Context")]
        mock_init_store.return_value = mock_store
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: b'{"completion": "Batch story"}')
        }
        mock_bedrock_client.return_value = mock_bedrock
        
        # Batch request
        batch_request = {
            'stories': [
                {
                    'core_idea': 'Richmond tech scene growth',
                    'style': 'short_post'
                },
                {
                    'core_idea': 'Richmond food innovation',
                    'style': 'long_post'
                },
                {
                    'core_idea': 'Richmond arts and culture',
                    'style': 'blog_post'
                }
            ],
            'parallel': True
        }
        
        start_time = time.time()
        batch_response = client.post('/stories/batch',
                                   json=batch_request,
                                   content_type='application/json')
        end_time = time.time()
        
        assert batch_response.status_code == 200
        batch_data = json.loads(batch_response.data)
        
        # Verify all stories were generated
        assert len(batch_data['stories']) == 3
        for story in batch_data['stories']:
            assert 'story' in story
            assert 'metadata' in story
            assert story['status'] == 'completed'
        
        # Performance check - should complete reasonably fast with parallel processing
        assert (end_time - start_time) < 10.0
    
    @patch('pinecone.vectorstore.init_vectorstore')
    @patch('bedrock.bedrock_llm.get_bedrock_client')
    def test_story_caching_flow(self, mock_bedrock_client, mock_init_store, client):
        """Test that similar requests use caching effectively"""
        # Setup mocks
        mock_store = Mock()
        mock_store.similarity_search.return_value = [Mock(page_content="Cached context")]
        mock_init_store.return_value = mock_store
        
        call_count = 0
        def mock_invoke():
            nonlocal call_count
            call_count += 1
            return {
                'body': Mock(read=lambda: f'{{"completion": "Story version {call_count}"}}'.encode())
            }
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.side_effect = mock_invoke
        mock_bedrock_client.return_value = mock_bedrock
        
        # First request - should hit LLM
        request_data = {
            'core_idea': 'Richmond tech professionals returning home',
            'style': 'short_post'
        }
        
        response1 = client.post('/generate-story',
                              json=request_data,
                              content_type='application/json')
        assert response1.status_code == 200
        
        # Very similar request - should use cache
        similar_request = {
            'core_idea': 'Richmond tech professionals returning home',  # Exact same
            'style': 'short_post'
        }
        
        response2 = client.post('/generate-story',
                              json=similar_request,
                              content_type='application/json')
        assert response2.status_code == 200
        
        # Both should return same story (from cache)
        story1 = json.loads(response1.data)['story']
        story2 = json.loads(response2.data)['story']
        assert story1 == story2
        
        # LLM should only be called once
        assert call_count == 1


@pytest.mark.e2e
class TestErrorRecoveryFlows:
    """Test error recovery in user flows"""
    
    def test_graceful_degradation_flow(self, client):
        """Test system degrades gracefully when services fail"""
        # Simulate various service failures
        with patch('pinecone.vectorstore.init_vectorstore') as mock_vector:
            mock_vector.side_effect = Exception("Vector DB down")
            
            # Should still be able to check health
            health_response = client.get('/health')
            assert health_response.status_code == 200
            
            # Should get appropriate error for story generation
            story_response = client.post('/generate-story',
                                       json={'core_idea': 'Test story'},
                                       content_type='application/json')
            assert story_response.status_code == 500
            error_data = json.loads(story_response.data)
            assert 'error' in error_data
            
            # Other endpoints should still work
            styles_response = client.get('/styles')
            assert styles_response.status_code == 200
    
    @patch('pinecone.vectorstore.init_vectorstore')
    @patch('bedrock.bedrock_llm.get_bedrock_client')
    def test_retry_flow(self, mock_bedrock_client, mock_init_store, client):
        """Test automatic retry on transient failures"""
        # Setup vector store mock
        mock_store = Mock()
        mock_store.similarity_search.return_value = [Mock(page_content="Context")]
        mock_init_store.return_value = mock_store
        
        # Setup Bedrock to fail then succeed
        fail_count = 0
        def mock_invoke(**kwargs):
            nonlocal fail_count
            fail_count += 1
            if fail_count < 3:
                raise Exception("Transient error")
            return {
                'body': Mock(read=lambda: b'{"completion": "Success after retries"}')
            }
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.side_effect = mock_invoke
        mock_bedrock_client.return_value = mock_bedrock
        
        # Make request - should eventually succeed after retries
        response = client.post('/generate-story',
                             json={'core_idea': 'Test retry logic'},
                             content_type='application/json')
        
        # Should succeed after retries
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['story'] == "Success after retries"
        assert fail_count == 3  # Failed twice, succeeded on third try