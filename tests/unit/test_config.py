"""
Unit tests for configuration management
"""
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, Mock
from config import Config


class TestConfigPaths:
    """Test configuration path handling"""
    
    def test_base_paths_initialization(self):
        """Test that base paths are correctly initialized"""
        # Paths should be Path objects
        assert isinstance(Config.BASE_DIR, Path)
        assert isinstance(Config.DATA_DIR, Path)
        assert isinstance(Config.PROMPTS_DIR, Path)
        
        # Verify relationships
        assert Config.DATA_DIR == Config.BASE_DIR / "data"
        assert Config.PROMPTS_DIR == Config.BASE_DIR / "prompts"
        
        # Verify BASE_DIR is correct
        assert Config.BASE_DIR.name == "storygen"


class TestEnvironmentVariables:
    """Test environment variable handling"""
    
    def test_required_env_vars_list(self):
        """Test required environment variables list"""
        assert "PINECONE_API_KEY" in Config.REQUIRED_ENV_VARS
        assert "AWS_ACCESS_KEY_ID" in Config.REQUIRED_ENV_VARS
        assert "AWS_SECRET_ACCESS_KEY" in Config.REQUIRED_ENV_VARS
        assert "OPENAI_API_KEY" in Config.REQUIRED_ENV_VARS
        assert len(Config.REQUIRED_ENV_VARS) == 4
    
    def test_optional_env_vars_defaults(self):
        """Test optional environment variables have defaults"""
        # Save original values
        original_values = {}
        optional_vars = [
            "AWS_REGION", "PINECONE_ENVIRONMENT", "PINECONE_INDEX_NAME",
            "FLASK_PORT", "FLASK_DEBUG", "BEDROCK_MODEL_ID"
        ]
        
        for var in optional_vars:
            if var in os.environ:
                original_values[var] = os.environ[var]
                del os.environ[var]
        
        try:
            # Reload config module to get defaults
            import importlib
            importlib.reload(sys.modules['config'])
            from config import Config as ReloadedConfig
            
            # Check defaults
            assert ReloadedConfig.AWS_REGION == "us-east-1"
            assert ReloadedConfig.PINECONE_ENVIRONMENT == "us-east1-gcp"
            assert ReloadedConfig.PINECONE_INDEX_NAME == "richmond-context"
            assert ReloadedConfig.FLASK_PORT == 5000
            assert ReloadedConfig.FLASK_DEBUG is True
            assert ReloadedConfig.BEDROCK_MODEL_ID == "anthropic.claude-3-sonnet-20240229-v1:0"
            
        finally:
            # Restore original values
            for var, value in original_values.items():
                os.environ[var] = value
    
    def test_token_limits(self):
        """Test token limit configuration"""
        assert Config.TOKEN_LIMITS["short_post"] == 1024
        assert Config.TOKEN_LIMITS["long_post"] == 2048
        assert Config.TOKEN_LIMITS["blog_post"] == 4096
        
        # All values should be integers
        for limit in Config.TOKEN_LIMITS.values():
            assert isinstance(limit, int)
    
    def test_chunk_settings(self):
        """Test document chunking settings"""
        assert Config.CHUNK_SIZE == 1000
        assert Config.CHUNK_OVERLAP == 100
        assert isinstance(Config.CHUNK_SIZE, int)
        assert isinstance(Config.CHUNK_OVERLAP, int)
        assert Config.CHUNK_OVERLAP < Config.CHUNK_SIZE


class TestConfigValidation:
    """Test configuration validation methods"""
    
    @patch('sys.exit')
    @patch('builtins.print')
    def test_validate_environment_missing_vars(self, mock_print, mock_exit, monkeypatch):
        """Test validation with missing required variables"""
        # Remove required env vars
        for var in Config.REQUIRED_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        
        # Run validation
        Config.validate_environment()
        
        # Should exit with error
        mock_exit.assert_called_once_with(1)
        
        # Should print error messages
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Missing required environment variables" in call for call in print_calls)
        assert any("PINECONE_API_KEY" in call for call in print_calls)
    
    @patch('builtins.print')
    def test_validate_environment_all_vars_present(self, mock_print, test_config):
        """Test validation with all required variables present"""
        # All vars are set by test_config fixture
        Config.validate_environment()
        
        # Should not print any missing var messages
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert not any("Missing required" in call for call in print_calls)
    
    @patch('builtins.print')
    def test_validate_environment_invalid_region(self, mock_print, test_config, monkeypatch):
        """Test validation with invalid AWS region"""
        monkeypatch.setenv("AWS_REGION", "invalid-region")
        
        # Reload config to pick up new region
        import importlib
        importlib.reload(sys.modules['config'])
        from config import Config as ReloadedConfig
        
        ReloadedConfig.validate_environment()
        
        # Should print warning about region
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Warning: AWS_REGION" in call for call in print_calls)
        assert any("invalid-region" in call for call in print_calls)
    
    @patch('pathlib.Path.mkdir')
    def test_validate_paths_creates_directories(self, mock_mkdir):
        """Test that validate_paths creates missing directories"""
        Config.validate_paths()
        
        # Should create both directories
        assert mock_mkdir.call_count >= 2
        mock_mkdir.assert_any_call(exist_ok=True)
    
    @patch('pathlib.Path.exists')
    @patch('builtins.print')
    def test_validate_paths_missing_prompt_file(self, mock_print, mock_exists):
        """Test validation when prompt file is missing"""
        # Mock that prompt file doesn't exist
        mock_exists.return_value = False
        
        Config.validate_paths()
        
        # Should print warning
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Warning: Story prompt template not found" in call for call in print_calls)


