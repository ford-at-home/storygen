"""
Performance tests including load testing, stress testing, and scalability validation
"""
import pytest
import time
import statistics
import concurrent.futures
import threading
import psutil
import json
from unittest.mock import patch, Mock
import asyncio
import aiohttp


@pytest.mark.performance
class TestResponseTimes:
    """Test API response time requirements"""
    
    @patch('pinecone.vectorstore.init_vectorstore')
    @patch('bedrock.bedrock_llm.get_bedrock_client')
    def test_story_generation_response_time(self, mock_bedrock_client, mock_init_store, client, performance_monitor):
        """Test story generation meets response time SLA"""
        # Setup mocks for consistent timing
        mock_store = Mock()
        mock_store.similarity_search.return_value = [Mock(page_content="Context")]
        mock_init_store.return_value = mock_store
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: b'{"completion": "Test story"}')
        }
        mock_bedrock_client.return_value = mock_bedrock
        
        performance_monitor.start()
        response_times = []
        
        # Run multiple requests to get average
        for i in range(10):
            start_time = time.time()
            response = client.post('/generate-story',
                                 json={
                                     'core_idea': f'Test story {i}',
                                     'style': 'short_post'
                                 },
                                 content_type='application/json')
            end_time = time.time()
            
            assert response.status_code == 200
            response_time = end_time - start_time
            response_times.append(response_time)
            performance_monitor.add_response_time(response_time)
        
        performance_monitor.stop()
        
        # Check performance metrics
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        max_response_time = max(response_times)
        
        # Performance requirements
        assert avg_response_time < 2.0, f"Average response time {avg_response_time}s exceeds 2s SLA"
        assert p95_response_time < 3.0, f"95th percentile {p95_response_time}s exceeds 3s SLA"
        assert max_response_time < 5.0, f"Max response time {max_response_time}s exceeds 5s limit"
        
        # Check system metrics
        perf_summary = performance_monitor.get_summary()
        assert perf_summary['avg_cpu_percent'] < 80, "Average CPU usage too high"
        assert perf_summary['avg_memory_percent'] < 80, "Average memory usage too high"
    
    def test_static_endpoint_response_times(self, client):
        """Test that static endpoints respond quickly"""
        static_endpoints = ['/health', '/stats', '/styles', '/']
        
        for endpoint in static_endpoints:
            response_times = []
            
            for _ in range(20):
                start_time = time.time()
                response = client.get(endpoint)
                end_time = time.time()
                
                assert response.status_code == 200
                response_times.append(end_time - start_time)
            
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            
            # Static endpoints should be very fast
            assert avg_time < 0.1, f"{endpoint} avg response time {avg_time}s exceeds 100ms"
            assert max_time < 0.2, f"{endpoint} max response time {max_time}s exceeds 200ms"


