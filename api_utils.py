"""
API utilities for error handling, validation, and logging
"""
import functools
import logging
import time
from flask import jsonify, request
from marshmallow import Schema, fields, ValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('storygen.api')


class StoryRequestSchema(Schema):
    """Schema for story generation request validation"""
    core_idea = fields.Str(required=True, validate=lambda x: len(x) > 10,
                          error_messages={"validator_failed": "Core idea must be at least 10 characters"})
    style = fields.Str(missing="short_post", 
                      validate=lambda x: x in ["short_post", "long_post", "blog_post"],
                      error_messages={"validator_failed": "Style must be one of: short_post, long_post, blog_post"})


def handle_errors(f):
    """Decorator for consistent error handling"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error: {e.messages}")
            return jsonify({
                "error": "Validation error",
                "details": e.messages
            }), 400
        except KeyError as e:
            logger.error(f"Missing required field: {str(e)}")
            return jsonify({
                "error": "Missing required field",
                "field": str(e)
            }), 400
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later."
            }), 500
    return decorated_function


def log_request(f):
    """Decorator to log API requests"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.path}")
        if request.is_json:
            logger.info(f"Request body: {request.get_json()}")
        
        # Execute function
        result = f(*args, **kwargs)
        
        # Log response
        duration = time.time() - start_time
        logger.info(f"Response time: {duration:.2f}s")
        
        return result
    return decorated_function


def validate_request(schema_class):
    """Decorator to validate request data against a schema"""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            schema = schema_class()
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No JSON data provided"}), 400
                    
                validated_data = schema.load(data)
                request.validated_data = validated_data
            except ValidationError as e:
                return jsonify({
                    "error": "Validation error",
                    "details": e.messages
                }), 400
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator


class APIError(Exception):
    """Custom API exception class"""
    def __init__(self, message, status_code=500, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details
        
    def to_dict(self):
        response = {"error": self.message}
        if self.details:
            response["details"] = self.details
        return response