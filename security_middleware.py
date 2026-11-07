"""
Security Middleware for Richmond Storyline Generator
Comprehensive input validation, sanitization, and security controls
"""

import re
import html
import json
import logging
from functools import wraps
from typing import Dict, Any, List, Optional, Callable
from urllib.parse import urlparse
import bleach
import validators
from flask import request, jsonify, abort, g
from marshmallow import Schema, fields, ValidationError, validates_schema
from werkzeug.datastructures import FileStorage
import magic
import hashlib
import os

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Security configuration constants"""
    
    # File upload limits
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'ogg', 'md'}
    ALLOWED_MIME_TYPES = {
        'text/plain', 'application/pdf', 'image/png', 'image/jpeg', 'image/gif',
        'audio/mpeg', 'audio/wav', 'audio/ogg', 'text/markdown'
    }
    
    # Input validation limits
    MAX_STRING_LENGTH = 10000
    MAX_ARRAY_LENGTH = 100
    MAX_OBJECT_DEPTH = 5
    
    # Rate limiting
    DEFAULT_RATE_LIMIT = 100  # requests per hour
    STRICT_RATE_LIMIT = 10    # requests per hour for sensitive endpoints
    
    # Security patterns
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload=',
        r'onerror=',
        r'onclick=',
        r'onmouseover=',
        r'eval\(',
        r'exec\(',
        r'system\(',
        r'import\s+os',
        r'import\s+subprocess',
        r'__import__',
        r'\.\./'
    ]
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',
        r'(\b(OR|AND)\s+\w+\s*=\s*\w+)',
        r'(--|#|/\*|\*/)',
        r'(\bUNION\s+SELECT\b)',
        r'(\bDROP\s+TABLE\b)',
        r'(\bINSERT\s+INTO\b)',
        r'(\bUPDATE\s+\w+\s+SET\b)'
    ]


class InputSanitizer:
    """Handles input sanitization and validation"""
    
    @staticmethod
    def sanitize_string(value: str, allow_html: bool = False) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return str(value)
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Normalize whitespace
        value = re.sub(r'\s+', ' ', value).strip()
        
        # Check for dangerous patterns
        for pattern in SecurityConfig.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"⚠️  Dangerous pattern detected: {pattern}")
                value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        # Check for SQL injection patterns
        for pattern in SecurityConfig.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"⚠️  SQL injection pattern detected: {pattern}")
                value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        # HTML sanitization
        if allow_html:
            # Allow safe HTML tags
            allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'i', 'b', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
            allowed_attributes = {}
            value = bleach.clean(value, tags=allowed_tags, attributes=allowed_attributes)
        else:
            # Escape HTML entities
            value = html.escape(value)
        
        # Limit length
        if len(value) > SecurityConfig.MAX_STRING_LENGTH:
            value = value[:SecurityConfig.MAX_STRING_LENGTH]
            logger.warning(f"⚠️  String truncated to {SecurityConfig.MAX_STRING_LENGTH} characters")
        
        return value
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage"""
        if not filename:
            return "unnamed_file"
        
        # Remove directory traversal attempts
        filename = os.path.basename(filename)
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:250] + ext
        
        # Ensure it's not empty
        if not filename:
            filename = "sanitized_file"
        
        return filename
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address"""
        return validators.email(email)
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL"""
        return validators.url(url)
    
    @staticmethod
    def validate_json_structure(data: Any, max_depth: int = 5, current_depth: int = 0) -> bool:
        """Validate JSON structure for safety"""
        if current_depth > max_depth:
            return False
        
        if isinstance(data, dict):
            if len(data) > 100:  # Limit object size
                return False
            for key, value in data.items():
                if not isinstance(key, str) or len(key) > 100:
                    return False
                if not InputSanitizer.validate_json_structure(value, max_depth, current_depth + 1):
                    return False
        
        elif isinstance(data, list):
            if len(data) > SecurityConfig.MAX_ARRAY_LENGTH:
                return False
            for item in data:
                if not InputSanitizer.validate_json_structure(item, max_depth, current_depth + 1):
                    return False
        
        elif isinstance(data, str):
            if len(data) > SecurityConfig.MAX_STRING_LENGTH:
                return False
        
        return True


