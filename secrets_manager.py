"""
Secure Secrets Management for Richmond Storyline Generator
Handles AWS Secrets Manager integration and secure credential storage
"""

import os
import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)


class SecretsManager:
    """Manages application secrets securely using AWS Secrets Manager"""
    
    def __init__(self, region_name: str = "us-east-1"):
        self.region_name = region_name
        self.secrets_client = None
        self.local_cache = {}
        self.encryption_key = None
        
        # Initialize AWS Secrets Manager client
        self._init_aws_client()
        
        # Initialize local encryption for fallback
        self._init_local_encryption()
    
    def _init_aws_client(self):
        """Initialize AWS Secrets Manager client"""
        try:
            self.secrets_client = boto3.client(
                'secretsmanager',
                region_name=self.region_name
            )
            # Test connection
            self.secrets_client.list_secrets(MaxResults=1)
            logger.info("✅ AWS Secrets Manager connected successfully")
        except NoCredentialsError:
            logger.warning("⚠️  AWS credentials not found. Using local encryption fallback.")
            self.secrets_client = None
        except Exception as e:
            logger.error(f"❌ AWS Secrets Manager connection failed: {e}")
            self.secrets_client = None
    
    def _init_local_encryption(self):
        """Initialize local encryption for fallback secret storage"""
        encryption_key = os.getenv('LOCAL_ENCRYPTION_KEY')
        if not encryption_key:
            encryption_key = Fernet.generate_key()
            logger.warning(f"⚠️  Generated new local encryption key: {encryption_key.decode()}")
            logger.warning("   Please set LOCAL_ENCRYPTION_KEY environment variable for production")
        else:
            encryption_key = encryption_key.encode()
        
        self.encryption_key = Fernet(encryption_key)
    
    def get_secret(self, secret_name: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Retrieve secret from AWS Secrets Manager or local fallback
        
        Args:
            secret_name: Name of the secret to retrieve
            use_cache: Whether to use cached value if available
            
        Returns:
            Dict containing secret key-value pairs or None if not found
        """
        # Check cache first
        if use_cache and secret_name in self.local_cache:
            return self.local_cache[secret_name]
        
        # Try AWS Secrets Manager first
        if self.secrets_client:
            try:
                response = self.secrets_client.get_secret_value(SecretId=secret_name)
                secret_data = json.loads(response['SecretString'])
                
                # Cache the result
                self.local_cache[secret_name] = secret_data
                logger.info(f"✅ Retrieved secret '{secret_name}' from AWS Secrets Manager")
                return secret_data
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ResourceNotFoundException':
                    logger.warning(f"⚠️  Secret '{secret_name}' not found in AWS Secrets Manager")
                else:
                    logger.error(f"❌ Error retrieving secret '{secret_name}': {e}")
            except Exception as e:
                logger.error(f"❌ Unexpected error retrieving secret '{secret_name}': {e}")
        
        # Fallback to local encrypted storage
        return self._get_local_secret(secret_name)
    
    def set_secret(self, secret_name: str, secret_value: Dict[str, Any]) -> bool:
        """
        Store secret in AWS Secrets Manager or local fallback
        
        Args:
            secret_name: Name of the secret
            secret_value: Dict containing secret key-value pairs
            
        Returns:
            True if successful, False otherwise
        """
        # Try AWS Secrets Manager first
        if self.secrets_client:
            try:
                secret_string = json.dumps(secret_value)
                
                # Try to update existing secret
                try:
                    self.secrets_client.update_secret(
                        SecretId=secret_name,
                        SecretString=secret_string
                    )
                    logger.info(f"✅ Updated secret '{secret_name}' in AWS Secrets Manager")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        # Create new secret
                        self.secrets_client.create_secret(
                            Name=secret_name,
                            SecretString=secret_string,
                            Description=f"Secret for Richmond Storyline Generator - {secret_name}"
                        )
                        logger.info(f"✅ Created secret '{secret_name}' in AWS Secrets Manager")
                    else:
                        raise
                
                # Cache the result
                self.local_cache[secret_name] = secret_value
                return True
                
            except Exception as e:
                logger.error(f"❌ Error storing secret '{secret_name}': {e}")
        
        # Fallback to local encrypted storage
        return self._set_local_secret(secret_name, secret_value)
    
    def _get_local_secret(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """Get secret from local encrypted storage"""
        try:
            env_var = f"LOCAL_SECRET_{secret_name.upper()}"
            encrypted_data = os.getenv(env_var)
            
            if encrypted_data:
                decrypted_data = self.encryption_key.decrypt(encrypted_data.encode())
                secret_data = json.loads(decrypted_data.decode())
                
                # Cache the result
                self.local_cache[secret_name] = secret_data
                logger.info(f"✅ Retrieved secret '{secret_name}' from local storage")
                return secret_data
            
        except Exception as e:
            logger.error(f"❌ Error retrieving local secret '{secret_name}': {e}")
        
        return None
    
    def _set_local_secret(self, secret_name: str, secret_value: Dict[str, Any]) -> bool:
        """Set secret in local encrypted storage"""
        try:
            secret_string = json.dumps(secret_value)
            encrypted_data = self.encryption_key.encrypt(secret_string.encode())
            
            env_var = f"LOCAL_SECRET_{secret_name.upper()}"
            logger.warning(f"⚠️  Store this encrypted secret as environment variable {env_var}:")
            logger.warning(f"   {encrypted_data.decode()}")
            
            # Cache the result
            self.local_cache[secret_name] = secret_value
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing local secret '{secret_name}': {e}")
            return False
    
    def get_database_credentials(self) -> Dict[str, str]:
        """Get database connection credentials"""
        credentials = self.get_secret("storygen-database")
        if not credentials:
            # Fallback to environment variables
            credentials = {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": os.getenv("DB_PORT", "5432"),
                "database": os.getenv("DB_NAME", "storygen"),
                "username": os.getenv("DB_USER", "storygen"),
                "password": os.getenv("DB_PASSWORD", "")
            }
        return credentials
    
    def get_api_keys(self) -> Dict[str, str]:
        """Get API keys for external services"""
        api_keys = self.get_secret("storygen-api-keys")
        if not api_keys:
            # Fallback to environment variables
            api_keys = {
                "pinecone_api_key": os.getenv("PINECONE_API_KEY", ""),
                "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
                "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", ""),
                "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "")
            }
        return api_keys
    
    def get_jwt_secret(self) -> str:
        """Get JWT secret key"""
        jwt_config = self.get_secret("storygen-jwt")
        if jwt_config and "secret_key" in jwt_config:
            return jwt_config["secret_key"]
        
        # Fallback to environment variable or generate new one
        jwt_secret = os.getenv("JWT_SECRET_KEY")
        if not jwt_secret:
            jwt_secret = Fernet.generate_key().decode()
            logger.warning(f"⚠️  Generated new JWT secret. Please store securely: {jwt_secret}")
        
        return jwt_secret
    
    def rotate_secrets(self) -> bool:
        """Rotate all application secrets"""
        try:
            # Generate new JWT secret
            new_jwt_secret = Fernet.generate_key().decode()
            jwt_config = {"secret_key": new_jwt_secret}
            
            if self.set_secret("storygen-jwt", jwt_config):
                logger.info("✅ JWT secret rotated successfully")
                return True
            else:
                logger.error("❌ Failed to rotate JWT secret")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error rotating secrets: {e}")
            return False
    
    def validate_secrets(self) -> Dict[str, bool]:
        """Validate that all required secrets are available"""
        validation_results = {}
        
        # Check API keys
        api_keys = self.get_api_keys()
        validation_results["pinecone_api_key"] = bool(api_keys.get("pinecone_api_key"))
        validation_results["openai_api_key"] = bool(api_keys.get("openai_api_key"))
        validation_results["aws_credentials"] = bool(
            api_keys.get("aws_access_key_id") and api_keys.get("aws_secret_access_key")
        )
        
        # Check JWT secret
        validation_results["jwt_secret"] = bool(self.get_jwt_secret())
        
        # Check database credentials
        db_creds = self.get_database_credentials()
        validation_results["database_credentials"] = bool(
            db_creds.get("host") and db_creds.get("username")
        )
        
        return validation_results
    
    def setup_initial_secrets(self) -> bool:
        """Set up initial secrets from environment variables"""
        try:
            # API Keys
            api_keys = {
                "pinecone_api_key": os.getenv("PINECONE_API_KEY", ""),
                "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
                "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", ""),
                "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "")
            }
            
            # JWT Configuration
            jwt_config = {
                "secret_key": os.getenv("JWT_SECRET_KEY", Fernet.generate_key().decode())
            }
            
            # Database Credentials
            db_credentials = {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": os.getenv("DB_PORT", "5432"),
                "database": os.getenv("DB_NAME", "storygen"),
                "username": os.getenv("DB_USER", "storygen"),
                "password": os.getenv("DB_PASSWORD", "")
            }
            
            # Store secrets
            success = True
            success &= self.set_secret("storygen-api-keys", api_keys)
            success &= self.set_secret("storygen-jwt", jwt_config)
            success &= self.set_secret("storygen-database", db_credentials)
            
            if success:
                logger.info("✅ Initial secrets setup completed successfully")
            else:
                logger.error("❌ Some secrets failed to be stored")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error setting up initial secrets: {e}")
            return False


# Global secrets manager instance
secrets_manager = SecretsManager()


def get_secure_config() -> Dict[str, Any]:
    """Get secure configuration for the application"""
    api_keys = secrets_manager.get_api_keys()
    jwt_secret = secrets_manager.get_jwt_secret()
    db_creds = secrets_manager.get_database_credentials()
    
    return {
        "api_keys": api_keys,
        "jwt_secret": jwt_secret,
        "database": db_creds
    }


def initialize_secrets():
    """Initialize secrets management"""
    logger.info("🔐 Initializing secrets management...")
    
    # Validate current secrets
    validation_results = secrets_manager.validate_secrets()
    
    missing_secrets = [key for key, valid in validation_results.items() if not valid]
    
    if missing_secrets:
        logger.warning(f"⚠️  Missing secrets: {', '.join(missing_secrets)}")
        logger.info("🔧 Setting up initial secrets from environment variables...")
        
        if secrets_manager.setup_initial_secrets():
            logger.info("✅ Secrets initialization completed")
        else:
            logger.error("❌ Failed to initialize some secrets")
    else:
        logger.info("✅ All required secrets are available")
    
    return secrets_manager