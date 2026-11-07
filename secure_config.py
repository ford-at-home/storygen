"""
Secure Configuration Management for Richmond Storyline Generator
Enhanced configuration with security-focused settings and validation
"""

import os
import sys
import secrets
from pathlib import Path
from typing import Dict, Any, List
from secrets_manager import secrets_manager


class SecureConfig:
    """Enhanced configuration with security features"""
    
    # Base paths
    BASE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BASE_DIR / "data"
    PROMPTS_DIR = BASE_DIR / "prompts"
    UPLOAD_DIR = BASE_DIR / "uploads"
    QUARANTINE_DIR = BASE_DIR / "quarantine"
    LOGS_DIR = BASE_DIR / "logs"
    
    # Environment detection
    ENVIRONMENT = os.getenv("FLASK_ENV", "production")
    IS_DEVELOPMENT = ENVIRONMENT == "development"
    IS_PRODUCTION = ENVIRONMENT == "production"
    
    # Security settings
    SECURITY_ENABLED = os.getenv("SECURITY_ENABLED", "true").lower() == "true"
    FORCE_HTTPS = os.getenv("FORCE_HTTPS", "true").lower() == "true"
    
    # Required security environment variables
    REQUIRED_SECURITY_VARS = [
        "JWT_SECRET_KEY",
        "ENCRYPTION_KEY",
        "SESSION_ENCRYPTION_KEY",
        "LOCAL_ENCRYPTION_KEY"
    ]
    
    # Required API keys (retrieved from secrets manager)
    REQUIRED_API_KEYS = [
        "PINECONE_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "OPENAI_API_KEY"
    ]
    
    # Optional environment variables with secure defaults
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east1-gcp")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "richmond-context")
    
    # Flask settings
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG = IS_DEVELOPMENT and os.getenv("FLASK_DEBUG", "false").lower() == "true"
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    
    # Model settings
    BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
    BEDROCK_EMBEDDING_MODEL_ID = os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v1")
    
    # Story generation settings
    DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
    TOKEN_LIMITS = {
        "short_post": int(os.getenv("SHORT_POST_TOKENS", "1024")),
        "long_post": int(os.getenv("LONG_POST_TOKENS", "2048")),
        "blog_post": int(os.getenv("BLOG_POST_TOKENS", "4096"))
    }
    
    # Document processing settings
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
    
    # Security configuration
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_STORAGE = os.getenv("RATE_LIMIT_STORAGE", "redis")
    
    # File upload security
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(25 * 1024 * 1024)))  # 25MB
    UPLOAD_DIRECTORY = os.getenv("UPLOAD_DIRECTORY", str(UPLOAD_DIR))
    QUARANTINE_DIRECTORY = os.getenv("QUARANTINE_DIRECTORY", str(QUARANTINE_DIR))
    ENABLE_VIRUS_SCAN = os.getenv("ENABLE_VIRUS_SCAN", "true").lower() == "true"
    
    # Redis configuration
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_SESSION_DB = int(os.getenv("REDIS_SESSION_DB", "1"))
    REDIS_RATE_LIMIT_DB = int(os.getenv("REDIS_RATE_LIMIT_DB", "2"))
    
    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "storygen.log"))
    
    # CORS configuration
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
    CORS_ENABLED = os.getenv("CORS_ENABLED", "true").lower() == "true"
    
    # Session configuration
    SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true"
    SESSION_COOKIE_HTTPONLY = os.getenv("SESSION_COOKIE_HTTPONLY", "true").lower() == "true"
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    
    # Database configuration (for future use)
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    
    @classmethod
    def generate_secure_keys(cls) -> Dict[str, str]:
        """Generate secure random keys for first-time setup"""
        return {
            "JWT_SECRET_KEY": secrets.token_urlsafe(32),
            "ENCRYPTION_KEY": secrets.token_urlsafe(32),
            "SESSION_ENCRYPTION_KEY": secrets.token_urlsafe(32),
            "LOCAL_ENCRYPTION_KEY": secrets.token_urlsafe(32)
        }
    
    @classmethod
    def validate_security_environment(cls) -> Dict[str, Any]:
        """Validate security environment configuration"""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "missing_vars": [],
            "security_status": {}
        }
        
        # Check required security variables
        missing_security_vars = []
        for var in cls.REQUIRED_SECURITY_VARS:
            if not os.getenv(var):
                missing_security_vars.append(var)
        
        if missing_security_vars:
            validation_results["missing_vars"].extend(missing_security_vars)
            validation_results["errors"].append(f"Missing security variables: {', '.join(missing_security_vars)}")
            validation_results["valid"] = False
        
        # Check API keys via secrets manager
        api_keys = secrets_manager.get_api_keys()
        missing_api_keys = []
        for key in cls.REQUIRED_API_KEYS:
            env_key = key.lower()
            if not api_keys.get(env_key):
                missing_api_keys.append(key)
        
        if missing_api_keys:
            validation_results["missing_vars"].extend(missing_api_keys)
            validation_results["errors"].append(f"Missing API keys: {', '.join(missing_api_keys)}")
            validation_results["valid"] = False
        
        # Security status checks
        validation_results["security_status"] = {
            "security_enabled": cls.SECURITY_ENABLED,
            "force_https": cls.FORCE_HTTPS,
            "rate_limiting": cls.RATE_LIMIT_ENABLED,
            "virus_scanning": cls.ENABLE_VIRUS_SCAN,
            "session_security": bool(os.getenv("SESSION_ENCRYPTION_KEY")),
            "cors_configured": bool(cls.ALLOWED_ORIGINS and cls.ALLOWED_ORIGINS[0]),
            "environment": cls.ENVIRONMENT
        }
        
        # Production-specific checks
        if cls.IS_PRODUCTION:
            if not cls.FORCE_HTTPS:
                validation_results["warnings"].append("HTTPS enforcement is disabled in production")
            
            if cls.FLASK_DEBUG:
                validation_results["warnings"].append("Debug mode enabled in production")
            
            if not cls.SECURITY_ENABLED:
                validation_results["errors"].append("Security features disabled in production")
                validation_results["valid"] = False
        
        return validation_results
    
    @classmethod
    def validate_paths(cls) -> Dict[str, Any]:
        """Validate and create required directories"""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "created_dirs": []
        }
        
        # Required directories
        required_dirs = [
            cls.DATA_DIR,
            cls.PROMPTS_DIR,
            cls.UPLOAD_DIR,
            cls.QUARANTINE_DIR,
            cls.LOGS_DIR
        ]
        
        for directory in required_dirs:
            try:
                directory.mkdir(exist_ok=True, parents=True)
                
                # Set secure permissions
                os.chmod(directory, 0o750)
                
                validation_results["created_dirs"].append(str(directory))
                
            except Exception as e:
                validation_results["errors"].append(f"Failed to create directory {directory}: {e}")
                validation_results["valid"] = False
        
        # Check for critical files
        story_prompt_path = cls.PROMPTS_DIR / "story_prompt.txt"
        if not story_prompt_path.exists():
            validation_results["warnings"].append(f"Story prompt template not found at {story_prompt_path}")
        
        return validation_results
    
    @classmethod
    def get_flask_config(cls) -> Dict[str, Any]:
        """Get Flask application configuration"""
        # Get secure configuration
        secure_config = secrets_manager.get_secure_config()
        
        config = {
            # Basic Flask settings
            "SECRET_KEY": secure_config.get("jwt_secret", os.getenv("JWT_SECRET_KEY", "")),
            "DEBUG": cls.FLASK_DEBUG,
            "TESTING": False,
            
            # Security settings
            "SESSION_COOKIE_SECURE": cls.SESSION_COOKIE_SECURE,
            "SESSION_COOKIE_HTTPONLY": cls.SESSION_COOKIE_HTTPONLY,
            "SESSION_COOKIE_SAMESITE": cls.SESSION_COOKIE_SAMESITE,
            "PERMANENT_SESSION_LIFETIME": cls.SESSION_TIMEOUT_HOURS * 3600,
            
            # File upload settings
            "MAX_CONTENT_LENGTH": cls.MAX_FILE_SIZE,
            "UPLOAD_FOLDER": cls.UPLOAD_DIRECTORY,
            
            # JWT settings
            "JWT_SECRET_KEY": secure_config.get("jwt_secret", os.getenv("JWT_SECRET_KEY", "")),
            "JWT_ACCESS_TOKEN_EXPIRES": 3600,  # 1 hour
            "JWT_REFRESH_TOKEN_EXPIRES": 30 * 24 * 3600,  # 30 days
            "JWT_BLACKLIST_ENABLED": True,
            "JWT_BLACKLIST_TOKEN_CHECKS": ["access", "refresh"],
            
            # Database settings (for future use)
            "SQLALCHEMY_DATABASE_URI": cls.DATABASE_URL,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "pool_size": cls.DB_POOL_SIZE,
                "max_overflow": cls.DB_MAX_OVERFLOW,
                "pool_pre_ping": True
            }
        }
        
        return config
    
    @classmethod
    def initialize_secure_config(cls) -> bool:
        """Initialize secure configuration"""
        print("🔐 Initializing secure configuration...")
        
        # Validate security environment
        security_validation = cls.validate_security_environment()
        
        if not security_validation["valid"]:
            print("❌ Security validation failed:")
            for error in security_validation["errors"]:
                print(f"   - {error}")
            
            # Generate secure keys if missing
            if security_validation["missing_vars"]:
                print("🔧 Generating secure keys...")
                secure_keys = cls.generate_secure_keys()
                
                print("💡 Please set these environment variables:")
                for key, value in secure_keys.items():
                    print(f"   export {key}='{value}'")
                
                return False
        
        # Show warnings
        if security_validation["warnings"]:
            print("⚠️  Security warnings:")
            for warning in security_validation["warnings"]:
                print(f"   - {warning}")
        
        # Validate paths
        path_validation = cls.validate_paths()
        
        if not path_validation["valid"]:
            print("❌ Path validation failed:")
            for error in path_validation["errors"]:
                print(f"   - {error}")
            return False
        
        # Show created directories
        if path_validation["created_dirs"]:
            print("📁 Created directories:")
            for directory in path_validation["created_dirs"]:
                print(f"   - {directory}")
        
        # Display security status
        print("🔒 Security Status:")
        for feature, enabled in security_validation["security_status"].items():
            status = "✅" if enabled else "❌"
            print(f"   {status} {feature.replace('_', ' ').title()}: {enabled}")
        
        print("✅ Secure configuration initialized successfully!")
        return True
    
    @classmethod
    def get_environment_template(cls) -> str:
        """Generate environment template with secure defaults"""
        template = """# Richmond Storyline Generator - Secure Configuration
# Generated by SecureConfig

# ==== SECURITY SETTINGS ====
FLASK_ENV=production
SECURITY_ENABLED=true
FORCE_HTTPS=true

# ==== CRYPTOGRAPHIC KEYS ====
# Generate these with: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=your_jwt_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here
SESSION_ENCRYPTION_KEY=your_session_encryption_key_here
LOCAL_ENCRYPTION_KEY=your_local_encryption_key_here

# ==== API KEYS ====
PINECONE_API_KEY=your_pinecone_api_key
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
OPENAI_API_KEY=your_openai_api_key

# ==== FLASK SETTINGS ====
FLASK_PORT=5000
FLASK_DEBUG=false
FLASK_HOST=0.0.0.0

# ==== AWS SETTINGS ====
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# ==== REDIS SETTINGS ====
REDIS_URL=redis://localhost:6379
REDIS_SESSION_DB=1
REDIS_RATE_LIMIT_DB=2

# ==== FILE UPLOAD SETTINGS ====
MAX_FILE_SIZE=26214400
UPLOAD_DIRECTORY=./uploads
QUARANTINE_DIRECTORY=./quarantine
ENABLE_VIRUS_SCAN=true

# ==== SECURITY FEATURES ====
RATE_LIMIT_ENABLED=true
CORS_ENABLED=true
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# ==== SESSION SETTINGS ====
SESSION_TIMEOUT_HOURS=24
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax

# ==== LOGGING ====
LOG_LEVEL=INFO
LOG_FILE=./logs/storygen.log

# ==== STORY GENERATION ====
DEFAULT_TEMPERATURE=0.7
SHORT_POST_TOKENS=1024
LONG_POST_TOKENS=2048
BLOG_POST_TOKENS=4096

# ==== DOCUMENT PROCESSING ====
CHUNK_SIZE=1000
CHUNK_OVERLAP=100
"""
        return template


# Create a convenience instance
secure_config = SecureConfig()


def initialize_secure_app_config():
    """Initialize secure application configuration"""
    return secure_config.initialize_secure_config()


def get_flask_config():
    """Get Flask configuration dictionary"""
    return secure_config.get_flask_config()


if __name__ == "__main__":
    # Initialize secure configuration
    if initialize_secure_app_config():
        print("🚀 Configuration ready for secure deployment!")
    else:
        print("❌ Configuration initialization failed")
        sys.exit(1)