class FileValidator:
    """Validates uploaded files for security"""
    
    @staticmethod
    def validate_file(file: FileStorage) -> Dict[str, Any]:
        """Comprehensive file validation"""
        validation_result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'metadata': {}
        }
        
        if not file or not file.filename:
            validation_result['errors'].append("No file provided")
            return validation_result
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)     # Reset to beginning
        
        if file_size > SecurityConfig.MAX_FILE_SIZE:
            validation_result['errors'].append(f"File too large: {file_size} bytes (max: {SecurityConfig.MAX_FILE_SIZE})")
            return validation_result
        
        # Check file extension
        filename = file.filename.lower()
        extension = filename.split('.')[-1] if '.' in filename else ''
        
        if extension not in SecurityConfig.ALLOWED_EXTENSIONS:
            validation_result['errors'].append(f"File extension not allowed: {extension}")
            return validation_result
        
        # Check MIME type
        file_content = file.read(1024)  # Read first 1KB
        file.seek(0)  # Reset
        
        try:
            mime_type = magic.from_buffer(file_content, mime=True)
            if mime_type not in SecurityConfig.ALLOWED_MIME_TYPES:
                validation_result['errors'].append(f"MIME type not allowed: {mime_type}")
                return validation_result
        except Exception as e:
            validation_result['warnings'].append(f"Could not determine MIME type: {e}")
        
        # Check for embedded executables (basic check)
        if b'MZ' in file_content[:100] or b'PK' in file_content[:10]:
            validation_result['errors'].append("File may contain executable content")
            return validation_result
        
        # Calculate file hash
        file_hash = hashlib.sha256()
        while True:
            chunk = file.read(8192)
            if not chunk:
                break
            file_hash.update(chunk)
        file.seek(0)  # Reset
        
        validation_result['metadata'] = {
            'size': file_size,
            'extension': extension,
            'mime_type': mime_type,
            'hash': file_hash.hexdigest(),
            'sanitized_filename': InputSanitizer.sanitize_filename(file.filename)
        }
        
        if not validation_result['errors']:
            validation_result['valid'] = True
        
        return validation_result


