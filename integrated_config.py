"""
Integrated Configuration Management for Richmond Storyline Generator
Unifies all configuration across environments with validation and security
"""

import os
import sys
import json
import secrets
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Application environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ServiceConfig:
    """Configuration for external services"""
    pinecone_api_key: str
    pinecone_environment: str = "us-east1-gcp"
    pinecone_index_name: str = "richmond-context"
    
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    
    openai_api_key: str = ""
    
    redis_url: str = "redis://localhost:6379"
    redis_session_db: int = 1
    redis_rate_limit_db: int = 2
    redis_cache_db: int = 3
    
    dynamodb_table_name: str = "storygen-sessions"
    s3_bucket_name: str = "storygen-uploads"


@dataclass
class SecurityConfig:
    """Security-related configuration"""
    jwt_secret_key: str
    encryption_key: str
    session_encryption_key: str
    local_encryption_key: str
    
    force_https: bool = True
    security_enabled: bool = True
    rate_limit_enabled: bool = True
    virus_scan_enabled: bool = True
    
    session_timeout_hours: int = 24
    jwt_access_token_expires: int = 3600  # 1 hour
    jwt_refresh_token_expires: int = 2592000  # 30 days
    
    allowed_origins: List[str] = field(default_factory=list)
    cors_enabled: bool = True
    
    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "Lax"


@dataclass
class ApplicationConfig:
    """Application-specific configuration"""
    flask_port: int = 5000
    flask_host: str = "0.0.0.0"
    flask_debug: bool = False
    
    # Model settings
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v1"
    
    # Story generation
    default_temperature: float = 0.7
    token_limits: Dict[str, int] = field(default_factory=lambda: {
        "short_post": 1024,
        "long_post": 2048,
        "blog_post": 4096
    })
    
    # Document processing
    chunk_size: int = 1000
    chunk_overlap: int = 100
    
    # File upload
    max_file_size: int = 26214400  # 25MB
    upload_directory: str = "./uploads"
    quarantine_directory: str = "./quarantine"
    
    # Performance
    cache_ttl: int = 3600  # 1 hour
    max_concurrent_requests: int = 100
    request_timeout: int = 30


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    
    grafana_enabled: bool = True
    grafana_port: int = 3000
    
    jaeger_enabled: bool = True
    jaeger_port: int = 16686
    
    log_level: str = "INFO"
    log_file: str = "./logs/storygen.log"
    
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    
    alert_email: Optional[str] = None
    alert_slack_webhook: Optional[str] = None


