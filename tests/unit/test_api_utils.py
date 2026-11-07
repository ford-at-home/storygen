"""
Unit tests for API utilities
"""
import pytest
import json
import logging
from unittest.mock import Mock, patch
from flask import Flask, request
from marshmallow import ValidationError
from api_utils import (
    StoryRequestSchema, handle_errors, log_request, 
    validate_request, APIError, logger
)


class TestStoryRequestSchema:
    """Test request validation schema"""
    
    def test_valid_request(self):
        """Test validation of valid request"""
        schema = StoryRequestSchema()
        data = {
            "core_idea": "Richmond tech scene is growing rapidly",
            "style": "short_post"
        }
        
        result = schema.load(data)
        assert result["core_idea"] == data["core_idea"]
        assert result["style"] == data["style"]
    
    def test_missing_core_idea(self):
        """Test validation with missing core_idea"""
        schema = StoryRequestSchema()
        data = {"style": "short_post"}
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        errors = exc_info.value.messages
        assert "core_idea" in errors
        assert "required" in str(errors["core_idea"]).lower()
    
    def test_short_core_idea(self):
        """Test validation with too short core_idea"""
        schema = StoryRequestSchema()
        data = {
            "core_idea": "short",  # Less than 10 chars
            "style": "short_post"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        errors = exc_info.value.messages
        assert "core_idea" in errors
        assert "at least 10 characters" in errors["core_idea"][0]
    
    def test_invalid_style(self):
        """Test validation with invalid style"""
        schema = StoryRequestSchema()
        data = {
            "core_idea": "Richmond tech scene is growing",
            "style": "invalid_style"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            schema.load(data)
        
        errors = exc_info.value.messages
        assert "style" in errors
        assert "must be one of" in errors["style"][0]
    
    def test_missing_style_uses_default(self):
        """Test that missing style uses default value"""
        schema = StoryRequestSchema()
        data = {"core_idea": "Richmond tech scene is growing"}
        
        result = schema.load(data)
        assert result["style"] == "short_post"  # Default value
    
    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored"""
        schema = StoryRequestSchema()
        data = {
            "core_idea": "Richmond tech scene is growing",
            "style": "short_post",
            "extra_field": "should be ignored"
        }
        
        result = schema.load(data)
        assert "extra_field" not in result
        assert len(result) == 2  # Only core_idea and style
    
    def test_whitespace_handling(self):
        """Test handling of whitespace in core_idea"""
        schema = StoryRequestSchema()
        
        # Leading/trailing whitespace should count
        data = {
            "core_idea": "   short   ",  # 11 chars with spaces
            "style": "short_post"
        }
        
        result = schema.load(data)
        assert result["core_idea"] == "   short   "
    
    def test_unicode_core_idea(self):
        """Test Unicode in core_idea"""
        schema = StoryRequestSchema()
        data = {
            "core_idea": "Richmond's café culture José María",  # Unicode chars
            "style": "short_post"
        }
        
        result = schema.load(data)
        assert "José" in result["core_idea"]
        assert "María" in result["core_idea"]


class TestErrorHandlingDecorator:
    """Test error handling decorator"""
    
    def test_handle_errors_success(self):
        """Test decorator with successful function"""
        @handle_errors
        def success_func():
            return {"status": "success"}, 200
        
        result, status = success_func()
        assert result["status"] == "success"
        assert status == 200
    
    def test_handle_errors_validation_error(self):
        """Test decorator handling ValidationError"""
        @handle_errors
        def validation_error_func():
            raise ValidationError({"field": ["Invalid value"]})
        
        with patch('api_utils.logger') as mock_logger:
            result, status = validation_error_func()
            
            # Check response
            assert status == 400
            assert result["error"] == "Validation error"
            assert "field" in result["details"]
            
            # Check logging
            mock_logger.warning.assert_called_once()
    
    def test_handle_errors_key_error(self):
        """Test decorator handling KeyError"""
        @handle_errors
        def key_error_func():
            raise KeyError("missing_field")
        
        with patch('api_utils.logger') as mock_logger:
            result, status = key_error_func()
            
            # Check response
            assert status == 400
            assert result["error"] == "Missing required field"
            assert result["field"] == "'missing_field'"
            
            # Check logging
            mock_logger.error.assert_called_once()
    
    def test_handle_errors_generic_exception(self):
        """Test decorator handling generic exception"""
        @handle_errors
        def generic_error_func():
            raise Exception("Something went wrong")
        
        with patch('api_utils.logger') as mock_logger:
            result, status = generic_error_func()
            
            # Check response
            assert status == 500
            assert result["error"] == "Internal server error"
            assert result["message"] == "An unexpected error occurred. Please try again later."
            
            # Check logging with traceback
            mock_logger.error.assert_called_once()
            assert mock_logger.error.call_args[1]["exc_info"] is True
    
    def test_handle_errors_preserves_function_name(self):
        """Test that decorator preserves function metadata"""
        @handle_errors
        def named_function():
            """Function docstring"""
            return "result", 200
        
        assert named_function.__name__ == "named_function"
        assert named_function.__doc__ == "Function docstring"


class TestLogRequestDecorator:
    """Test request logging decorator"""
    
    @patch('api_utils.logger')
    @patch('time.time')
    def test_log_request_success(self, mock_time, mock_logger):
        """Test request logging for successful request"""
        # Setup time mock
        mock_time.side_effect = [1000.0, 1001.5]  # 1.5 second duration
        
        # Create Flask app for request context
        app = Flask(__name__)
        
        @log_request
        def test_func():
            return {"result": "success"}, 200
        
        with app.test_request_context('/test', method='POST', 
                                     json={"data": "test"}):
            result, status = test_func()
            
            # Check logging calls
            assert mock_logger.info.call_count == 3
            
            # Check request logging
            first_call = mock_logger.info.call_args_list[0][0][0]
            assert "Request: POST /test" in first_call
            
            # Check body logging
            second_call = mock_logger.info.call_args_list[1][0][0]
            assert "Request body:" in second_call
            
            # Check response time logging
            third_call = mock_logger.info.call_args_list[2][0][0]
            assert "Response time: 1.50s" in third_call
    
    @patch('api_utils.logger')
    def test_log_request_no_json_body(self, mock_logger):
        """Test request logging without JSON body"""
        app = Flask(__name__)
        
        @log_request
        def test_func():
            return "OK", 200
        
        with app.test_request_context('/test', method='GET'):
            test_func()
            
            # Should log request but not body
            assert mock_logger.info.call_count == 2  # Request and response time
            calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert not any("Request body" in call for call in calls)
    
    @patch('api_utils.logger')
    def test_log_request_preserves_exception(self, mock_logger):
        """Test that logging doesn't swallow exceptions"""
        app = Flask(__name__)
        
        @log_request
        def test_func():
            raise ValueError("Test error")
        
        with app.test_request_context('/test'):
            with pytest.raises(ValueError) as exc_info:
                test_func()
            
            assert str(exc_info.value) == "Test error"


class TestValidateRequestDecorator:
    """Test request validation decorator"""
    
    def test_validate_request_success(self):
        """Test successful request validation"""
        app = Flask(__name__)
        
        @validate_request(StoryRequestSchema)
        def test_func():
            # Should have validated_data on request
            assert hasattr(request, 'validated_data')
            return request.validated_data, 200
        
        with app.test_request_context(
            '/test',
            method='POST',
            json={"core_idea": "Valid idea here", "style": "short_post"}
        ):
            result, status = test_func()
            assert status == 200
            assert result["core_idea"] == "Valid idea here"
            assert result["style"] == "short_post"
    
    def test_validate_request_no_json(self):
        """Test validation with no JSON data"""
        app = Flask(__name__)
        
        @validate_request(StoryRequestSchema)
        def test_func():
            return "OK", 200
        
        with app.test_request_context('/test', method='POST'):
            result, status = test_func()
            assert status == 400
            assert result["error"] == "No JSON data provided"
    
    def test_validate_request_validation_error(self):
        """Test validation with invalid data"""
        app = Flask(__name__)
        
        @validate_request(StoryRequestSchema)
        def test_func():
            return "OK", 200
        
        with app.test_request_context(
            '/test',
            method='POST',
            json={"core_idea": "short"}  # Too short
        ):
            result, status = test_func()
            assert status == 400
            assert result["error"] == "Validation error"
            assert "core_idea" in result["details"]
    
    def test_validate_request_preserves_metadata(self):
        """Test that decorator preserves function metadata"""
        @validate_request(StoryRequestSchema)
        def named_func():
            """Docstring"""
            return "OK", 200
        
        assert named_func.__name__ == "named_func"
        assert named_func.__doc__ == "Docstring"


class TestAPIError:
    """Test custom API error class"""
    
    def test_api_error_basic(self):
        """Test basic APIError creation"""
        error = APIError("Test error", 400)
        
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.status_code == 400
        assert error.details is None
    
    def test_api_error_with_details(self):
        """Test APIError with details"""
        details = {"field": "value", "reason": "invalid"}
        error = APIError("Validation failed", 422, details)
        
        assert error.message == "Validation failed"
        assert error.status_code == 422
        assert error.details == details
    
    def test_api_error_to_dict(self):
        """Test APIError to_dict method"""
        # Without details
        error1 = APIError("Simple error", 500)
        dict1 = error1.to_dict()
        assert dict1 == {"error": "Simple error"}
        
        # With details
        error2 = APIError("Complex error", 400, {"info": "additional"})
        dict2 = error2.to_dict()
        assert dict2 == {
            "error": "Complex error",
            "details": {"info": "additional"}
        }
    
    def test_api_error_default_status_code(self):
        """Test default status code is 500"""
        error = APIError("Error")
        assert error.status_code == 500


class TestLogger:
    """Test logger configuration"""
    
    def test_logger_exists(self):
        """Test that logger is properly configured"""
        assert logger is not None
        assert logger.name == 'storygen.api'
        assert isinstance(logger, logging.Logger)
    
    def test_logger_level(self):
        """Test logger level"""
        # Should be INFO or higher
        assert logger.level <= logging.INFO