class SecurityMiddleware:
    """Main security middleware class"""
    
    def __init__(self, app=None):
        self.app = app
        self.request_counts = {}
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security middleware"""
        self.app = app
        
        # Register before_request handlers
        app.before_request(self._security_check)
        app.before_request(self._rate_limit_check)
        
        # Register after_request handlers
        app.after_request(self._add_security_headers)
    
    def _security_check(self):
        """Perform security checks on incoming requests"""
        # Check content type for POST requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.content_type
            if not content_type:
                abort(400, "Content-Type header required")
            
            if not content_type.startswith(('application/json', 'multipart/form-data')):
                abort(415, "Unsupported Media Type")
        
        # Check for suspicious headers
        suspicious_headers = [
            'X-Forwarded-For',
            'X-Real-IP',
            'X-Originating-IP'
        ]
        
        for header in suspicious_headers:
            if header in request.headers:
                # Log potential proxy/load balancer headers
                logger.info(f"🔍 Proxy header detected: {header}: {request.headers[header]}")
        
        # Validate User-Agent
        user_agent = request.headers.get('User-Agent', '')
        if not user_agent or len(user_agent) < 10:
            logger.warning("⚠️  Suspicious or missing User-Agent")
        
        # Check for common attack patterns in URL
        if any(pattern in request.url for pattern in ['../', '..%2f', '..%5c']):
            logger.warning(f"⚠️  Directory traversal attempt: {request.url}")
            abort(400, "Invalid request")
    
    def _rate_limit_check(self):
        """Basic rate limiting check"""
        client_ip = request.remote_addr
        current_time = int(time.time())
        
        # Simple in-memory rate limiting (use Redis in production)
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        # Clean old requests (older than 1 hour)
        self.request_counts[client_ip] = [
            req_time for req_time in self.request_counts[client_ip]
            if current_time - req_time < 3600
        ]
        
        # Check rate limit
        if len(self.request_counts[client_ip]) >= SecurityConfig.DEFAULT_RATE_LIMIT:
            logger.warning(f"⚠️  Rate limit exceeded for IP: {client_ip}")
            abort(429, "Rate limit exceeded")
        
        # Add current request
        self.request_counts[client_ip].append(current_time)
    
    def _add_security_headers(self, response):
        """Add security headers to response"""
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Remove server header
        response.headers.pop('Server', None)
        
        return response


# Validation schemas
class SecureStoryRequestSchema(Schema):
    """Secure story request validation schema"""
    core_idea = fields.Str(required=True, validate=lambda x: 10 <= len(x) <= 2000)
    style = fields.Str(required=False, validate=lambda x: x in ['short_post', 'long_post', 'blog_post'])
    context = fields.Dict(required=False)
    
    @validates_schema
    def validate_request(self, data, **kwargs):
        """Validate entire request"""
        # Sanitize core_idea
        if 'core_idea' in data:
            data['core_idea'] = InputSanitizer.sanitize_string(data['core_idea'])
        
        # Validate JSON structure
        if not InputSanitizer.validate_json_structure(data):
            raise ValidationError("Invalid JSON structure")


class SecureFileUploadSchema(Schema):
    """Secure file upload validation schema"""
    file = fields.Raw(required=True)
    description = fields.Str(required=False, validate=lambda x: len(x) <= 500)
    
    @validates_schema
    def validate_file_upload(self, data, **kwargs):
        """Validate file upload"""
        if 'file' not in data:
            raise ValidationError("No file provided")
        
        file = data['file']
        if not isinstance(file, FileStorage):
            raise ValidationError("Invalid file format")
        
        # Validate file
        validation_result = FileValidator.validate_file(file)
        if not validation_result['valid']:
            raise ValidationError(f"File validation failed: {validation_result['errors']}")


# Decorators
def validate_json(schema_class: Schema):
    """Decorator to validate JSON input"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get JSON data
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No JSON data provided'}), 400
                
                # Validate with schema
                schema = schema_class()
                validated_data = schema.load(data)
                
                # Store validated data in request
                request.validated_data = validated_data
                
                return f(*args, **kwargs)
                
            except ValidationError as e:
                return jsonify({
                    'error': 'Validation failed',
                    'details': e.messages
                }), 400
            except Exception as e:
                logger.error(f"❌ Validation error: {e}")
                return jsonify({
                    'error': 'Invalid request',
                    'message': str(e)
                }), 400
        
        return decorated_function
    return decorator


def validate_file_upload():
    """Decorator to validate file uploads"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Check if file is in request
                if 'file' not in request.files:
                    return jsonify({'error': 'No file provided'}), 400
                
                file = request.files['file']
                
                # Validate file
                validation_result = FileValidator.validate_file(file)
                if not validation_result['valid']:
                    return jsonify({
                        'error': 'File validation failed',
                        'details': validation_result['errors']
                    }), 400
                
                # Store validation result
                request.file_validation = validation_result
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"❌ File validation error: {e}")
                return jsonify({
                    'error': 'File validation failed',
                    'message': str(e)
                }), 400
        
        return decorated_function
    return decorator


def require_https():
    """Decorator to require HTTPS"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_secure and not request.headers.get('X-Forwarded-Proto') == 'https':
                logger.warning("⚠️  Non-HTTPS request blocked")
                return jsonify({
                    'error': 'HTTPS required',
                    'message': 'This endpoint requires a secure connection'
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


import time

# Initialize security middleware
security_middleware = SecurityMiddleware()


def create_security_middleware(app):
    """Create and configure security middleware"""
    security_middleware.init_app(app)
    return security_middleware