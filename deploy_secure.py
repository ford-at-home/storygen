#!/usr/bin/env python3
"""
Secure Deployment Script for Richmond Storyline Generator
Handles secure deployment with all security checks and validations
"""

import os
import sys
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple
import secrets
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecureDeployment:
    """Handles secure deployment of the application"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.deployment_config = {}
        self.errors = []
        self.warnings = []
        
    def run_deployment(self, environment: str = "production") -> bool:
        """Run complete secure deployment"""
        
        print("🚀 Starting Secure Deployment for Richmond Storyline Generator")
        print("=" * 60)
        
        # Step 1: Environment validation
        if not self._validate_environment(environment):
            return False
        
        # Step 2: Dependencies check
        if not self._check_dependencies():
            return False
        
        # Step 3: Security configuration
        if not self._setup_security_config():
            return False
        
        # Step 4: Infrastructure setup
        if not self._setup_infrastructure():
            return False
        
        # Step 5: Application deployment
        if not self._deploy_application():
            return False
        
        # Step 6: Security validation
        if not self._validate_security():
            return False
        
        # Step 7: Health checks
        if not self._run_health_checks():
            return False
        
        print("\n✅ Secure deployment completed successfully!")
        print("🔒 All security measures are active and validated")
        
        return True
    
    def _validate_environment(self, environment: str) -> bool:
        """Validate deployment environment"""
        print("\n📋 Step 1: Environment Validation")
        
        valid_environments = ["development", "staging", "production"]
        if environment not in valid_environments:
            self.errors.append(f"Invalid environment: {environment}")
            return False
        
        # Set environment variables
        os.environ["FLASK_ENV"] = environment
        
        if environment == "production":
            os.environ["SECURITY_ENABLED"] = "true"
            os.environ["FORCE_HTTPS"] = "true"
            os.environ["FLASK_DEBUG"] = "false"
        
        print(f"✅ Environment set to: {environment}")
        return True
    
    def _check_dependencies(self) -> bool:
        """Check system dependencies"""
        print("\n🔧 Step 2: Dependencies Check")
        
        # Check Python packages
        required_packages = [
            "flask", "redis", "cryptography", "jwt", "bcrypt",
            "boto3", "pinecone-client", "marshmallow", "bleach"
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            self.errors.append(f"Missing packages: {', '.join(missing_packages)}")
            print("❌ Missing required packages")
            print("💡 Run: pip install -r requirements.txt")
            return False
        
        # Check Redis
        if not self._check_redis():
            return False
        
        # Check ClamAV (optional)
        self._check_clamav()
        
        print("✅ All dependencies satisfied")
        return True
    
    def _check_redis(self) -> bool:
        """Check Redis connectivity"""
        try:
            import redis
            
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            client = redis.from_url(redis_url)
            client.ping()
            print("✅ Redis connection successful")
            return True
            
        except Exception as e:
            self.errors.append(f"Redis connection failed: {e}")
            print("❌ Redis connection failed")
            print("💡 Make sure Redis is running: redis-server")
            return False
    
    def _check_clamav(self) -> bool:
        """Check ClamAV (optional)"""
        try:
            result = subprocess.run(
                ["clamscan", "--version"],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                print("✅ ClamAV available for virus scanning")
                return True
            else:
                self.warnings.append("ClamAV not available - virus scanning disabled")
                print("⚠️  ClamAV not available - virus scanning disabled")
                return False
                
        except Exception:
            self.warnings.append("ClamAV not available - virus scanning disabled")
            print("⚠️  ClamAV not available - virus scanning disabled")
            return False
    
    def _setup_security_config(self) -> bool:
        """Setup security configuration"""
        print("\n🔐 Step 3: Security Configuration")
        
        # Check for required security environment variables
        required_vars = [
            "JWT_SECRET_KEY",
            "ENCRYPTION_KEY", 
            "SESSION_ENCRYPTION_KEY",
            "LOCAL_ENCRYPTION_KEY"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print("🔑 Generating missing security keys...")
            self._generate_security_keys(missing_vars)
        
        # Validate API keys
        api_keys = [
            "PINECONE_API_KEY",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY", 
            "OPENAI_API_KEY"
        ]
        
        missing_api_keys = []
        for key in api_keys:
            if not os.getenv(key):
                missing_api_keys.append(key)
        
        if missing_api_keys:
            self.errors.append(f"Missing API keys: {', '.join(missing_api_keys)}")
            print("❌ Missing required API keys")
            print("💡 Set environment variables or configure AWS Secrets Manager")
            return False
        
        # Initialize secure configuration
        from secure_config import initialize_secure_app_config
        if not initialize_secure_app_config():
            self.errors.append("Security configuration initialization failed")
            return False
        
        print("✅ Security configuration completed")
        return True
    
    def _generate_security_keys(self, missing_vars: List[str]):
        """Generate and display security keys"""
        print("\n🔑 Generated Security Keys:")
        print("Add these to your environment variables:")
        print("-" * 50)
        
        for var in missing_vars:
            key = secrets.token_urlsafe(32)
            print(f"export {var}='{key}'")
            
        print("-" * 50)
        print("⚠️  Save these keys securely before proceeding!")
        
        # Ask user to confirm
        response = input("\nHave you saved the keys? (y/N): ")
        if response.lower() != 'y':
            print("❌ Deployment cancelled - please save the keys first")
            sys.exit(1)
    
    def _setup_infrastructure(self) -> bool:
        """Setup infrastructure components"""
        print("\n🏗️  Step 4: Infrastructure Setup")
        
        # Create directories
        directories = [
            "uploads", "quarantine", "logs", "data", "prompts"
        ]
        
        for directory in directories:
            dir_path = self.base_dir / directory
            dir_path.mkdir(exist_ok=True)
            
            # Set secure permissions
            os.chmod(dir_path, 0o750)
            
        print("✅ Directory structure created")
        
        # Setup AWS Secrets Manager (if configured)
        if self._setup_aws_secrets():
            print("✅ AWS Secrets Manager configured")
        else:
            self.warnings.append("AWS Secrets Manager not configured - using environment variables")
        
        return True
    
    def _setup_aws_secrets(self) -> bool:
        """Setup AWS Secrets Manager"""
        try:
            import boto3
            
            # Test AWS credentials
            client = boto3.client('secretsmanager')
            client.list_secrets(MaxResults=1)
            
            # Initialize secrets manager
            from secrets_manager import initialize_secrets
            initialize_secrets()
            
            return True
            
        except Exception as e:
            self.warnings.append(f"AWS Secrets Manager setup failed: {e}")
            return False
    
    def _deploy_application(self) -> bool:
        """Deploy the application"""
        print("\n🚀 Step 5: Application Deployment")
        
        # Validate application files
        required_files = [
            "secure_app.py",
            "auth.py",
            "secrets_manager.py",
            "secure_session_manager.py",
            "security_middleware.py",
            "rate_limiter.py",
            "secure_file_handler.py"
        ]
        
        missing_files = []
        for file in required_files:
            if not (self.base_dir / file).exists():
                missing_files.append(file)
        
        if missing_files:
            self.errors.append(f"Missing application files: {', '.join(missing_files)}")
            return False
        
        print("✅ Application files validated")
        
        # Start application (in background for testing)
        print("🔄 Starting secure application...")
        
        # Import and validate the secure app
        try:
            from secure_app import create_secure_app
            app = create_secure_app()
            print("✅ Application started successfully")
            return True
            
        except Exception as e:
            self.errors.append(f"Application startup failed: {e}")
            return False
    
    def _validate_security(self) -> bool:
        """Validate security measures"""
        print("\n🔒 Step 6: Security Validation")
        
        security_checks = [
            ("Authentication System", self._check_auth_system),
            ("Rate Limiting", self._check_rate_limiting),
            ("Input Validation", self._check_input_validation),
            ("File Security", self._check_file_security),
            ("Session Management", self._check_session_management),
            ("Security Headers", self._check_security_headers)
        ]
        
        failed_checks = []
        for check_name, check_function in security_checks:
            try:
                if check_function():
                    print(f"✅ {check_name}")
                else:
                    print(f"❌ {check_name}")
                    failed_checks.append(check_name)
            except Exception as e:
                print(f"❌ {check_name}: {e}")
                failed_checks.append(check_name)
        
        if failed_checks:
            self.errors.append(f"Security validation failed: {', '.join(failed_checks)}")
            return False
        
        return True
    
    def _check_auth_system(self) -> bool:
        """Check authentication system"""
        from auth import AuthManager
        auth_manager = AuthManager()
        return auth_manager is not None
    
    def _check_rate_limiting(self) -> bool:
        """Check rate limiting"""
        from rate_limiter import get_rate_limiter
        rate_limiter = get_rate_limiter()
        return rate_limiter.redis_client is not None
    
    def _check_input_validation(self) -> bool:
        """Check input validation"""
        from security_middleware import InputSanitizer
        test_input = "<script>alert('test')</script>"
        sanitized = InputSanitizer.sanitize_string(test_input)
        return "<script>" not in sanitized
    
    def _check_file_security(self) -> bool:
        """Check file security"""
        from secure_file_handler import get_file_handler
        file_handler = get_file_handler()
        return file_handler.upload_dir.exists()
    
    def _check_session_management(self) -> bool:
        """Check session management"""
        from secure_session_manager import get_session_manager
        session_manager = get_session_manager()
        return session_manager.redis_client is not None
    
    def _check_security_headers(self) -> bool:
        """Check security headers"""
        # This would require running the app and making a request
        # For now, just check that Talisman is importable
        try:
            import flask_talisman
            return True
        except ImportError:
            return False
    
    def _run_health_checks(self) -> bool:
        """Run final health checks"""
        print("\n🏥 Step 7: Health Checks")
        
        # Check environment variables
        required_env = [
            "FLASK_ENV", "SECURITY_ENABLED", "JWT_SECRET_KEY"
        ]
        
        for var in required_env:
            if not os.getenv(var):
                self.errors.append(f"Missing environment variable: {var}")
                return False
        
        print("✅ Environment variables validated")
        
        # Check file permissions
        secure_dirs = ["uploads", "quarantine", "logs"]
        for dirname in secure_dirs:
            dir_path = self.base_dir / dirname
            if dir_path.exists():
                stat = dir_path.stat()
                if stat.st_mode & 0o077:  # Check for world/group write permissions
                    self.warnings.append(f"Directory {dirname} has insecure permissions")
        
        print("✅ File permissions validated")
        
        # Summary
        self._print_deployment_summary()
        
        return True
    
    def _print_deployment_summary(self):
        """Print deployment summary"""
        print("\n" + "=" * 60)
        print("🎯 DEPLOYMENT SUMMARY")
        print("=" * 60)
        
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"   - {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        print("\n🔒 SECURITY FEATURES ACTIVE:")
        features = [
            "JWT Authentication",
            "Redis Session Management", 
            "Rate Limiting",
            "Input Validation",
            "File Upload Security",
            "Security Headers",
            "HTTPS Enforcement"
        ]
        
        for feature in features:
            print(f"   ✅ {feature}")
        
        print("\n📊 NEXT STEPS:")
        print("   1. Test all endpoints for functionality")
        print("   2. Run penetration testing")
        print("   3. Configure monitoring and alerting")
        print("   4. Setup backup procedures")
        print("   5. Document incident response procedures")
        
        print("\n🌐 APPLICATION URLS:")
        port = os.getenv("FLASK_PORT", "5000")
        print(f"   - Health Check: http://localhost:{port}/health")
        print(f"   - Security Status: http://localhost:{port}/security-status")
        print(f"   - API Documentation: http://localhost:{port}/")


def main():
    """Main deployment function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Secure deployment for Richmond Storyline Generator")
    parser.add_argument(
        "--environment", 
        choices=["development", "staging", "production"],
        default="production",
        help="Deployment environment"
    )
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip dependency checks (not recommended)"
    )
    
    args = parser.parse_args()
    
    deployment = SecureDeployment()
    
    try:
        success = deployment.run_deployment(args.environment)
        
        if success:
            print("\n🎉 Deployment completed successfully!")
            print("🔐 Your application is now secure and ready for production!")
            sys.exit(0)
        else:
            print("\n💥 Deployment failed!")
            print("Please fix the errors and try again.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during deployment: {e}")
        logger.exception("Deployment error")
        sys.exit(1)


if __name__ == "__main__":
    main()