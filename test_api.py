#!/usr/bin/env python3
"""
Test script for Richmond Storyline Generator API
Tests all endpoints and validates functionality
"""
import requests
import json
import time
import sys

# Base URL for the API
BASE_URL = "http://localhost:5000"

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test(name):
    print(f"\n{BLUE}Testing: {name}{RESET}")

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_response(response):
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")

def test_health():
    """Test health check endpoint"""
    print_test("Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print_success("Health check passed")
                return True
        print_error("Health check failed")
        print_response(response)
        return False
    except Exception as e:
        print_error(f"Connection failed: {str(e)}")
        return False

def test_root():
    """Test root endpoint"""
    print_test("Root Documentation")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            if "service" in data and "endpoints" in data:
                print_success("Root documentation available")
                return True
        print_error("Root documentation failed")
        print_response(response)
        return False
    except Exception as e:
        print_error(f"Request failed: {str(e)}")
        return False

def test_styles():
    """Test styles endpoint"""
    print_test("Story Styles")
    try:
        response = requests.get(f"{BASE_URL}/styles")
        if response.status_code == 200:
            data = response.json()
            if "styles" in data and len(data["styles"]) == 3:
                print_success("Styles endpoint working")
                for style in data["styles"]:
                    print(f"  - {style['name']}: {style['description']}")
                return True
        print_error("Styles endpoint failed")
        print_response(response)
        return False
    except Exception as e:
        print_error(f"Request failed: {str(e)}")
        return False

def test_generate_story(core_idea, style="short_post"):
    """Test story generation"""
    print_test(f"Story Generation ({style})")
    try:
        payload = {
            "core_idea": core_idea,
            "style": style
        }
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{BASE_URL}/generate-story",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            if "story" in data:
                print_success("Story generated successfully")
                print(f"\nStory preview: {data['story'][:200]}...")
                if "metadata" in data:
                    print(f"\nMetadata: {json.dumps(data['metadata'], indent=2)}")
                return True
        
        print_error(f"Story generation failed (Status: {response.status_code})")
        print_response(response)
        return False
    except Exception as e:
        print_error(f"Request failed: {str(e)}")
        return False

def test_validation_errors():
    """Test validation error handling"""
    print_test("Validation Error Handling")
    
    # Test missing core_idea
    try:
        response = requests.post(
            f"{BASE_URL}/generate-story",
            json={},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 400:
            print_success("Missing core_idea validation works")
        else:
            print_error("Missing core_idea should return 400")
            print_response(response)
    except Exception as e:
        print_error(f"Request failed: {str(e)}")
    
    # Test short core_idea
    try:
        response = requests.post(
            f"{BASE_URL}/generate-story",
            json={"core_idea": "test"},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 400:
            print_success("Short core_idea validation works")
        else:
            print_error("Short core_idea should return 400")
            print_response(response)
    except Exception as e:
        print_error(f"Request failed: {str(e)}")
    
    # Test invalid style
    try:
        response = requests.post(
            f"{BASE_URL}/generate-story",
            json={"core_idea": "Richmond tech scene is growing", "style": "invalid_style"},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 400:
            print_success("Invalid style validation works")
        else:
            print_error("Invalid style should return 400")
            print_response(response)
    except Exception as e:
        print_error(f"Request failed: {str(e)}")

def test_stats():
    """Test stats endpoint"""
    print_test("API Statistics")
    try:
        response = requests.get(f"{BASE_URL}/stats")
        if response.status_code == 200:
            data = response.json()
            print_success("Stats endpoint working")
            print(f"Stats: {json.dumps(data, indent=2)}")
            return True
        print_error("Stats endpoint failed")
        print_response(response)
        return False
    except Exception as e:
        print_error(f"Request failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print(f"{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}Richmond Storyline Generator API Tests{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")
    
    # Check if API is running
    if not test_health():
        print(f"\n{RED}API is not running! Start it with: python app.py{RESET}")
        sys.exit(1)
    
    # Run tests
    test_root()
    test_styles()
    test_validation_errors()
    
    # Test story generation with different styles
    test_ideas = [
        "Richmond tech professionals are returning from coastal cities to build innovative startups",
        "The transformation of Scott's Addition from industrial district to innovation hub",
        "How Richmond's food scene reflects its diverse community and creative spirit"
    ]
    
    styles = ["short_post", "long_post", "blog_post"]
    
    # Test one story per style
    for i, style in enumerate(styles):
        if i < len(test_ideas):
            test_generate_story(test_ideas[i], style)
            time.sleep(1)  # Brief pause between requests
    
    # Check final stats
    test_stats()
    
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}Tests Complete!{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}")

if __name__ == "__main__":
    main()