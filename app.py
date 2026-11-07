"""
Enhanced Flask API for Richmond Storyline Generator
Includes error handling, validation, logging, and monitoring
"""
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pinecone.vectorstore import retrieve_context
from bedrock.bedrock_llm import generate_story
from config import config
from api_utils import (
    handle_errors, log_request, validate_request, 
    StoryRequestSchema, APIError, logger
)
from conversation_api import conversation_bp
from voice_api import voice_bp
from features_api import features_bp
import time
import uuid
import json

# Initialize configuration
config.initialize()

# Create Flask app
app = Flask(__name__)

# Enable CORS for frontend development
CORS(app, origins=["http://localhost:3000", "http://localhost:8080"])

# Register blueprints
app.register_blueprint(conversation_bp)
app.register_blueprint(voice_bp)
app.register_blueprint(features_bp)

# Configure max upload size for audio files
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB

# Request tracking
request_stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "average_response_time": 0
}


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        "status": "healthy",
        "service": "richmond-storyline-generator",
        "version": "1.0.0",
        "timestamp": time.time()
    })


@app.route("/stats", methods=["GET"])
def get_stats():
    """Get API usage statistics"""
    return jsonify(request_stats)


@app.route("/generate-story", methods=["POST"])
@handle_errors
@log_request
@validate_request(StoryRequestSchema)
def generate():
    """Generate a Richmond story based on user input"""
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Get validated data
    data = request.validated_data
    core_idea = data["core_idea"]
    style = data["style"]
    
    logger.info(f"Request {request_id}: Generating {style} for idea: {core_idea[:50]}...")
    
    try:
        # Update stats
        request_stats["total_requests"] += 1
        
        # Retrieve context with error handling
        logger.info(f"Request {request_id}: Retrieving context...")
        context_chunks = retrieve_context(core_idea)
        
        if not context_chunks:
            logger.warning(f"Request {request_id}: No context found")
            context_chunks = "No specific Richmond context found for this topic."
        
        # Generate story with timeout protection
        logger.info(f"Request {request_id}: Generating story...")
        story = generate_story(core_idea, context_chunks, style)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Update stats
        request_stats["successful_requests"] += 1
        total_requests = request_stats["total_requests"]
        request_stats["average_response_time"] = (
            (request_stats["average_response_time"] * (total_requests - 1) + response_time) 
            / total_requests
        )
        
        logger.info(f"Request {request_id}: Success in {response_time:.2f}s")
        
        return jsonify({
            "story": story,
            "metadata": {
                "request_id": request_id,
                "style": style,
                "response_time": f"{response_time:.2f}s",
                "context_retrieved": bool(context_chunks and context_chunks != "No specific Richmond context found for this topic.")
            }
        })
        
    except Exception as e:
        request_stats["failed_requests"] += 1
        logger.error(f"Request {request_id}: Failed - {str(e)}")
        raise APIError(f"Failed to generate story: {str(e)}", 500)


@app.route("/styles", methods=["GET"])
def get_styles():
    """Get available story styles and their descriptions"""
    return jsonify({
        "styles": [
            {
                "id": "short_post",
                "name": "Short Post",
                "description": "A concise story perfect for social media (300-500 words)",
                "max_tokens": config.TOKEN_LIMITS["short_post"]
            },
            {
                "id": "long_post",
                "name": "Long Post", 
                "description": "A detailed narrative with rich context (600-1000 words)",
                "max_tokens": config.TOKEN_LIMITS["long_post"]
            },
            {
                "id": "blog_post",
                "name": "Blog Post",
                "description": "A comprehensive article with full development (1000-2000 words)",
                "max_tokens": config.TOKEN_LIMITS["blog_post"]
            }
        ]
    })


@app.route("/voice-demo", methods=["GET"])
def voice_demo():
    """Serve voice recording demo page"""
    return render_template('voice_demo.html')


@app.route("/", methods=["GET"])
def index():
    """Welcome endpoint with API documentation"""
    return jsonify({
        "service": "Richmond Storyline Generator API",
        "version": "1.0.0",
        "endpoints": {
            "/": "This documentation",
            "/health": "Health check endpoint",
            "/stats": "API usage statistics",
            "/styles": "Get available story styles",
            "/generate-story": {
                "method": "POST",
                "description": "Generate a Richmond story",
                "body": {
                    "core_idea": "Your story idea (required, min 10 chars)",
                    "style": "short_post|long_post|blog_post (optional, default: short_post)"
                }
            }
        },
        "example": {
            "url": "POST /generate-story",
            "body": {
                "core_idea": "Richmond tech professionals returning from coastal cities",
                "style": "short_post"
            }
        }
    })


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist. See / for available endpoints."
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        "error": "Method not allowed",
        "message": f"{request.method} method is not allowed for this endpoint"
    }), 405


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred. Please try again later."
    }), 500


@app.before_request
def before_request():
    """Log all incoming requests"""
    logger.info(f"Incoming request: {request.method} {request.path} from {request.remote_addr}")


@app.after_request
def after_request(response):
    """Add security headers and log response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


if __name__ == "__main__":
    logger.info(f"Starting Richmond Storyline Generator API on port {config.FLASK_PORT}")
    app.run(
        debug=config.FLASK_DEBUG, 
        port=config.FLASK_PORT,
        host="0.0.0.0"  # Allow external connections
    )