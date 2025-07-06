"""
Unit tests for Pinecone vector store integration
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from pinecone.vectorstore import init_vectorstore, retrieve_context


class TestVectorstoreInitialization:
    """Test vector store initialization"""
    
    @patch('pinecone.init')
    @patch('langchain.vectorstores.Pinecone')
    @patch('langchain.embeddings.BedrockEmbeddings')
    def test_init_vectorstore_success(self, mock_embeddings, mock_pinecone_store, mock_pinecone_init, test_config):
        """Test successful vector store initialization"""
        # Set environment variable
        os.environ["PINECONE_API_KEY"] = "test-key"
        
        # Call function
        store = init_vectorstore()
        
        # Verify Pinecone was initialized
        mock_pinecone_init.assert_called_once_with(
            api_key="test-key",
            environment=test_config.PINECONE_ENVIRONMENT
        )
        
        # Verify embeddings were created
        mock_embeddings.assert_called_once_with(
            region_name=test_config.AWS_REGION,
            model_id=test_config.BEDROCK_EMBEDDING_MODEL_ID
        )
        
        # Verify vector store was created
        mock_pinecone_store.assert_called_once_with(
            index_name=test_config.PINECONE_INDEX_NAME,
            embedding=mock_embeddings.return_value
        )
        
        assert store == mock_pinecone_store.return_value
    
    @patch('pinecone.init')
    def test_init_vectorstore_missing_api_key(self, mock_pinecone_init):
        """Test initialization with missing API key"""
        # Remove API key if present
        if "PINECONE_API_KEY" in os.environ:
            del os.environ["PINECONE_API_KEY"]
        
        # Should raise KeyError
        with pytest.raises(KeyError):
            init_vectorstore()
    
    @patch('pinecone.init')
    @patch('langchain.vectorstores.Pinecone')
    @patch('langchain.embeddings.BedrockEmbeddings')
    def test_init_vectorstore_pinecone_error(self, mock_embeddings, mock_pinecone_store, mock_pinecone_init):
        """Test handling of Pinecone initialization error"""
        os.environ["PINECONE_API_KEY"] = "test-key"
        
        # Mock Pinecone to raise error
        mock_pinecone_init.side_effect = Exception("Pinecone connection failed")
        
        # Should propagate exception
        with pytest.raises(Exception) as exc_info:
            init_vectorstore()
        
        assert "Pinecone connection failed" in str(exc_info.value)


class TestContextRetrieval:
    """Test context retrieval functionality"""
    
    @patch('pinecone.vectorstore.init_vectorstore')
    def test_retrieve_context_success(self, mock_init_store):
        """Test successful context retrieval"""
        # Setup mock store
        mock_store = Mock()
        mock_docs = [
            Mock(page_content="Richmond tech scene is thriving."),
            Mock(page_content="Scott's Addition is the innovation hub."),
            Mock(page_content="Local entrepreneurs are building community."),
            Mock(page_content="Richmond startups focus on social impact."),
            Mock(page_content="The city supports tech growth initiatives.")
        ]
        mock_store.similarity_search.return_value = mock_docs
        mock_init_store.return_value = mock_store
        
        # Retrieve context
        result = retrieve_context("Richmond tech startups")
        
        # Verify similarity search was called
        mock_store.similarity_search.assert_called_once_with("Richmond tech startups", k=5)
        
        # Verify result format
        expected = "\n\n".join([doc.page_content for doc in mock_docs])
        assert result == expected
        assert "Richmond tech scene is thriving" in result
        assert "Scott's Addition" in result
    
    @patch('pinecone.vectorstore.init_vectorstore')
    def test_retrieve_context_empty_results(self, mock_init_store):
        """Test context retrieval with no results"""
        # Setup mock store with empty results
        mock_store = Mock()
        mock_store.similarity_search.return_value = []
        mock_init_store.return_value = mock_store
        
        # Retrieve context
        result = retrieve_context("obscure topic")
        
        # Should return empty string
        assert result == ""
    
    @patch('pinecone.vectorstore.init_vectorstore')
    def test_retrieve_context_fewer_results(self, mock_init_store):
        """Test context retrieval with fewer than k results"""
        # Setup mock store with only 2 results
        mock_store = Mock()
        mock_docs = [
            Mock(page_content="First result"),
            Mock(page_content="Second result")
        ]
        mock_store.similarity_search.return_value = mock_docs
        mock_init_store.return_value = mock_store
        
        # Retrieve context
        result = retrieve_context("limited topic")
        
        # Should return both results
        assert result == "First result\n\nSecond result"
    
    @patch('pinecone.vectorstore.init_vectorstore')
    def test_retrieve_context_unicode_content(self, mock_init_store):
        """Test context retrieval with Unicode content"""
        # Setup mock store with Unicode content
        mock_store = Mock()
        mock_docs = [
            Mock(page_content="Richmond's café culture includes José's restaurant"),
            Mock(page_content="Local entrepreneur María launched a tech startup")
        ]
        mock_store.similarity_search.return_value = mock_docs
        mock_init_store.return_value = mock_store
        
        # Retrieve context
        result = retrieve_context("Richmond entrepreneurs")
        
        # Verify Unicode is preserved
        assert "José's" in result
        assert "María" in result
    
    @patch('pinecone.vectorstore.init_vectorstore')
    def test_retrieve_context_long_query(self, mock_init_store):
        """Test context retrieval with very long query"""
        # Setup mock store
        mock_store = Mock()
        mock_store.similarity_search.return_value = [Mock(page_content="Result")]
        mock_init_store.return_value = mock_store
        
        # Create very long query
        long_query = "Richmond " * 500  # ~4000 chars
        
        # Should handle long query
        result = retrieve_context(long_query)
        assert result == "Result"
        
        # Verify the long query was passed
        mock_store.similarity_search.assert_called_with(long_query, k=5)
    
    @patch('pinecone.vectorstore.init_vectorstore')
    def test_retrieve_context_store_error(self, mock_init_store):
        """Test handling of vector store errors"""
        # Setup mock store to raise error
        mock_store = Mock()
        mock_store.similarity_search.side_effect = Exception("Vector search failed")
        mock_init_store.return_value = mock_store
        
        # Should propagate exception
        with pytest.raises(Exception) as exc_info:
            retrieve_context("query")
        
        assert "Vector search failed" in str(exc_info.value)
    
    @patch('pinecone.vectorstore.init_vectorstore')
    def test_retrieve_context_special_characters(self, mock_init_store):
        """Test context retrieval with special characters in query"""
        # Setup mock store
        mock_store = Mock()
        mock_store.similarity_search.return_value = [Mock(page_content="Result")]
        mock_init_store.return_value = mock_store
        
        # Query with special characters
        special_query = "Richmond's \"tech scene\" & <startup> ecosystem!"
        
        # Should handle special characters
        result = retrieve_context(special_query)
        assert result == "Result"
        
        # Verify query was passed correctly
        mock_store.similarity_search.assert_called_with(special_query, k=5)
    
    @patch('pinecone.vectorstore.init_vectorstore')
    def test_retrieve_context_whitespace_handling(self, mock_init_store):
        """Test context retrieval with various whitespace"""
        # Setup mock store
        mock_store = Mock()
        mock_docs = [
            Mock(page_content="  Result with leading space"),
            Mock(page_content="Result with trailing space  "),
            Mock(page_content="\nResult with newlines\n")
        ]
        mock_store.similarity_search.return_value = mock_docs
        mock_init_store.return_value = mock_store
        
        # Retrieve context
        result = retrieve_context("  query with spaces  ")
        
        # Verify whitespace is preserved in content
        assert "  Result with leading space" in result
        assert "Result with trailing space  " in result
        assert "\nResult with newlines\n" in result
    
    @patch('pinecone.vectorstore.init_vectorstore')
    def test_retrieve_context_none_results(self, mock_init_store):
        """Test handling of None in results"""
        # Setup mock store with None in results
        mock_store = Mock()
        mock_docs = [
            Mock(page_content="Valid result"),
            None,  # This shouldn't happen but test defensive coding
            Mock(page_content="Another valid result")
        ]
        mock_store.similarity_search.return_value = mock_docs
        mock_init_store.return_value = mock_store
        
        # Should handle None gracefully
        with pytest.raises(AttributeError):
            retrieve_context("query")
    
    @patch('pinecone.vectorstore.init_vectorstore')
    def test_retrieve_context_performance(self, mock_init_store):
        """Test context retrieval performance with many results"""
        import time
        
        # Setup mock store with many results
        mock_store = Mock()
        mock_docs = [Mock(page_content=f"Result {i}" * 100) for i in range(5)]
        mock_store.similarity_search.return_value = mock_docs
        mock_init_store.return_value = mock_store
        
        # Measure retrieval time
        start_time = time.time()
        result = retrieve_context("performance test")
        end_time = time.time()
        
        # Should complete quickly (under 100ms for string joining)
        assert (end_time - start_time) < 0.1
        
        # Verify all results are included
        for i in range(5):
            assert f"Result {i}" in result