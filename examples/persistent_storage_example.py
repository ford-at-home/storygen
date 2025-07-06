"""
Example of using the persistent data layer
Shows how to integrate DynamoDB, caching, and analytics
"""
import asyncio
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from data import (
    init_data_layer, save_user, save_session, save_story,
    get_user, get_session, get_story,
    track_event, get_analytics_dashboard,
    User, Story, UserRole, StoryStyle, StoryStatus
)
from session_manager_persistent import SessionFactory, persistent_session_store


async def example_user_flow():
    """Example of complete user flow with persistence"""
    
    print("=== Richmond StoryGen Persistent Storage Example ===\n")
    
    # Initialize data layer
    print("1. Initializing data layer...")
    await init_data_layer(
        create_tables=True,
        warm_cache=True,
        enable_backups=False  # Disable for example
    )
    print("✅ Data layer initialized\n")
    
    # Create a user
    print("2. Creating user...")
    user = User(
        email="sarah@richmondtech.com",
        username="sarah_rva",
        role=UserRole.REGISTERED
    )
    user.profile["full_name"] = "Sarah Richmond"
    user.profile["bio"] = "Tech entrepreneur returning to RVA"
    user.profile["interests"] = ["startups", "community", "innovation"]
    
    success = await save_user(user)
    print(f"✅ User created: {user.user_id}\n")
    
    # Track user signup
    track_event(
        "user_signup",
        user_id=user.user_id,
        properties={"source": "example"}
    )
    
    # Create a session
    print("3. Creating session...")
    session = await SessionFactory.create_session(
        user_id=user.user_id,
        initial_idea="Richmond's growing tech scene attracts talent from major cities"
    )
    print(f"✅ Session created: {session.session_id}\n")
    
    # Simulate conversation
    print("4. Simulating conversation...")
    
    # Add conversation turns
    session.add_turn(
        stage="kickoff",
        user_input="I want to tell the story of Richmond's tech renaissance",
        llm_response="That's a compelling topic! Richmond's tech scene has transformed dramatically. What specific aspect interests you most?"
    )
    
    session.add_turn(
        stage="depth_analysis",
        user_input="The return of tech professionals from Silicon Valley and NYC",
        llm_response="The 'boomerang' effect is fascinating. Many are drawn back by Richmond's quality of life and growing opportunities."
    )
    
    session.story_elements.personal_anecdote = "After 5 years in San Francisco, I returned to Richmond and found a thriving startup ecosystem"
    session.story_elements.selected_hook = "What if the next tech hub isn't on the coast?"
    session.story_elements.richmond_quote = "Richmond is no longer just a government town - it's a tech town with soul"
    
    # Save session updates
    await persistent_session_store.save(session)
    print("✅ Conversation simulated\n")
    
    # Generate story
    print("5. Creating story...")
    story = Story(
        user_id=user.user_id,
        session_id=session.session_id,
        title="Richmond's Tech Renaissance: The Great Return",
        content="""
What if the next tech hub isn't on the coast?

After five years building products in Silicon Valley, I found myself 
questioning the endless commutes, astronomical rents, and the paradoxical 
isolation of being surrounded by millions. The breaking point came during 
another 90-minute commute, stuck on the 101, when I realized I was spending 
more time in traffic than with my family.

That's when Richmond called me home.

What I discovered upon returning wasn't the sleepy government town I'd left 
behind. Richmond had transformed. The city's tech scene was buzzing with 
energy, but it was different from the Valley's cutthroat culture. Here, 
entrepreneurs actually helped each other. Coffee meetings happened at 
locally-owned shops, not corporate chains. And the best part? I could 
afford to live downtown and bike to work.

"Richmond is no longer just a government town - it's a tech town with soul," 
as one local founder put it. The data backs this up: tech employment has 
grown 42% in the past five years, with over 200 startups now calling RVA home.

The city offers something the coastal hubs can't: authentic community. 
Whether it's the monthly RVA Tech meetups at local breweries or the 
collaborative workspace at 1717 Innovation Center, there's a genuine desire 
to see everyone succeed.

For those considering the move, know this: Richmond doesn't ask you to 
sacrifice your ambition. It asks you to blend it with actual living. 
Here, you can build the next big thing and still make it home for dinner.

Ready to write your own Richmond story? The city is waiting, and trust me, 
the timing has never been better.
        """.strip(),
        style=StoryStyle.BLOG_POST
    )
    
    # Set story elements
    story.elements = {
        "core_idea": session.story_elements.core_idea,
        "hook": session.story_elements.selected_hook,
        "personal_anecdote": session.story_elements.personal_anecdote,
        "richmond_quote": session.story_elements.richmond_quote,
        "tags": ["tech", "richmond", "startups", "community"],
        "themes": ["innovation", "community", "quality-of-life"]
    }
    
    # Calculate metrics
    story.metrics["word_count"] = len(story.content.split())
    story.metrics["reading_time_minutes"] = round(story.metrics["word_count"] / 200, 1)
    story.generation_details["generation_time_seconds"] = 3.5
    
    # Save story
    success = await save_story(story)
    print(f"✅ Story created: {story.story_id}\n")
    
    # Complete session
    session.story_elements.final_story = story.content
    session.complete()
    await persistent_session_store.save(session)
    
    # Demonstrate retrieval
    print("6. Testing retrieval...")
    
    # Get user from cache/db
    retrieved_user = get_user(user.user_id)
    print(f"✅ Retrieved user: {retrieved_user.username}")
    
    # Get session
    retrieved_session = get_session(session.session_id)
    print(f"✅ Retrieved session: {retrieved_session.status.value}")
    
    # Get story
    retrieved_story = get_story(story.story_id)
    print(f"✅ Retrieved story: {retrieved_story.title[:30]}...\n")
    
    # Show analytics
    print("7. Analytics Dashboard...")
    dashboard = get_analytics_dashboard("1h")
    
    print(f"Overview:")
    print(f"  - Total events: {dashboard['overview']['total_events']}")
    print(f"  - Unique users: {dashboard['overview']['unique_users']}")
    print(f"  - Event categories: {dashboard['overview']['event_categories']}")
    
    # Get session stats
    print("\n8. Session Statistics...")
    stats = persistent_session_store.get_session_stats()
    print(f"  - L1 cache size: {stats['l1_cache_size']}")
    print(f"  - Active sessions: {stats['active_sessions']}")
    print(f"  - Storage backend: {stats['storage_backend']}")
    
    print("\n✅ Example completed successfully!")
    print("\nKey Takeaways:")
    print("- All data is now persistently stored in DynamoDB")
    print("- Multi-layer caching provides fast access")
    print("- Analytics are automatically tracked")
    print("- Sessions expire and are cleaned up automatically")
    print("- Data is validated before storage")
    print("- Backups can be scheduled for disaster recovery")


async def cleanup_example():
    """Cleanup example data"""
    print("\nCleaning up example data...")
    # In production, you would implement proper cleanup
    # For now, data will be cleaned up by TTL
    print("✅ Cleanup scheduled via TTL")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_user_flow())
    
    # Optional cleanup
    # asyncio.run(cleanup_example())