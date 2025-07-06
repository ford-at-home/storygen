#!/usr/bin/env python3
"""
Development setup script for Richmond Storyline Generator
Helps developers quickly set up their environment
"""
import os
import sys
import subprocess
from pathlib import Path
import shutil

# ANSI color codes for pretty output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")

def print_success(text):
    """Print success message"""
    print(f"{GREEN}✅ {text}{RESET}")

def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_error(text):
    """Print error message"""
    print(f"{RED}❌ {text}{RESET}")

def check_python_version():
    """Check if Python version is 3.11 or higher"""
    print("Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print_error(f"Python 3.11+ required, but you have {version.major}.{version.minor}")
        sys.exit(1)
    print_success(f"Python {version.major}.{version.minor} detected")

def create_directories():
    """Create required directories"""
    print("\nCreating directories...")
    dirs = ['data', 'logs', 'prompts', 'bedrock', 'pinecone', 'ingestion']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print_success(f"Created {dir_name}/")

def check_env_file():
    """Check for .env file and create from example if needed"""
    print("\nChecking environment configuration...")
    if not Path('.env').exists():
        if Path('.env.example').exists():
            shutil.copy('.env.example', '.env')
            print_success("Created .env from .env.example")
            print_warning("Please edit .env with your API keys!")
            return False
        else:
            print_error("No .env or .env.example file found!")
            return False
    else:
        print_success(".env file exists")
        return True

def install_dependencies():
    """Install Python dependencies"""
    print("\nInstalling dependencies...")
    
    # Check if uv is available
    if shutil.which('uv'):
        print("Using uv for dependency installation...")
        subprocess.run(['uv', 'pip', 'install', '-r', 'requirements.txt'], check=True)
    else:
        print("Using pip for dependency installation...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
    
    print_success("Dependencies installed")

def validate_aws_credentials():
    """Check if AWS credentials are configured"""
    print("\nValidating AWS credentials...")
    try:
        import boto3
        # Try to create a client to validate credentials
        client = boto3.client('sts')
        client.get_caller_identity()
        print_success("AWS credentials validated")
        return True
    except Exception as e:
        print_warning("AWS credentials not configured or invalid")
        print("   Run: aws configure")
        return False

def validate_pinecone_connection():
    """Check if Pinecone API key is valid"""
    print("\nValidating Pinecone connection...")
    try:
        import pinecone
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        api_key = os.getenv('PINECONE_API_KEY')
        
        if not api_key:
            print_warning("PINECONE_API_KEY not set in .env")
            return False
            
        pinecone.init(api_key=api_key, environment='us-east1-gcp')
        print_success("Pinecone connection validated")
        return True
    except Exception as e:
        print_warning(f"Pinecone connection failed: {str(e)}")
        return False

def check_data_files():
    """Check if Richmond data files exist"""
    print("\nChecking data files...")
    expected_files = [
        'richmond_quotes.md',
        'richmond_culture.md', 
        'richmond_economy.md',
        'richmond_stories.md',
        'richmond_news.md'
    ]
    
    data_dir = Path('data')
    missing_files = []
    
    for file_name in expected_files:
        if (data_dir / file_name).exists():
            print_success(f"Found {file_name}")
        else:
            missing_files.append(file_name)
            print_error(f"Missing {file_name}")
    
    return len(missing_files) == 0

def run_tests():
    """Run basic tests to ensure setup is correct"""
    print("\nRunning basic tests...")
    
    # Test imports
    try:
        import flask
        import boto3
        import pinecone
        import langchain
        import jinja2
        print_success("All required packages can be imported")
    except ImportError as e:
        print_error(f"Import error: {str(e)}")
        return False
    
    # Test configuration
    try:
        from config import config
        config.validate_paths()
        print_success("Configuration validated")
    except Exception as e:
        print_error(f"Configuration error: {str(e)}")
        return False
    
    return True

def main():
    """Main setup function"""
    print_header("Richmond Storyline Generator Setup")
    
    # Track setup status
    all_good = True
    
    # Run setup steps
    check_python_version()
    create_directories()
    
    env_exists = check_env_file()
    if not env_exists:
        all_good = False
    
    try:
        install_dependencies()
    except subprocess.CalledProcessError:
        print_error("Failed to install dependencies")
        all_good = False
    
    # Import dotenv after installation
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print_warning("python-dotenv not installed, skipping .env loading")
    
    # Validation steps
    aws_valid = validate_aws_credentials()
    pinecone_valid = validate_pinecone_connection()
    data_exists = check_data_files()
    tests_pass = run_tests()
    
    # Summary
    print_header("Setup Summary")
    
    if all_good and aws_valid and pinecone_valid and data_exists and tests_pass:
        print_success("Setup completed successfully! 🎉")
        print("\nNext steps:")
        print("1. Run the document ingestion: python ingestion/ingest_docs.py")
        print("2. Start the API server: python app.py")
        print("3. Test the API: curl -X POST http://localhost:5000/generate-story -H 'Content-Type: application/json' -d '{\"core_idea\": \"test\"}'")
    else:
        print_warning("Setup completed with warnings")
        print("\nPlease address the following issues:")
        if not env_exists:
            print("- Edit .env file with your API keys")
        if not aws_valid:
            print("- Configure AWS credentials")
        if not pinecone_valid:
            print("- Add valid PINECONE_API_KEY to .env")
        if not data_exists:
            print("- Ensure all Richmond data files are in data/")
        if not tests_pass:
            print("- Fix the configuration or import errors")

if __name__ == "__main__":
    main()