@pytest.mark.performance
@pytest.mark.slow
class TestLoadTesting:
    """Test system under various load conditions"""
    
    @patch('pinecone.vectorstore.init_vectorstore')
    @patch('bedrock.bedrock_llm.get_bedrock_client')
    def test_concurrent_users_load(self, mock_bedrock_client, mock_init_store, client):
        """Test system with multiple concurrent users"""
        # Setup mocks
        mock_store = Mock()
        mock_store.similarity_search.return_value = [Mock(page_content="Context")]
        mock_init_store.return_value = mock_store
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: b'{"completion": "Concurrent story"}')
        }
        mock_bedrock_client.return_value = mock_bedrock
        
        # Simulate concurrent users
        concurrent_users = 50
        requests_per_user = 5
        
        def user_simulation(user_id):
            results = []
            for i in range(requests_per_user):
                start_time = time.time()
                try:
                    response = client.post('/generate-story',
                                         json={
                                             'core_idea': f'User {user_id} story {i}',
                                             'style': 'short_post'
                                         },
                                         content_type='application/json')
                    end_time = time.time()
                    
                    results.append({
                        'user_id': user_id,
                        'request_id': i,
                        'status': response.status_code,
                        'response_time': end_time - start_time,
                        'success': response.status_code == 200
                    })
                except Exception as e:
                    results.append({
                        'user_id': user_id,
                        'request_id': i,
                        'status': 500,
                        'response_time': time.time() - start_time,
                        'success': False,
                        'error': str(e)
                    })
                
                # Small delay between requests
                time.sleep(0.1)
            
            return results
        
        # Run concurrent users
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(user_simulation, i) for i in range(concurrent_users)]
            all_results = []
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())
        end_time = time.time()
        
        # Analyze results
        total_requests = len(all_results)
        successful_requests = sum(1 for r in all_results if r['success'])
        failed_requests = total_requests - successful_requests
        response_times = [r['response_time'] for r in all_results if r['success']]
        
        # Performance metrics
        success_rate = successful_requests / total_requests
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times) if response_times else 0
        throughput = total_requests / (end_time - start_time)
        
        # Assertions
        assert success_rate > 0.95, f"Success rate {success_rate:.2%} below 95% threshold"
        assert avg_response_time < 3.0, f"Average response time {avg_response_time}s exceeds 3s under load"
        assert p95_response_time < 5.0, f"95th percentile {p95_response_time}s exceeds 5s under load"
        assert throughput > 10, f"Throughput {throughput:.2f} req/s below minimum 10 req/s"
    
    @pytest.mark.asyncio
    async def test_async_load_testing(self):
        """Test system with async load testing"""
        base_url = "http://localhost:5000"
        concurrent_requests = 100
        total_requests = 1000
        
        async def make_request(session, request_id):
            start_time = time.time()
            try:
                async with session.post(
                    f"{base_url}/generate-story",
                    json={
                        'core_idea': f'Async test story {request_id}',
                        'style': 'short_post'
                    }
                ) as response:
                    await response.text()
                    return {
                        'request_id': request_id,
                        'status': response.status,
                        'response_time': time.time() - start_time,
                        'success': response.status == 200
                    }
            except Exception as e:
                return {
                    'request_id': request_id,
                    'status': 0,
                    'response_time': time.time() - start_time,
                    'success': False,
                    'error': str(e)
                }
        
        # Run async load test
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            
            # Create batches of concurrent requests
            results = []
            for batch_start in range(0, total_requests, concurrent_requests):
                batch_end = min(batch_start + concurrent_requests, total_requests)
                batch_tasks = [
                    make_request(session, i)
                    for i in range(batch_start, batch_end)
                ]
                batch_results = await asyncio.gather(*batch_tasks)
                results.extend(batch_results)
            
            end_time = time.time()
        
        # Analyze results
        successful = [r for r in results if r['success']]
        response_times = [r['response_time'] for r in successful]
        
        # Metrics
        success_rate = len(successful) / len(results)
        avg_response_time = statistics.mean(response_times) if response_times else 0
        total_time = end_time - start_time
        requests_per_second = len(results) / total_time
        
        # Assertions
        assert success_rate > 0.9, f"Success rate {success_rate:.2%} below 90%"
        assert avg_response_time < 5.0, f"Average response time {avg_response_time}s too high"
        assert requests_per_second > 20, f"Throughput {requests_per_second:.2f} req/s too low"


@pytest.mark.performance
class TestMemoryManagement:
    """Test memory usage and leak detection"""
    
    @patch('pinecone.vectorstore.init_vectorstore')
    @patch('bedrock.bedrock_llm.get_bedrock_client')
    def test_memory_leak_detection(self, mock_bedrock_client, mock_init_store, client):
        """Test for memory leaks during extended operation"""
        # Setup mocks
        mock_store = Mock()
        mock_store.similarity_search.return_value = [Mock(page_content="Context")]
        mock_init_store.return_value = mock_store
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = {
            'body': Mock(read=lambda: b'{"completion": "Memory test story"}')
        }
        mock_bedrock_client.return_value = mock_bedrock
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make many requests
        for i in range(100):
            response = client.post('/generate-story',
                                 json={
                                     'core_idea': f'Memory test {i}' * 100,  # Larger payloads
                                     'style': 'blog_post'
                                 },
                                 content_type='application/json')
            assert response.status_code == 200
            
            # Periodic memory check
            if i % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                
                # Memory growth should be limited
                assert memory_growth < 100, f"Memory grew by {memory_growth}MB after {i} requests"
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory
        
        # Total memory growth should be reasonable
        assert total_growth < 50, f"Total memory growth {total_growth}MB exceeds 50MB limit"
    
    def test_large_payload_handling(self, client):
        """Test handling of large payloads"""
        # Create increasingly large payloads
        payload_sizes = [1_000, 10_000, 100_000, 1_000_000]  # Characters
        
        for size in payload_sizes:
            large_idea = "x" * size
            
            start_time = time.time()
            response = client.post('/generate-story',
                                 json={'core_idea': large_idea},
                                 content_type='application/json')
            end_time = time.time()
            
            # Should handle large payloads gracefully
            assert response.status_code in [200, 400, 413]
            
            # Response time should scale reasonably
            response_time = end_time - start_time
            assert response_time < 10.0, f"Response time {response_time}s for {size} chars too high"


