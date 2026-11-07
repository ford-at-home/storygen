#!/usr/bin/env python3
"""
Test script for Richmond Storyline Generator Conversational API
Tests the multi-turn conversation flow
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

def print_header(text):
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg):
    print(f"{YELLOW}→ {msg}{RESET}")

def test_conversation_flow():
    """Test a complete conversation flow"""
    print_header("Testing Complete Conversation Flow")
    
    # Step 1: Start conversation
    print_info("Starting new conversation...")
    start_response = requests.post(
        f"{BASE_URL}/conversation/start",
        json={
            "initial_idea": "I'm a software developer who moved back to Richmond from San Francisco to help build the local tech community",
            "user_id": "test_user_123"
        }
    )
    
    if start_response.status_code != 200:
        print_error(f"Failed to start conversation: {start_response.status_code}")
        print(start_response.text)
        return
    
    data = start_response.json()
    session_id = data['session_id']
    print_success(f"Conversation started - Session ID: {session_id}")
    print(f"Stage: {data['current_stage']}")
    print(f"Response: {data['response'][:200]}...")
    print(f"Progress: {data['metadata']['conversation_progress']}")
    
    # Step 2: Continue with follow-up
    print_info("\nProviding follow-up response...")
    time.sleep(1)  # Brief pause
    
    continue_response = requests.post(
        f"{BASE_URL}/conversation/continue",
        json={
            "session_id": session_id,
            "user_response": "I realized that Richmond has all the ingredients for a thriving tech scene - talented people, affordable living, and a collaborative spirit. I wanted to be part of building something meaningful here rather than just being another cog in the Silicon Valley machine."
        }
    )
    
    if continue_response.status_code != 200:
        print_error(f"Failed to continue conversation: {continue_response.status_code}")
        print(continue_response.text)
        return
    
    data = continue_response.json()
    print_success("Follow-up processed")
    print(f"Stage: {data['current_stage']}")
    print(f"Response: {data['response'][:200]}...")
    print(f"Progress: {data['metadata']['conversation_progress']}")
    
    # Step 3: Provide personal anecdote
    print_info("\nProviding personal anecdote...")
    time.sleep(1)
    
    anecdote_response = requests.post(
        f"{BASE_URL}/conversation/continue",
        json={
            "session_id": session_id,
            "user_response": "Last month, I organized a hackathon at a local brewery in Scott's Addition. Seeing developers, designers, and entrepreneurs collaborating over craft beer, building solutions for local nonprofits - that's when I knew I made the right choice. One team even created an app to help Richmond food banks coordinate deliveries."
        }
    )
    
    if anecdote_response.status_code != 200:
        print_error(f"Failed to submit anecdote: {anecdote_response.status_code}")
        print(anecdote_response.text)
        return
    
    data = anecdote_response.json()
    print_success("Personal anecdote processed")
    print(f"Stage: {data['current_stage']}")
    
    # Check if we have options to select
    if data.get('options'):
        print_info("\nHooks generated:")
        for i, option in enumerate(data['options']):
            print(f"{i+1}. {option[:100]}...")
        
        # Step 4: Select a hook
        print_info("\nSelecting hook #1...")
        time.sleep(1)
        
        select_response = requests.post(
            f"{BASE_URL}/conversation/select-option",
            json={
                "session_id": session_id,
                "selection_type": "hook",
                "selected_index": 0
            }
        )
        
        if select_response.status_code != 200:
            print_error(f"Failed to select hook: {select_response.status_code}")
            print(select_response.text)
            return
        
        data = select_response.json()
        print_success("Hook selected")
        print(f"Selected: {data['selected'][:100]}...")
    
    # Continue to get CTAs
    print_info("\nContinuing to CTA generation...")
    time.sleep(1)
    
    # The arc development should return CTA options
    if 'response' in data and 'options' not in data:
        # Need another continue call to get CTAs
        cta_response = requests.post(
            f"{BASE_URL}/conversation/continue",
            json={
                "session_id": session_id,
                "user_response": "Continue"
            }
        )
        
        if cta_response.status_code == 200:
            data = cta_response.json()
    
    # If we have CTA options
    if data.get('options'):
        print_info("\nCTAs generated:")
        for i, option in enumerate(data['options']):
            print(f"{i+1}. {option[:100]}...")
        
        # Step 5: Select a CTA
        print_info("\nSelecting CTA #2...")
        time.sleep(1)
        
        select_cta_response = requests.post(
            f"{BASE_URL}/conversation/select-option",
            json={
                "session_id": session_id,
                "selection_type": "cta",
                "selected_index": 1
            }
        )
        
        if select_cta_response.status_code != 200:
            print_error(f"Failed to select CTA: {select_cta_response.status_code}")
            print(select_cta_response.text)
            return
        
        print_success("CTA selected")
    
    # Step 6: Generate final story
    print_info("\nGenerating final story...")
    time.sleep(1)
    
    final_response = requests.post(
        f"{BASE_URL}/conversation/generate-final",
        json={
            "session_id": session_id,
            "style": "long_post"
        }
    )
    
    if final_response.status_code != 200:
        print_error(f"Failed to generate final story: {final_response.status_code}")
        print(final_response.text)
        return
    
    data = final_response.json()
    print_success("Final story generated!")
    print(f"\nStory preview: {data['story'][:500]}...")
    print(f"\nMetadata:")
    print(f"- Duration: {data['metadata']['conversation_duration']:.1f}s")
    print(f"- Total turns: {data['metadata']['total_turns']}")
    print(f"- Core idea: {data['metadata']['story_elements']['core_idea'][:100]}...")
    
    # Step 7: Check session details
    print_info("\nChecking session details...")
    session_response = requests.get(f"{BASE_URL}/conversation/session/{session_id}")
    
    if session_response.status_code == 200:
        session_data = session_response.json()
        print_success("Session retrieved")
        print(f"Status: {session_data['status']}")
        print(f"Turns: {len(session_data['conversation_history'])}")
        print(f"Story elements completed: {sum(1 for v in session_data['story_elements'].values() if v)}/5")

def test_session_management():
    """Test session management endpoints"""
    print_header("Testing Session Management")
    
    # Create a test session
    start_response = requests.post(
        f"{BASE_URL}/conversation/start",
        json={"initial_idea": "Test session for management features"}
    )
    
    if start_response.status_code != 200:
        print_error("Failed to create test session")
        return
    
    session_id = start_response.json()['session_id']
    print_success(f"Created test session: {session_id}")
    
    # Test session export
    print_info("\nTesting session export...")
    export_response = requests.get(f"{BASE_URL}/conversation/session/{session_id}/export")
    
    if export_response.status_code == 200:
        export_data = export_response.json()
        print_success("Session exported successfully")
        print(f"Export contains {len(json.dumps(export_data['export']))} characters")
    
    # Test active sessions
    print_info("\nTesting active sessions list...")
    active_response = requests.get(f"{BASE_URL}/conversation/sessions/active")
    
    if active_response.status_code == 200:
        active_data = active_response.json()
        print_success(f"Found {active_data['total']} active sessions")
        for session in active_data['active_sessions'][:3]:  # Show first 3
            print(f"  - {session['session_id']}: Stage {session['current_stage']}, {session['turns']} turns")

def test_error_handling():
    """Test error handling in conversation API"""
    print_header("Testing Error Handling")
    
    # Test invalid session ID
    print_info("Testing invalid session ID...")
    response = requests.post(
        f"{BASE_URL}/conversation/continue",
        json={
            "session_id": "invalid-session-id",
            "user_response": "This should fail"
        }
    )
    
    if response.status_code == 404:
        print_success("Invalid session properly rejected")
    else:
        print_error(f"Expected 404, got {response.status_code}")
    
    # Test missing required fields
    print_info("\nTesting missing required fields...")
    response = requests.post(
        f"{BASE_URL}/conversation/start",
        json={}
    )
    
    if response.status_code == 400:
        print_success("Missing fields properly rejected")
    else:
        print_error(f"Expected 400, got {response.status_code}")
    
    # Test short initial idea
    print_info("\nTesting short initial idea...")
    response = requests.post(
        f"{BASE_URL}/conversation/start",
        json={"initial_idea": "Too short"}
    )
    
    if response.status_code == 400:
        print_success("Short idea properly rejected")
    else:
        print_error(f"Expected 400, got {response.status_code}")

def main():
    """Run all conversation tests"""
    print_header("Richmond Storyline Generator - Conversation API Tests")
    
    # Check if API is running
    try:
        health_response = requests.get(f"{BASE_URL}/health")
        if health_response.status_code != 200:
            print_error("API is not running! Start it with: python app.py")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API! Start it with: python app.py")
        sys.exit(1)
    
    print_success("API is running")
    
    # Run tests
    try:
        test_error_handling()
        test_session_management()
        test_conversation_flow()
        
        print_header("All Tests Complete!")
        print_success("Conversational API is working correctly")
        
    except Exception as e:
        print_error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()