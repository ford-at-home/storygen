"""
Configuration management for Richmond Storyline Generator
Handles environment variables, paths, and application settings
"""
import os
import sys
from pathlib import Path


class Config:
    """Application configuration with environment variable support"""
    
    # Base paths
    BASE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BASE_DIR / "data"
    PROMPTS_DIR = BASE_DIR / "prompts"
    
    # Required environment variables
    REQUIRED_ENV_VARS = [
        "PINECONE_API_KEY",
        "AWS_ACCESS_KEY_ID", 
        "AWS_SECRET_ACCESS_KEY",
        "OPENAI_API_KEY"
    ]
    
    # Optional environment variables with defaults
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east1-gcp")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "richmond-context")
    
    # API settings
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    
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
    
    @classmethod
    def validate_environment(cls):
        """Validate that all required environment variables are set"""
        missing_vars = []
        
        for var in cls.REQUIRED_ENV_VARS:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print("❌ Missing required environment variables:")
            for var in missing_vars:
                print(f"   - {var}")
            print("\n💡 Please set these environment variables before running the application.")
            print("   You can use a .env file or export them in your shell:")
            print("   export PINECONE_API_KEY='your-key-here'")
            sys.exit(1)
            
        # Validate AWS region
        valid_regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
        if cls.AWS_REGION not in valid_regions:
            print(f"⚠️  Warning: AWS_REGION '{cls.AWS_REGION}' may not support all Bedrock models.")
            print(f"   Recommended regions: {', '.join(valid_regions)}")
    
    @classmethod
    def validate_paths(cls):
        """Validate that required directories exist"""
        # Create directories if they don't exist
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.PROMPTS_DIR.mkdir(exist_ok=True)
        
        # Check for prompt files
        story_prompt_path = cls.PROMPTS_DIR / "story_prompt.txt"
        if not story_prompt_path.exists():
            print(f"⚠️  Warning: Story prompt template not found at {story_prompt_path}")
            print("   Story generation may fail without this file.")
    
    @classmethod
    def initialize(cls):
        """Initialize configuration and validate environment"""
        cls.validate_environment()
        cls.validate_paths()
        
        print("✅ Configuration validated successfully!")
        print(f"   - Data directory: {cls.DATA_DIR}")
        print(f"   - Prompts directory: {cls.PROMPTS_DIR}")
        print(f"   - AWS Region: {cls.AWS_REGION}")
        print(f"   - Pinecone Index: {cls.PINECONE_INDEX_NAME}")
        
    @classmethod
    def get_env_example(cls):
        """Generate example .env content"""
        return """# Richmond Storyline Generator Environment Variables

# Required API Keys
PINECONE_API_KEY=your-pinecone-api-key
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
OPENAI_API_KEY=your-openai-api-key

# Optional Configuration
AWS_REGION=us-east-1
PINECONE_ENVIRONMENT=us-east1-gcp
PINECONE_INDEX_NAME=richmond-context

# Flask Settings
FLASK_PORT=5000
FLASK_DEBUG=true

# Model Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
DEFAULT_TEMPERATURE=0.7

# Token Limits
SHORT_POST_TOKENS=1024
LONG_POST_TOKENS=2048
BLOG_POST_TOKENS=4096

# Document Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=100
"""


# Create a convenience instance
config = Config()