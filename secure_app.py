"""
Secure Flask Application for Richmond Storyline Generator
Integrates all security components for production-ready deployment
"""

import logging
import os
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_talisman import Talisman
from werkzeug.middleware.proxy_fix import ProxyFix

# Import security components
from auth import AuthManager, create_auth_routes
from secrets_manager import initialize_secrets, get_secure_config
from secure_session_manager import get_session_manager
from security_middleware import create_security_middleware, validate_json, SecureStoryRequestSchema
from rate_limiter import rate_limit, strict_rate_limit, auth_rate_limit, upload_rate_limit
from secure_file_handler import get_file_handler

# Import business logic
from pinecone.vectorstore import retrieve_context
from bedrock.bedrock_llm import generate_story
from config import config
from api_utils import handle_errors, log_request, APIError, logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class SecureStoryGenApp:
    """Secure Story Generation Application"""
    
    def __init__(self):
        self.app = None
        self.auth_manager = None
        self.session_manager = None
        self.file_handler = None
        self.secure_config = None
        
    def create_app(self) -> Flask:
        """Create and configure the secure Flask application"""
        
        # Initialize secrets management
        logger.info("🔐 Initializing secure configuration...")
        initialize_secrets()
        self.secure_config = get_secure_config()
        
        # Create Flask app
        self.app = Flask(__name__)
        
        # Configure app with secure settings
        self._configure_app()
        
        # Initialize security components
        self._initialize_security()
        
        # Register routes
        self._register_routes()
        
        # Register error handlers
        self._register_error_handlers()
        
        logger.info("✅ Secure application initialized successfully")
        return self.app
    
    def _configure_app(self):
        """Configure Flask application with secure settings"""
        
        # Basic configuration
        self.app.config['SECRET_KEY'] = self.secure_config['jwt_secret']
        self.app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB
        
        # JWT configuration
        self.app.config['JWT_SECRET_KEY'] = self.secure_config['jwt_secret']
        self.app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600  # 1 hour
        self.app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 2592000  # 30 days
        
        # Security headers with Talisman
        self._configure_security_headers()
        
        # Proxy support for production
        self.app.wsgi_app = ProxyFix(self.app.wsgi_app, x_for=1, x_proto=1)
    
    def _configure_security_headers(self):
        """Configure comprehensive security headers"""
        
        csp = {
            'default-src': "'self'",
            'script-src': "'self' 'unsafe-inline'",
            'style-src': "'self' 'unsafe-inline'",
            'img-src': "'self' data:",
            'font-src': "'self'",
            'connect-src': "'self'",
            'frame-ancestors': "'none'",
            'base-uri': "'self'",
            'object-src': "'none'",
            'media-src': "'self'"
        }
        
        # Initialize Talisman with security headers
        Talisman(
            self.app,
            force_https=os.getenv('FORCE_HTTPS', 'true').lower() == 'true',
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,
            content_security_policy=csp,
            content_security_policy_nonce_in=['script-src', 'style-src'],
            referrer_policy='strict-origin-when-cross-origin',
            permissions_policy={
                'geolocation': '()',
                'microphone': '()',
                'camera': '()',
                'fullscreen': '()',
                'payment': '()',
                'usb': '()'
            }
        )
    
    def _initialize_security(self):
        """Initialize all security components"""
        
        # Authentication manager
        self.auth_manager = AuthManager(self.app)
        
        # Session manager
        self.session_manager = get_session_manager()
        
        # File handler
        self.file_handler = get_file_handler()
        
        # Security middleware
        create_security_middleware(self.app)
        
        # CORS configuration
        CORS(self.app, 
             origins=self._get_allowed_origins(),
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
             supports_credentials=True,
             max_age=3600)
        
        logger.info("✅ Security components initialized")
    
    def _get_allowed_origins(self) -> list:
        """Get allowed CORS origins"""
        allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
        allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]
        
        # Add localhost for development
        if os.getenv('FLASK_ENV') == 'development':
            allowed_origins.extend([
                'http://localhost:3000',
                'http://localhost:8080',
                'http://127.0.0.1:3000',
                'http://127.0.0.1:8080'
            ])
        
        return allowed_origins
    
    def _register_routes(self):
        """Register all application routes"""
        
        # Authentication routes
        create_auth_routes(self.app)
        
        # Health check route
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'service': 'richmond-storyline-generator',
                'version': '2.0.0-secure',
                'timestamp': time.time(),
                'security_enabled': True
            })
        
        # Protected story generation route
        @self.app.route('/generate-story', methods=['POST'])
        @rate_limit()
        @validate_json(SecureStoryRequestSchema)
        @handle_errors
        @log_request
        def generate_story_secure():
            """Generate a Richmond story with security controls"""
            
            # Get validated data
            data = request.validated_data
            core_idea = data['core_idea']
            style = data.get('style', 'short_post')
            
            # Log request
            logger.info(f"Story generation request: {core_idea[:50]}... (style: {style})")
            
            try:
                # Retrieve context
                context_chunks = retrieve_context(core_idea)
                if not context_chunks:
                    context_chunks = "No specific Richmond context found for this topic."
                
                # Generate story
                story = generate_story(core_idea, context_chunks, style)
                
                return jsonify({
                    'story': story,
                    'metadata': {
                        'style': style,
                        'context_retrieved': bool(context_chunks and context_chunks != "No specific Richmond context found for this topic."),
                        'security_validated': True
                    }
                })
                
            except Exception as e:
                logger.error(f"Story generation failed: {e}")
                raise APIError(f"Failed to generate story: {str(e)}", 500)
        
        # Secure file upload route
        @self.app.route('/upload-file', methods=['POST'])
        @upload_rate_limit()
        @handle_errors
        def upload_file_secure():
            """Secure file upload endpoint"""
            
            # Check if file is present
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            user_id = request.form.get('user_id', 'anonymous')
            
            # Validate file
            validation_result = self.file_handler.validate_file(file, user_id)
            
            if not validation_result['valid']:
                return jsonify({
                    'error': 'File validation failed',
                    'details': validation_result['errors']
                }), 400
            
            # Save file securely
            save_result = self.file_handler.save_file(file, user_id, validation_result)
            
            if not save_result['success']:
                return jsonify({
                    'error': 'File upload failed',
                    'details': save_result['error']
                }), 500
            
            return jsonify({
                'message': 'File uploaded successfully',
                'file_id': save_result['file_id'],
                'metadata': save_result['metadata']
            })
        
        # Get available story styles
        @self.app.route('/styles', methods=['GET'])
        @rate_limit()
        def get_styles():
            """Get available story styles"""
            return jsonify({
                'styles': [
                    {
                        'id': 'short_post',
                        'name': 'Short Post',
                        'description': 'A concise story perfect for social media (300-500 words)',
                        'max_tokens': config.TOKEN_LIMITS['short_post']
                    },
                    {
                        'id': 'long_post',
                        'name': 'Long Post',
                        'description': 'A detailed narrative with rich context (600-1000 words)',
                        'max_tokens': config.TOKEN_LIMITS['long_post']
                    },
                    {
                        'id': 'blog_post',
                        'name': 'Blog Post',
                        'description': 'A comprehensive article with full development (1000-2000 words)',
                        'max_tokens': config.TOKEN_LIMITS['blog_post']
                    }
                ]
            })
        
        # Security status endpoint
        @self.app.route('/security-status', methods=['GET'])
        @strict_rate_limit()
        def security_status():
            """Get security status information"""
            return jsonify({
                'security_enabled': True,
                'components': {
                    'authentication': bool(self.auth_manager),
                    'session_management': bool(self.session_manager),
                    'file_security': bool(self.file_handler),
                    'rate_limiting': True,
                    'input_validation': True,
                    'security_headers': True
                },
                'timestamp': time.time()
            })
    
    def _register_error_handlers(self):
        """Register error handlers"""
        
        @self.app.errorhandler(400)
        def bad_request(error):
            return jsonify({
                'error': 'Bad Request',
                'message': 'The request was invalid or malformed',
                'status_code': 400
            }), 400
        
        @self.app.errorhandler(401)
        def unauthorized(error):
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication required',
                'status_code': 401
            }), 401
        
        @self.app.errorhandler(403)
        def forbidden(error):
            return jsonify({
                'error': 'Forbidden',
                'message': 'Access denied',
                'status_code': 403
            }), 403
        
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested resource was not found',
                'status_code': 404
            }), 404
        
        @self.app.errorhandler(429)
        def rate_limit_exceeded(error):
            return jsonify({
                'error': 'Rate Limit Exceeded',
                'message': 'Too many requests. Please try again later.',
                'status_code': 429
            }), 429
        
        @self.app.errorhandler(500)
        def internal_error(error):
            logger.error(f"Internal server error: {str(error)}")
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred',
                'status_code': 500
            }), 500
        
        @self.app.errorhandler(APIError)
        def handle_api_error(error):
            return jsonify({
                'error': 'API Error',
                'message': error.message,
                'status_code': error.status_code
            }), error.status_code
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the secure application"""
        
        # Production security checks
        if not debug:
            # Check for HTTPS in production
            if not os.getenv('FORCE_HTTPS', 'true').lower() == 'true':
                logger.warning("⚠️  HTTPS enforcement is disabled in production")
            
            # Check for secure configuration
            if not self.secure_config:
                logger.error("❌ Secure configuration not available")
                raise RuntimeError("Cannot run in production without secure configuration")
        
        logger.info(f"🚀 Starting secure application on {host}:{port}")
        logger.info(f"🔒 Security features: Authentication, Rate Limiting, Input Validation, File Security")
        
        self.app.run(host=host, port=port, debug=debug, threaded=True)


# Create application factory
def create_secure_app():
    """Application factory for secure story generation app"""
    app_instance = SecureStoryGenApp()
    return app_instance.create_app()


if __name__ == '__main__':
    import time
    
    # Create secure application
    secure_app = SecureStoryGenApp()
    app = secure_app.create_app()
    
    # Run application
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    secure_app.run(port=port, debug=debug)