@pytest.mark.performance
class TestScalability:
    """Test system scalability"""
    
    def test_database_connection_pooling(self):
        """Test database connection pool efficiency"""
        # This would test actual database connections
        # Simulating connection pool metrics
        from config import Config
        
        # Verify connection pool settings
        assert hasattr(Config, 'DB_POOL_SIZE') or 'DB_POOL_SIZE' in os.environ
        assert hasattr(Config, 'DB_POOL_TIMEOUT') or 'DB_POOL_TIMEOUT' in os.environ
    
    @patch('pinecone.vectorstore.init_vectorstore')
    def test_vector_search_scalability(self, mock_init_store):
        """Test vector search performance with large datasets"""
        # Simulate searching with different result set sizes
        result_sizes = [10, 100, 1000, 10000]
        
        for size in result_sizes:
            mock_store = Mock()
            mock_docs = [Mock(page_content=f"Result {i}") for i in range(size)]
            mock_store.similarity_search.return_value = mock_docs[:5]  # Still return top 5
            mock_init_store.return_value = mock_store
            
            start_time = time.time()
            from pinecone.vectorstore import retrieve_context
            context = retrieve_context("Scalability test query")
            end_time = time.time()
            
            search_time = end_time - start_time
            
            # Search time should be reasonable even with large datasets
            assert search_time < 1.0, f"Search time {search_time}s too high for {size} documents"
    
    def test_horizontal_scaling_readiness(self, client):
        """Test that application is ready for horizontal scaling"""
        # Check stateless design
        session_endpoints = ['/health', '/generate-story', '/styles']
        
        # Make requests that would go to different instances
        for endpoint in session_endpoints:
            responses = []
            for i in range(10):
                if endpoint == '/generate-story':
                    response = client.post(endpoint,
                                         json={'core_idea': f'Test {i}'},
                                         content_type='application/json')
                else:
                    response = client.get(endpoint)
                
                responses.append(response)
            
            # All responses should be consistent (stateless)
            status_codes = [r.status_code for r in responses]
            assert len(set(status_codes)) <= 2, f"Inconsistent responses for {endpoint}"


@pytest.mark.performance
class TestCaching:
    """Test caching performance"""
    
    @patch('pinecone.vectorstore.init_vectorstore')
    @patch('bedrock.bedrock_llm.get_bedrock_client')
    def test_cache_hit_performance(self, mock_bedrock_client, mock_init_store, client):
        """Test performance improvement with caching"""
        # Setup mocks
        mock_store = Mock()
        mock_store.similarity_search.return_value = [Mock(page_content="Cached context")]
        mock_init_store.return_value = mock_store
        
        call_count = 0
        def mock_invoke(**kwargs):
            nonlocal call_count
            call_count += 1
            time.sleep(0.5)  # Simulate LLM latency
            return {
                'body': Mock(read=lambda: b'{"completion": "Cached story"}')
            }
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.side_effect = mock_invoke
        mock_bedrock_client.return_value = mock_bedrock
        
        # First request (cache miss)
        start_time = time.time()
        response1 = client.post('/generate-story',
                              json={'core_idea': 'Cacheable story idea'},
                              content_type='application/json')
        first_request_time = time.time() - start_time
        
        assert response1.status_code == 200
        assert call_count == 1
        
        # Second request (cache hit)
        start_time = time.time()
        response2 = client.post('/generate-story',
                              json={'core_idea': 'Cacheable story idea'},
                              content_type='application/json')
        second_request_time = time.time() - start_time
        
        assert response2.status_code == 200
        
        # Cache hit should be much faster
        assert second_request_time < first_request_time / 2
        
        # LLM should not be called again (cached)
        assert call_count == 1
    
    def test_cache_invalidation(self, client):
        """Test cache invalidation strategies"""
        # Test that cache can be invalidated
        response = client.post('/cache/clear',
                             headers={'Authorization': 'Bearer admin-token'},
                             content_type='application/json')
        
        # Should be able to clear cache (or 404 if not implemented)
        assert response.status_code in [200, 404]


@pytest.mark.performance
class TestResourceUtilization:
    """Test efficient resource utilization"""
    
    def test_cpu_usage_efficiency(self, client, performance_monitor):
        """Test CPU usage remains efficient"""
        performance_monitor.start()
        
        # Perform various operations
        operations = [
            ('GET', '/health', None),
            ('GET', '/styles', None),
            ('POST', '/generate-story', {'core_idea': 'Test story'}),
            ('GET', '/stats', None)
        ]
        
        for method, endpoint, data in operations * 10:
            if method == 'GET':
                client.get(endpoint)
            else:
                client.post(endpoint, json=data, content_type='application/json')
            time.sleep(0.1)
        
        performance_monitor.stop()
        metrics = performance_monitor.get_summary()
        
        # CPU usage should be reasonable
        assert metrics['avg_cpu_percent'] < 50, f"Average CPU {metrics['avg_cpu_percent']}% too high"
        assert metrics['max_cpu_percent'] < 90, f"Max CPU {metrics['max_cpu_percent']}% too high"
    
    def test_thread_pool_efficiency(self, performance_monitor):
        """Test thread pool usage is efficient"""
        performance_monitor.start()
        time.sleep(1)  # Let it collect baseline
        performance_monitor.stop()
        
        metrics = performance_monitor.get_summary()
        
        # Thread count should be reasonable
        assert metrics['avg_threads'] < 50, f"Average thread count {metrics['avg_threads']} too high"
        assert metrics['max_threads'] < 100, f"Max thread count {metrics['max_threads']} too high"