class TestConfigInitialization:
    """Test configuration initialization"""
    
    @patch('config.Config.validate_environment')
    @patch('config.Config.validate_paths')
    @patch('builtins.print')
    def test_initialize_success(self, mock_print, mock_validate_paths, mock_validate_env, test_config):
        """Test successful initialization"""
        Config.initialize()
        
        # Should call both validation methods
        mock_validate_env.assert_called_once()
        mock_validate_paths.assert_called_once()
        
        # Should print success message
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Configuration validated successfully" in call for call in print_calls)
        assert any(f"Data directory: {Config.DATA_DIR}" in call for call in print_calls)
    
    @patch('config.Config.validate_environment')
    def test_initialize_validation_error(self, mock_validate_env):
        """Test initialization with validation error"""
        # Mock validation to raise exception
        mock_validate_env.side_effect = Exception("Validation failed")
        
        # Should propagate exception
        with pytest.raises(Exception) as exc_info:
            Config.initialize()
        
        assert "Validation failed" in str(exc_info.value)


class TestConfigHelpers:
    """Test configuration helper methods"""
    
    def test_get_env_example(self):
        """Test environment example generation"""
        example = Config.get_env_example()
        
        # Should be a string
        assert isinstance(example, str)
        
        # Should contain all required variables
        for var in Config.REQUIRED_ENV_VARS:
            assert var in example
        
        # Should contain helpful placeholders
        assert "your-pinecone-api-key" in example
        assert "your-aws-access-key" in example
        
        # Should contain optional variables
        assert "AWS_REGION=" in example
        assert "FLASK_PORT=" in example
        
        # Should be valid env file format
        lines = example.strip().split('\n')
        for line in lines:
            if line and not line.startswith('#'):
                assert '=' in line


class TestConfigSingleton:
    """Test config singleton instance"""
    
    def test_config_instance_exists(self):
        """Test that config instance is created"""
        from config import config
        assert config is not None
        assert isinstance(config, Config)
    
    def test_config_instance_has_attributes(self):
        """Test that config instance has all attributes"""
        from config import config
        
        # Check required attributes
        assert hasattr(config, 'BASE_DIR')
        assert hasattr(config, 'DATA_DIR')
        assert hasattr(config, 'PROMPTS_DIR')
        assert hasattr(config, 'AWS_REGION')
        assert hasattr(config, 'TOKEN_LIMITS')


class TestConfigEdgeCases:
    """Test configuration edge cases"""
    
    def test_empty_env_var_handling(self, monkeypatch):
        """Test handling of empty environment variables"""
        monkeypatch.setenv("AWS_REGION", "")
        
        # Reload config
        import importlib
        importlib.reload(sys.modules['config'])
        from config import Config as ReloadedConfig
        
        # Empty string should be used (not default)
        assert ReloadedConfig.AWS_REGION == ""
    
    def test_boolean_env_var_parsing(self, monkeypatch):
        """Test boolean environment variable parsing"""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("1", False),  # Only 'true' should be True
            ("yes", False),
            ("", False)
        ]
        
        for value, expected in test_cases:
            monkeypatch.setenv("FLASK_DEBUG", value)
            
            # Reload config
            import importlib
            importlib.reload(sys.modules['config'])
            from config import Config as ReloadedConfig
            
            assert ReloadedConfig.FLASK_DEBUG == expected, f"Failed for value: {value}"
    
    def test_numeric_env_var_parsing(self, monkeypatch):
        """Test numeric environment variable parsing"""
        # Test integer parsing
        monkeypatch.setenv("FLASK_PORT", "8080")
        monkeypatch.setenv("SHORT_POST_TOKENS", "512")
        
        # Test float parsing
        monkeypatch.setenv("DEFAULT_TEMPERATURE", "0.9")
        
        # Reload config
        import importlib
        importlib.reload(sys.modules['config'])
        from config import Config as ReloadedConfig
        
        assert ReloadedConfig.FLASK_PORT == 8080
        assert ReloadedConfig.TOKEN_LIMITS["short_post"] == 512
        assert ReloadedConfig.DEFAULT_TEMPERATURE == 0.9