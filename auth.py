"""
Authentication and Authorization Module for Richmond Storyline Generator
Implements JWT-based authentication with user management and secure session handling
"""

import os
import uuid
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Dict, Any

import bcrypt
import jwt
from flask import Flask, request, jsonify, current_app
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    get_jwt_identity, jwt_required, get_jwt, verify_jwt_in_request
)
from marshmallow import Schema, fields, ValidationError
import redis
from cryptography.fernet import Fernet

from config import config


class UserSchema(Schema):
    """User registration/login validation schema"""
    username = fields.Str(required=True, validate=lambda x: 3 <= len(x) <= 50)
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=lambda x: len(x) >= 8)
    full_name = fields.Str(required=False, validate=lambda x: len(x) <= 100)


class LoginSchema(Schema):
    """Login validation schema"""
    username = fields.Str(required=True)
    password = fields.Str(required=True)


class AuthenticationError(Exception):
    """Custom authentication error"""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthManager:
    """Manages user authentication and session security"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.jwt_manager = None
        self.redis_client = None
        self.cipher_suite = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize authentication with Flask app"""
        self.app = app
        
        # Configure JWT
        app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', self._generate_secret_key())
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
        app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
        app.config['JWT_BLACKLIST_ENABLED'] = True
        app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']
        
        # Initialize JWT manager
        self.jwt_manager = JWTManager(app)
        
        # Initialize Redis for session storage
        self._init_redis()
        
        # Initialize encryption
        self._init_encryption()
        
        # Register JWT callbacks
        self._register_jwt_callbacks()
    
    def _init_redis(self):
        """Initialize Redis connection for session storage"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            print("✅ Redis connected successfully")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            print("⚠️  Falling back to in-memory session storage (not recommended for production)")
            self.redis_client = None
    
    def _init_encryption(self):
        """Initialize encryption for sensitive data"""
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            encryption_key = Fernet.generate_key()
            print(f"⚠️  Generated new encryption key: {encryption_key.decode()}")
            print("   Please set ENCRYPTION_KEY environment variable for production")
        else:
            encryption_key = encryption_key.encode()
        
        self.cipher_suite = Fernet(encryption_key)
    
    def _generate_secret_key(self) -> str:
        """Generate a secure random secret key"""
        return os.urandom(32).hex()
    
    def _register_jwt_callbacks(self):
        """Register JWT event callbacks"""
        
        @self.jwt_manager.token_in_blocklist_loader
        def check_if_token_revoked(jwt_header, jwt_payload):
            """Check if token is revoked"""
            jti = jwt_payload['jti']
            return self._is_token_revoked(jti)
        
        @self.jwt_manager.expired_token_loader
        def expired_token_callback(jwt_header, jwt_payload):
            return jsonify({
                'error': 'Token has expired',
                'message': 'Please log in again'
            }), 401
        
        @self.jwt_manager.invalid_token_loader
        def invalid_token_callback(error):
            return jsonify({
                'error': 'Invalid token',
                'message': 'Please provide a valid token'
            }), 401
        
        @self.jwt_manager.unauthorized_loader
        def missing_token_callback(error):
            return jsonify({
                'error': 'Authorization required',
                'message': 'Please log in to access this resource'
            }), 401
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user with encrypted storage"""
        try:
            # Validate input
            schema = UserSchema()
            validated_data = schema.load(user_data)
            
            # Check if user already exists
            if self._user_exists(validated_data['username'], validated_data['email']):
                raise AuthenticationError("User already exists", 409)
            
            # Hash password
            hashed_password = self.hash_password(validated_data['password'])
            
            # Create user record
            user_id = str(uuid.uuid4())
            user_record = {
                'user_id': user_id,
                'username': validated_data['username'],
                'email': validated_data['email'],
                'password_hash': hashed_password,
                'full_name': validated_data.get('full_name', ''),
                'created_at': datetime.utcnow().isoformat(),
                'is_active': True,
                'failed_login_attempts': 0,
                'last_login': None
            }
            
            # Store user (encrypted)
            self._store_user(user_record)
            
            # Remove sensitive data before returning
            user_record.pop('password_hash', None)
            return user_record
            
        except ValidationError as e:
            raise AuthenticationError(f"Validation error: {e.messages}", 400)
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials"""
        try:
            # Validate input
            schema = LoginSchema()
            validated_data = schema.load({'username': username, 'password': password})
            
            # Get user record
            user_record = self._get_user_by_username(validated_data['username'])
            if not user_record:
                raise AuthenticationError("Invalid credentials", 401)
            
            # Check if account is locked
            if user_record.get('failed_login_attempts', 0) >= 5:
                raise AuthenticationError("Account locked due to too many failed attempts", 423)
            
            # Verify password
            if not self.verify_password(validated_data['password'], user_record['password_hash']):
                # Increment failed attempts
                user_record['failed_login_attempts'] = user_record.get('failed_login_attempts', 0) + 1
                self._update_user(user_record)
                raise AuthenticationError("Invalid credentials", 401)
            
            # Reset failed attempts and update last login
            user_record['failed_login_attempts'] = 0
            user_record['last_login'] = datetime.utcnow().isoformat()
            self._update_user(user_record)
            
            # Remove sensitive data
            user_record.pop('password_hash', None)
            return user_record
            
        except ValidationError as e:
            raise AuthenticationError(f"Validation error: {e.messages}", 400)
    
    def create_tokens(self, user_id: str) -> Dict[str, str]:
        """Create access and refresh tokens"""
        access_token = create_access_token(identity=user_id)
        refresh_token = create_refresh_token(identity=user_id)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
    
    def revoke_token(self, jti: str):
        """Revoke a token by adding it to blacklist"""
        if self.redis_client:
            # Store in Redis with expiration
            self.redis_client.setex(f"revoked_token:{jti}", 3600, "true")
        else:
            # Store in memory (not persistent)
            if not hasattr(self, '_revoked_tokens'):
                self._revoked_tokens = set()
            self._revoked_tokens.add(jti)
    
    def _is_token_revoked(self, jti: str) -> bool:
        """Check if token is revoked"""
        if self.redis_client:
            return self.redis_client.exists(f"revoked_token:{jti}")
        else:
            return hasattr(self, '_revoked_tokens') and jti in self._revoked_tokens
    
    def _user_exists(self, username: str, email: str) -> bool:
        """Check if user exists by username or email"""
        return (self._get_user_by_username(username) is not None or 
                self._get_user_by_email(email) is not None)
    
    def _store_user(self, user_record: Dict[str, Any]):
        """Store user record (encrypted)"""
        if self.redis_client:
            encrypted_data = self.cipher_suite.encrypt(str(user_record).encode())
            self.redis_client.hset(
                "users", 
                user_record['username'], 
                encrypted_data.decode()
            )
            self.redis_client.hset(
                "user_emails", 
                user_record['email'], 
                user_record['username']
            )
        else:
            # Fallback to memory storage
            if not hasattr(self, '_users'):
                self._users = {}
                self._user_emails = {}
            self._users[user_record['username']] = user_record
            self._user_emails[user_record['email']] = user_record['username']
    
    def _get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        if self.redis_client:
            encrypted_data = self.redis_client.hget("users", username)
            if encrypted_data:
                decrypted_data = self.cipher_suite.decrypt(encrypted_data.encode())
                return eval(decrypted_data.decode())  # Note: In production, use proper serialization
        else:
            return getattr(self, '_users', {}).get(username)
        return None
    
    def _get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        if self.redis_client:
            username = self.redis_client.hget("user_emails", email)
            if username:
                return self._get_user_by_username(username)
        else:
            username = getattr(self, '_user_emails', {}).get(email)
            if username:
                return self._get_user_by_username(username)
        return None
    
    def _update_user(self, user_record: Dict[str, Any]):
        """Update user record"""
        self._store_user(user_record)


# Global auth manager instance
auth_manager = AuthManager()


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'error': 'Authentication required',
                'message': str(e)
            }), 401
    return decorated_function


def get_current_user() -> Optional[str]:
    """Get current authenticated user ID"""
    try:
        return get_jwt_identity()
    except:
        return None


def create_auth_routes(app: Flask):
    """Create authentication routes"""
    
    @app.route('/auth/register', methods=['POST'])
    def register():
        """User registration endpoint"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            user_record = auth_manager.create_user(data)
            tokens = auth_manager.create_tokens(user_record['user_id'])
            
            return jsonify({
                'message': 'User created successfully',
                'user': user_record,
                'tokens': tokens
            }), 201
            
        except AuthenticationError as e:
            return jsonify({'error': e.message}), e.status_code
        except Exception as e:
            return jsonify({'error': 'Registration failed', 'message': str(e)}), 500
    
    @app.route('/auth/login', methods=['POST'])
    def login():
        """User login endpoint"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            user_record = auth_manager.authenticate_user(
                data.get('username'), 
                data.get('password')
            )
            
            tokens = auth_manager.create_tokens(user_record['user_id'])
            
            return jsonify({
                'message': 'Login successful',
                'user': user_record,
                'tokens': tokens
            }), 200
            
        except AuthenticationError as e:
            return jsonify({'error': e.message}), e.status_code
        except Exception as e:
            return jsonify({'error': 'Login failed', 'message': str(e)}), 500
    
    @app.route('/auth/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def refresh():
        """Refresh access token"""
        try:
            current_user = get_jwt_identity()
            new_access_token = create_access_token(identity=current_user)
            
            return jsonify({
                'access_token': new_access_token
            }), 200
            
        except Exception as e:
            return jsonify({'error': 'Token refresh failed', 'message': str(e)}), 500
    
    @app.route('/auth/logout', methods=['POST'])
    @jwt_required()
    def logout():
        """Logout and revoke token"""
        try:
            jti = get_jwt()['jti']
            auth_manager.revoke_token(jti)
            
            return jsonify({'message': 'Successfully logged out'}), 200
            
        except Exception as e:
            return jsonify({'error': 'Logout failed', 'message': str(e)}), 500
    
    @app.route('/auth/profile', methods=['GET'])
    @jwt_required()
    def profile():
        """Get user profile"""
        try:
            current_user_id = get_jwt_identity()
            # In a real app, you'd fetch the user from database
            return jsonify({
                'user_id': current_user_id,
                'message': 'Profile retrieved successfully'
            }), 200
            
        except Exception as e:
            return jsonify({'error': 'Profile retrieval failed', 'message': str(e)}), 500