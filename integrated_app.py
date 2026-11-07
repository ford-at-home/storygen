"""
Integrated Flask Application for Richmond Storyline Generator
Main entry point that combines all components into a cohesive system
"""

import os
import sys
import logging
import time
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_talisman import Talisman
from werkzeug.middleware.proxy_fix import ProxyFix

# Import integrated configuration
from integrated_config import get_config, Environment

# Import security components
from auth import AuthManager, create_auth_routes
from secrets_manager import initialize_secrets
from secure_session_manager import get_session_manager
from security_middleware import create_security_middleware, validate_json, SecureStoryRequestSchema
from rate_limiter import rate_limit, strict_rate_limit, auth_rate_limit, upload_rate_limit
from secure_file_handler import get_file_handler

# Import business logic components
from pinecone.vectorstore import retrieve_context
from bedrock.bedrock_llm import generate_story
from voice_processor import VoiceProcessor
from conversation_engine import ConversationEngine
from story_features import StoryFeatures
from cache import CacheManager
from metrics import MetricsCollector

# Import API modules
from conversation_api import create_conversation_routes
from voice_api import create_voice_routes
from features_api import create_features_routes
from api_utils import handle_errors, log_request, APIError, logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class IntegratedStoryGenApp:
    """Integrated Story Generation Application with all components"""
    
    def __init__(self, environment: str = None):
        self.config = get_config(environment)
        self.app = None
        
        # Component instances
        self.auth_manager = None
        self.session_manager = None
        self.file_handler = None
        self.voice_processor = None
        self.conversation_engine = None
        self.story_features = None
        self.cache_manager = None
        self.metrics_collector = None
        
    def create_app(self) -> Flask:
        """Create and configure the integrated Flask application"""
        
        logger.info("🚀 Starting Richmond Storyline Generator Integration...")
        
        # Validate configuration
        is_valid, errors, warnings = self.config.validate()
        if not is_valid:
            logger.error(f"Configuration validation failed: {errors}")
            sys.exit(1)
        
        # Initialize secrets if in production
        if self.config.environment == Environment.PRODUCTION:
            logger.info("🔐 Initializing secure secrets management...")
            initialize_secrets()
        
        # Create Flask app
        self.app = Flask(__name__, 
                        static_folder='frontend/dist',
                        static_url_path='')
        
        # Configure app
        self._configure_app()
        
        # Initialize all components
        self._initialize_components()
        
        # Setup middleware and security
        self._setup_middleware()
        
        # Register all routes
        self._register_routes()
        
        # Setup error handlers
        self._register_error_handlers()
        
        # Initialize monitoring
        self._setup_monitoring()
        
        logger.info("✅ Application integration complete!")
        return self.app
    
    def _configure_app(self):
        """Configure Flask application with integrated settings"""
        # Apply Flask configuration
        self.app.config.update(self.config.get_flask_config())
        
        # Additional production settings
        if self.config.environment == Environment.PRODUCTION:
            self.app.config['PREFERRED_URL_SCHEME'] = 'https'
            self.app.config['SESSION_COOKIE_SECURE'] = True
            self.app.config['SESSION_COOKIE_HTTPONLY'] = True
            self.app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    def _initialize_components(self):
        """Initialize all application components"""
        logger.info("🔧 Initializing application components...")
        
        # Security components
        self.auth_manager = AuthManager(self.app)
        self.session_manager = get_session_manager()
        self.file_handler = get_file_handler()
        
        # Business logic components
        self.voice_processor = VoiceProcessor()
        self.conversation_engine = ConversationEngine()
        self.story_features = StoryFeatures()
        
        # Infrastructure components
        self.cache_manager = CacheManager(
            redis_url=self.config.services.redis_url,
            db=self.config.services.redis_cache_db,
            default_ttl=self.config.application.cache_ttl
        )
        
        if self.config.monitoring.metrics_enabled:
            self.metrics_collector = MetricsCollector()
        
        logger.info("✅ All components initialized")
    
    def _setup_middleware(self):
        """Setup middleware and security layers"""
        # Proxy support for production
        if self.config.environment == Environment.PRODUCTION:
            self.app.wsgi_app = ProxyFix(self.app.wsgi_app, x_for=1, x_proto=1)
        
        # Security headers with Talisman
        if self.config.security.security_enabled:
            self._configure_security_headers()
        
        # Security middleware
        create_security_middleware(self.app)
        
        # CORS configuration
        if self.config.security.cors_enabled:
            CORS(self.app,
                 origins=self.config.security.allowed_origins,
                 methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
                 allow_headers=['Content-Type', 'Authorization', 'X-Requested-With'],
                 supports_credentials=True,
                 max_age=3600)
    
    def _configure_security_headers(self):
        """Configure comprehensive security headers"""
        csp = {
            'default-src': "'self'",
            'script-src': "'self' 'unsafe-inline' 'unsafe-eval'",  # For React
            'style-src': "'self' 'unsafe-inline'",
            'img-src': "'self' data: https:",
            'font-src': "'self' data:",
            'connect-src': "'self' ws: wss:",  # For WebSocket connections
            'frame-ancestors': "'none'",
            'base-uri': "'self'",
            'object-src': "'none'",
            'media-src': "'self' blob:"  # For voice recordings
        }
        
        Talisman(
            self.app,
            force_https=self.config.security.force_https,
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,
            content_security_policy=csp,
            content_security_policy_nonce_in=['script-src', 'style-src'],
            referrer_policy='strict-origin-when-cross-origin',
            permissions_policy={
                'geolocation': '()',
                'microphone': '(self)',  # Allow for voice recording
                'camera': '()',
                'fullscreen': '(self)',
                'payment': '()',
                'usb': '()'
            }
        )
    
    def _register_routes(self):
        """Register all application routes"""
        logger.info("🛣️  Registering application routes...")
        
        # Authentication routes
        create_auth_routes(self.app)
        
        # API routes
        create_conversation_routes(self.app, self.conversation_engine)
        create_voice_routes(self.app, self.voice_processor)
        create_features_routes(self.app, self.story_features)
        
        # Health and status endpoints
        self._register_health_routes()
        
        # Core story generation endpoint
        self._register_story_routes()
        
        # Static file serving for frontend
        self._register_static_routes()
        
        logger.info("✅ All routes registered")
    
    def _register_health_routes(self):
        """Register health check and status routes"""
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Comprehensive health check"""
            health_status = {
                'status': 'healthy',
                'service': 'richmond-storyline-generator',
                'version': '3.0.0-integrated',
                'timestamp': time.time(),
                'environment': self.config.environment.value,
                'components': {}
            }
            
            # Check Redis
            try:
                self.cache_manager.ping()
                health_status['components']['redis'] = 'healthy'
            except Exception as e:
                health_status['components']['redis'] = f'unhealthy: {str(e)}'
                health_status['status'] = 'degraded'
            
            # Check Pinecone
            try:
                from pinecone.vectorstore import init_vectorstore
                store = init_vectorstore()
                health_status['components']['pinecone'] = 'healthy'
            except Exception as e:
                health_status['components']['pinecone'] = f'unhealthy: {str(e)}'
                health_status['status'] = 'degraded'
            
            # Check AWS
            try:
                import boto3
                bedrock = boto3.client('bedrock-runtime', region_name=self.config.services.aws_region)
                health_status['components']['bedrock'] = 'healthy'
            except Exception as e:
                health_status['components']['bedrock'] = f'unhealthy: {str(e)}'
                health_status['status'] = 'degraded'
            
            status_code = 200 if health_status['status'] == 'healthy' else 503
            return jsonify(health_status), status_code
        
        @self.app.route('/api/status', methods=['GET'])
        @rate_limit()
        def system_status():
            """Get detailed system status"""
            return jsonify({
                'system': {
                    'environment': self.config.environment.value,
                    'uptime': time.time(),
                    'version': '3.0.0-integrated'
                },
                'configuration': {
                    'security_enabled': self.config.security.security_enabled,
                    'rate_limiting': self.config.security.rate_limit_enabled,
                    'cors_enabled': self.config.security.cors_enabled,
                    'metrics_enabled': self.config.monitoring.metrics_enabled
                },
                'services': {
                    'redis': self.config.services.redis_url.split('@')[-1] if '@' in self.config.services.redis_url else 'local',
                    'pinecone': self.config.services.pinecone_index_name,
                    'bedrock': self.config.application.bedrock_model_id
                }
            })
    
    def _register_story_routes(self):
        """Register core story generation routes"""
        
        @self.app.route('/api/generate-story', methods=['POST'])
        @rate_limit()
        @validate_json(SecureStoryRequestSchema)
        @handle_errors
        @log_request
        def generate_story_integrated():
            """Generate a Richmond story with all integrated features"""
            data = request.validated_data
            core_idea = data['core_idea']
            style = data.get('style', 'short_post')
            
            # Track metrics
            if self.metrics_collector:
                self.metrics_collector.increment('story_generation_requests')
            
            start_time = time.time()
            
            # Check cache first
            cache_key = f"story:{core_idea}:{style}"
            cached_story = self.cache_manager.get(cache_key)
            
            if cached_story:
                logger.info("Cache hit for story generation")
                if self.metrics_collector:
                    self.metrics_collector.increment('cache_hits')
                return jsonify({
                    'story': cached_story,
                    'metadata': {
                        'style': style,
                        'cached': True,
                        'generation_time': 0
                    }
                })
            
            try:
                # Retrieve context
                context_chunks = retrieve_context(core_idea)
                if not context_chunks:
                    context_chunks = "No specific Richmond context found for this topic."
                
                # Generate story
                story = generate_story(core_idea, context_chunks, style)
                
                # Cache the result
                self.cache_manager.set(cache_key, story, ttl=self.config.application.cache_ttl)
                
                # Track metrics
                generation_time = time.time() - start_time
                if self.metrics_collector:
                    self.metrics_collector.record_histogram('story_generation_time', generation_time)
                
                return jsonify({
                    'story': story,
                    'metadata': {
                        'style': style,
                        'context_retrieved': bool(context_chunks and context_chunks != "No specific Richmond context found for this topic."),
                        'cached': False,
                        'generation_time': generation_time
                    }
                })
                
            except Exception as e:
                logger.error(f"Story generation failed: {e}")
                if self.metrics_collector:
                    self.metrics_collector.increment('story_generation_errors')
                raise APIError(f"Failed to generate story: {str(e)}", 500)
        
        @self.app.route('/api/styles', methods=['GET'])
        @rate_limit()
        def get_styles():
            """Get available story styles"""
            return jsonify({
                'styles': [
                    {
                        'id': 'short_post',
                        'name': 'Short Post',
                        'description': 'A concise story perfect for social media (300-500 words)',
                        'max_tokens': self.config.application.token_limits['short_post']
                    },
                    {
                        'id': 'long_post',
                        'name': 'Long Post',
                        'description': 'A detailed narrative with rich context (600-1000 words)',
                        'max_tokens': self.config.application.token_limits['long_post']
                    },
                    {
                        'id': 'blog_post',
                        'name': 'Blog Post',
                        'description': 'A comprehensive article with full development (1000-2000 words)',
                        'max_tokens': self.config.application.token_limits['blog_post']
                    }
                ]
            })
    
    def _register_static_routes(self):
        """Register routes for serving the frontend"""
        
        @self.app.route('/', defaults={'path': ''})
        @self.app.route('/<path:path>')
        def serve(path):
            """Serve React application"""
            if path != "" and os.path.exists(self.app.static_folder + '/' + path):
                return send_from_directory(self.app.static_folder, path)
            else:
                return send_from_directory(self.app.static_folder, 'index.html')
    
    def _register_error_handlers(self):
        """Register comprehensive error handlers"""
        
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
    
    def _setup_monitoring(self):
        """Setup monitoring and observability"""
        if not self.config.monitoring.metrics_enabled:
            return
        
        logger.info("📊 Setting up monitoring...")
        
        # Prometheus metrics endpoint
        if self.config.monitoring.prometheus_enabled:
            from prometheus_client import make_wsgi_app
            from werkzeug.middleware.dispatcher import DispatcherMiddleware
            
            # Add prometheus metrics endpoint
            self.app.wsgi_app = DispatcherMiddleware(self.app.wsgi_app, {
                '/metrics': make_wsgi_app()
            })
        
        # Request tracking
        @self.app.before_request
        def track_request():
            request.start_time = time.time()
        
        @self.app.after_request
        def track_response(response):
            if hasattr(request, 'start_time'):
                duration = time.time() - request.start_time
                if self.metrics_collector:
                    self.metrics_collector.record_histogram(
                        'http_request_duration_seconds',
                        duration,
                        labels={
                            'method': request.method,
                            'endpoint': request.endpoint or 'unknown',
                            'status': response.status_code
                        }
                    )
            return response
    
    def run(self, host=None, port=None, debug=None):
        """Run the integrated application"""
        host = host or self.config.application.flask_host
        port = port or self.config.application.flask_port
        debug = debug if debug is not None else self.config.application.flask_debug
        
        # Final startup checks
        if self.config.environment == Environment.PRODUCTION and debug:
            logger.error("Cannot run in debug mode in production!")
            sys.exit(1)
        
        logger.info(f"🚀 Starting Richmond Storyline Generator on {host}:{port}")
        logger.info(f"🌍 Environment: {self.config.environment.value}")
        logger.info(f"🔒 Security: {'Enabled' if self.config.security.security_enabled else 'Disabled'}")
        logger.info(f"📊 Monitoring: {'Enabled' if self.config.monitoring.metrics_enabled else 'Disabled'}")
        
        # Use appropriate server for environment
        if self.config.environment == Environment.PRODUCTION:
            logger.info("🏭 Running in production mode with Gunicorn")
            # Production should use gunicorn, not direct Flask run
            return self.app
        else:
            # Development mode
            self.app.run(
                host=host,
                port=port,
                debug=debug,
                threaded=True,
                use_reloader=debug
            )


# Application factory
def create_integrated_app(environment: str = None) -> Flask:
    """Create the integrated application"""
    app_instance = IntegratedStoryGenApp(environment)
    return app_instance.create_app()


# Gunicorn entry point
def create_app():
    """Entry point for Gunicorn"""
    return create_integrated_app()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Richmond Storyline Generator - Integrated")
    parser.add_argument('--environment', choices=['development', 'staging', 'production'],
                      default=os.getenv('FLASK_ENV', 'development'),
                      help='Application environment')
    parser.add_argument('--port', type=int, default=None,
                      help='Port to run on')
    parser.add_argument('--host', default=None,
                      help='Host to bind to')
    
    args = parser.parse_args()
    
    # Create and run the application
    app_instance = IntegratedStoryGenApp(args.environment)
    app = app_instance.create_app()
    app_instance.run(host=args.host, port=args.port)