class IntegratedConfig:
    """Main configuration class that integrates all config sections"""
    
    def __init__(self, environment: Optional[str] = None):
        self.environment = Environment(environment or os.getenv("FLASK_ENV", "production"))
        self.base_dir = Path(__file__).resolve().parent
        
        # Initialize config sections
        self.services: Optional[ServiceConfig] = None
        self.security: Optional[SecurityConfig] = None
        self.application: Optional[ApplicationConfig] = None
        self.monitoring: Optional[MonitoringConfig] = None
        
        # Validation results
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
        
        # Load configuration
        self._load_configuration()
    
    def _load_configuration(self):
        """Load configuration from environment and files"""
        # Load service configuration
        self.services = self._load_service_config()
        
        # Load security configuration
        self.security = self._load_security_config()
        
        # Load application configuration
        self.application = self._load_application_config()
        
        # Load monitoring configuration
        self.monitoring = self._load_monitoring_config()
        
        # Apply environment-specific overrides
        self._apply_environment_overrides()
    
    def _load_service_config(self) -> ServiceConfig:
        """Load service configuration"""
        # Try to load from AWS Secrets Manager first
        aws_config = self._load_from_aws_secrets()
        
        return ServiceConfig(
            pinecone_api_key=aws_config.get("pinecone_api_key") or os.getenv("PINECONE_API_KEY", ""),
            pinecone_environment=os.getenv("PINECONE_ENVIRONMENT", "us-east1-gcp"),
            pinecone_index_name=os.getenv("PINECONE_INDEX_NAME", "richmond-context"),
            aws_access_key_id=aws_config.get("aws_access_key_id") or os.getenv("AWS_ACCESS_KEY_ID", ""),
            aws_secret_access_key=aws_config.get("aws_secret_access_key") or os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            openai_api_key=aws_config.get("openai_api_key") or os.getenv("OPENAI_API_KEY", ""),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            redis_session_db=int(os.getenv("REDIS_SESSION_DB", "1")),
            redis_rate_limit_db=int(os.getenv("REDIS_RATE_LIMIT_DB", "2")),
            redis_cache_db=int(os.getenv("REDIS_CACHE_DB", "3")),
            dynamodb_table_name=os.getenv("DYNAMODB_TABLE_NAME", "storygen-sessions"),
            s3_bucket_name=os.getenv("S3_BUCKET_NAME", "storygen-uploads")
        )
    
    def _load_security_config(self) -> SecurityConfig:
        """Load security configuration"""
        # Generate keys if not present
        jwt_secret = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(32)
        encryption_key = os.getenv("ENCRYPTION_KEY") or secrets.token_urlsafe(32)
        session_key = os.getenv("SESSION_ENCRYPTION_KEY") or secrets.token_urlsafe(32)
        local_key = os.getenv("LOCAL_ENCRYPTION_KEY") or secrets.token_urlsafe(32)
        
        # Load allowed origins
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
        allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]
        
        # Add development origins if in dev mode
        if self.environment == Environment.DEVELOPMENT:
            allowed_origins.extend([
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8080",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173"
            ])
        
        return SecurityConfig(
            jwt_secret_key=jwt_secret,
            encryption_key=encryption_key,
            session_encryption_key=session_key,
            local_encryption_key=local_key,
            force_https=os.getenv("FORCE_HTTPS", "true").lower() == "true",
            security_enabled=os.getenv("SECURITY_ENABLED", "true").lower() == "true",
            rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
            virus_scan_enabled=os.getenv("VIRUS_SCAN_ENABLED", "true").lower() == "true",
            session_timeout_hours=int(os.getenv("SESSION_TIMEOUT_HOURS", "24")),
            allowed_origins=allowed_origins,
            cors_enabled=os.getenv("CORS_ENABLED", "true").lower() == "true"
        )
    
    def _load_application_config(self) -> ApplicationConfig:
        """Load application configuration"""
        return ApplicationConfig(
            flask_port=int(os.getenv("FLASK_PORT", "5000")),
            flask_host=os.getenv("FLASK_HOST", "0.0.0.0"),
            flask_debug=self.environment == Environment.DEVELOPMENT and os.getenv("FLASK_DEBUG", "false").lower() == "true",
            bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"),
            bedrock_embedding_model_id=os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v1"),
            default_temperature=float(os.getenv("DEFAULT_TEMPERATURE", "0.7")),
            token_limits={
                "short_post": int(os.getenv("SHORT_POST_TOKENS", "1024")),
                "long_post": int(os.getenv("LONG_POST_TOKENS", "2048")),
                "blog_post": int(os.getenv("BLOG_POST_TOKENS", "4096"))
            },
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "100")),
            max_file_size=int(os.getenv("MAX_FILE_SIZE", str(26214400))),
            upload_directory=os.getenv("UPLOAD_DIRECTORY", "./uploads"),
            quarantine_directory=os.getenv("QUARANTINE_DIRECTORY", "./quarantine"),
            cache_ttl=int(os.getenv("CACHE_TTL", "3600")),
            max_concurrent_requests=int(os.getenv("MAX_CONCURRENT_REQUESTS", "100")),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30"))
        )
    
    def _load_monitoring_config(self) -> MonitoringConfig:
        """Load monitoring configuration"""
        return MonitoringConfig(
            prometheus_enabled=os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true",
            prometheus_port=int(os.getenv("PROMETHEUS_PORT", "9090")),
            grafana_enabled=os.getenv("GRAFANA_ENABLED", "true").lower() == "true",
            grafana_port=int(os.getenv("GRAFANA_PORT", "3000")),
            jaeger_enabled=os.getenv("JAEGER_ENABLED", "true").lower() == "true",
            jaeger_port=int(os.getenv("JAEGER_PORT", "16686")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "./logs/storygen.log"),
            metrics_enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
            tracing_enabled=os.getenv("TRACING_ENABLED", "true").lower() == "true",
            alert_email=os.getenv("ALERT_EMAIL"),
            alert_slack_webhook=os.getenv("ALERT_SLACK_WEBHOOK")
        )
    
    def _load_from_aws_secrets(self) -> Dict[str, Any]:
        """Try to load configuration from AWS Secrets Manager"""
        try:
            if not self.environment == Environment.PRODUCTION:
                return {}
            
            import boto3
            client = boto3.client('secretsmanager')
            
            # Try to get secrets
            secret_name = f"storygen/{self.environment.value}/api-keys"
            response = client.get_secret_value(SecretId=secret_name)
            
            if 'SecretString' in response:
                return json.loads(response['SecretString'])
            
            return {}
            
        except Exception as e:
            logger.warning(f"Could not load from AWS Secrets Manager: {e}")
            return {}
    
    def _apply_environment_overrides(self):
        """Apply environment-specific configuration overrides"""
        if self.environment == Environment.PRODUCTION:
            # Production overrides
            self.security.force_https = True
            self.security.security_enabled = True
            self.application.flask_debug = False
            self.monitoring.metrics_enabled = True
            self.monitoring.tracing_enabled = True
            
        elif self.environment == Environment.DEVELOPMENT:
            # Development overrides
            self.security.force_https = False
            self.application.flask_debug = True
            self.monitoring.prometheus_enabled = False
            self.monitoring.grafana_enabled = False
            self.monitoring.jaeger_enabled = False
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """Validate the complete configuration"""
        self.validation_errors = []
        self.validation_warnings = []
        
        # Validate required API keys
        if not self.services.pinecone_api_key:
            self.validation_errors.append("PINECONE_API_KEY is required")
        
        if not self.services.aws_access_key_id and self.environment == Environment.PRODUCTION:
            self.validation_errors.append("AWS_ACCESS_KEY_ID is required in production")
        
        if not self.services.openai_api_key:
            self.validation_warnings.append("OPENAI_API_KEY not set - voice transcription will not work")
        
        # Validate security in production
        if self.environment == Environment.PRODUCTION:
            if not self.security.force_https:
                self.validation_errors.append("HTTPS must be enforced in production")
            
            if not self.security.security_enabled:
                self.validation_errors.append("Security features must be enabled in production")
            
            if self.application.flask_debug:
                self.validation_errors.append("Debug mode must be disabled in production")
        
        # Validate paths
        paths_to_check = [
            Path(self.application.upload_directory),
            Path(self.application.quarantine_directory),
            Path(self.monitoring.log_file).parent
        ]
        
        for path in paths_to_check:
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    self.validation_warnings.append(f"Created directory: {path}")
                except Exception as e:
                    self.validation_errors.append(f"Could not create directory {path}: {e}")
        
        # Validate Redis connection
        try:
            import redis
            r = redis.from_url(self.services.redis_url)
            r.ping()
        except Exception as e:
            self.validation_warnings.append(f"Redis connection failed: {e}")
        
        is_valid = len(self.validation_errors) == 0
        return is_valid, self.validation_errors, self.validation_warnings
    
    def get_flask_config(self) -> Dict[str, Any]:
        """Get Flask-specific configuration dictionary"""
        return {
            "SECRET_KEY": self.security.jwt_secret_key,
            "DEBUG": self.application.flask_debug,
            "TESTING": False,
            "MAX_CONTENT_LENGTH": self.application.max_file_size,
            "UPLOAD_FOLDER": self.application.upload_directory,
            
            # Security
            "SESSION_COOKIE_SECURE": self.security.session_cookie_secure,
            "SESSION_COOKIE_HTTPONLY": self.security.session_cookie_httponly,
            "SESSION_COOKIE_SAMESITE": self.security.session_cookie_samesite,
            "PERMANENT_SESSION_LIFETIME": self.security.session_timeout_hours * 3600,
            
            # JWT
            "JWT_SECRET_KEY": self.security.jwt_secret_key,
            "JWT_ACCESS_TOKEN_EXPIRES": self.security.jwt_access_token_expires,
            "JWT_REFRESH_TOKEN_EXPIRES": self.security.jwt_refresh_token_expires
        }
    
    def get_bedrock_config(self) -> Dict[str, Any]:
        """Get Bedrock-specific configuration"""
        return {
            "model_id": self.application.bedrock_model_id,
            "embedding_model_id": self.application.bedrock_embedding_model_id,
            "region": self.services.aws_region,
            "temperature": self.application.default_temperature,
            "token_limits": self.application.token_limits
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration"""
        return {
            "url": self.services.redis_url,
            "session_db": self.services.redis_session_db,
            "rate_limit_db": self.services.redis_rate_limit_db,
            "cache_db": self.services.redis_cache_db
        }
    
    def display_config(self):
        """Display current configuration (with sensitive data masked)"""
        print("\n" + "=" * 60)
        print("🔧 INTEGRATED CONFIGURATION")
        print("=" * 60)
        
        print(f"\n📍 Environment: {self.environment.value}")
        print(f"📁 Base Directory: {self.base_dir}")
        
        print("\n🔑 Services:")
        print(f"  - Pinecone Index: {self.services.pinecone_index_name}")
        print(f"  - AWS Region: {self.services.aws_region}")
        print(f"  - Redis URL: {self.services.redis_url}")
        
        print("\n🔒 Security:")
        print(f"  - HTTPS Enforced: {self.security.force_https}")
        print(f"  - Security Enabled: {self.security.security_enabled}")
        print(f"  - Rate Limiting: {self.security.rate_limit_enabled}")
        print(f"  - Session Timeout: {self.security.session_timeout_hours}h")
        
        print("\n⚙️  Application:")
        print(f"  - Port: {self.application.flask_port}")
        print(f"  - Debug Mode: {self.application.flask_debug}")
        print(f"  - Model: {self.application.bedrock_model_id}")
        print(f"  - Max File Size: {self.application.max_file_size / 1024 / 1024:.1f}MB")
        
        print("\n📊 Monitoring:")
        print(f"  - Prometheus: {self.monitoring.prometheus_enabled} (port {self.monitoring.prometheus_port})")
        print(f"  - Grafana: {self.monitoring.grafana_enabled} (port {self.monitoring.grafana_port})")
        print(f"  - Log Level: {self.monitoring.log_level}")
        
        # Show validation status
        is_valid, errors, warnings = self.validate()
        
        if errors:
            print("\n❌ Validation Errors:")
            for error in errors:
                print(f"  - {error}")
        
        if warnings:
            print("\n⚠️  Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        
        if is_valid:
            print("\n✅ Configuration is valid and ready for use!")
        
        print("=" * 60)
    
    def export_env_template(self) -> str:
        """Export environment variable template"""
        template = f"""# Richmond Storyline Generator - Integrated Configuration
# Environment: {self.environment.value}
# Generated by IntegratedConfig

# ==== ENVIRONMENT ====
FLASK_ENV={self.environment.value}

# ==== API KEYS ====
PINECONE_API_KEY=your-pinecone-api-key
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
OPENAI_API_KEY=your-openai-api-key

# ==== SECURITY KEYS ====
JWT_SECRET_KEY={secrets.token_urlsafe(32)}
ENCRYPTION_KEY={secrets.token_urlsafe(32)}
SESSION_ENCRYPTION_KEY={secrets.token_urlsafe(32)}
LOCAL_ENCRYPTION_KEY={secrets.token_urlsafe(32)}

# ==== SERVICE CONFIGURATION ====
PINECONE_ENVIRONMENT={self.services.pinecone_environment}
PINECONE_INDEX_NAME={self.services.pinecone_index_name}
AWS_REGION={self.services.aws_region}
REDIS_URL={self.services.redis_url}

# ==== APPLICATION SETTINGS ====
FLASK_PORT={self.application.flask_port}
FLASK_HOST={self.application.flask_host}
FLASK_DEBUG={str(self.application.flask_debug).lower()}

# ==== SECURITY SETTINGS ====
FORCE_HTTPS={str(self.security.force_https).lower()}
SECURITY_ENABLED={str(self.security.security_enabled).lower()}
RATE_LIMIT_ENABLED={str(self.security.rate_limit_enabled).lower()}
CORS_ENABLED={str(self.security.cors_enabled).lower()}
ALLOWED_ORIGINS={','.join(self.security.allowed_origins)}

# ==== MONITORING ====
PROMETHEUS_ENABLED={str(self.monitoring.prometheus_enabled).lower()}
GRAFANA_ENABLED={str(self.monitoring.grafana_enabled).lower()}
LOG_LEVEL={self.monitoring.log_level}

# ==== MODEL CONFIGURATION ====
BEDROCK_MODEL_ID={self.application.bedrock_model_id}
DEFAULT_TEMPERATURE={self.application.default_temperature}

# ==== PERFORMANCE ====
CACHE_TTL={self.application.cache_ttl}
MAX_CONCURRENT_REQUESTS={self.application.max_concurrent_requests}
REQUEST_TIMEOUT={self.application.request_timeout}
"""
        return template


# Global configuration instance
_config: Optional[IntegratedConfig] = None


def get_config(environment: Optional[str] = None) -> IntegratedConfig:
    """Get or create the global configuration instance"""
    global _config
    
    if _config is None or (environment and _config.environment.value != environment):
        _config = IntegratedConfig(environment)
    
    return _config


def initialize_config(environment: Optional[str] = None) -> IntegratedConfig:
    """Initialize and validate configuration"""
    config = get_config(environment)
    
    # Display configuration
    config.display_config()
    
    # Validate
    is_valid, errors, warnings = config.validate()
    
    if not is_valid:
        print("\n❌ Configuration validation failed!")
        print("Please fix the errors before proceeding.")
        sys.exit(1)
    
    return config


if __name__ == "__main__":
    # Test configuration
    config = initialize_config()
    
    # Export template if requested
    if "--export" in sys.argv:
        template = config.export_env_template()
        
        output_file = Path(".env.template")
        output_file.write_text(template)
        
        print(f"\n✅ Environment template exported to: {output_file}")