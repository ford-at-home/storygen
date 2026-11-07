#!/usr/bin/env python3
"""
Test script to evaluate story generation quality
Compares original vs enhanced prompts
"""
import requests
import json
import time
from datetime import datetime

# Base URL for the API
BASE_URL = "http://localhost:5000"

# Test stories to generate
TEST_IDEAS = [
    {
        "core_idea": "A Richmond coffee shop owner discovers that bringing people together over locally roasted beans can spark innovation and community change",
        "style": "short_post",
        "description": "Community building story"
    },
    {
        "core_idea": "The transformation of Richmond's Church Hill neighborhood from overlooked historic district to thriving creative hub, told through the eyes of long-time residents",
        "style": "long_post",
        "description": "Neighborhood evolution story"
    },
    {
        "core_idea": "How Richmond's growing tech scene is creating opportunities for people who never thought they could work in technology, focusing on career changers and non-traditional paths",
        "style": "blog_post",
        "description": "Tech accessibility story"
    }
]

# Quality criteria for evaluation
QUALITY_CRITERIA = {
    "richmond_specificity": "Contains specific Richmond places, people, or cultural references",
    "emotional_resonance": "Evokes emotion and personal connection",
    "narrative_structure": "Has clear beginning, middle, and end with good flow",
    "unique_voice": "Sounds authentic and conversational, not generic",
    "actionable_ending": "Includes clear call-to-action or next steps",
    "local_context": "Integrates Richmond history, culture, or current events",
    "vivid_details": "Uses specific, sensory details rather than abstractions"
}

def print_header(text):
    print("\n" + "="*80)
    print(text.center(80))
    print("="*80 + "\n")

def print_section(text):
    print("\n" + "-"*60)
    print(text)
    print("-"*60)

def test_story_generation(idea_obj):
    """Test story generation for a given idea"""
    print_header(f"Testing: {idea_obj['description']}")
    print(f"Core idea: {idea_obj['core_idea']}")
    print(f"Style: {idea_obj['style']}")
    
    # Generate story
    print("\nGenerating story...")
    start_time = time.time()
    
    response = requests.post(
        f"{BASE_URL}/generate-story",
        json={
            "core_idea": idea_obj["core_idea"],
            "style": idea_obj["style"]
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Error generating story: {response.status_code}")
        print(response.text)
        return None
    
    generation_time = time.time() - start_time
    data = response.json()
    story = data["story"]
    
    print(f"✅ Story generated in {generation_time:.2f} seconds")
    print(f"   Request ID: {data['metadata']['request_id']}")
    print(f"   Context retrieved: {data['metadata']['context_retrieved']}")
    
    return {
        "story": story,
        "metadata": data["metadata"],
        "generation_time": generation_time
    }

def analyze_story_quality(story):
    """Analyze story quality based on criteria"""
    print_section("Quality Analysis")
    
    analysis = {}
    
    # Check for Richmond specificity
    richmond_keywords = [
        "Richmond", "RVA", "James River", "Fan District", "Carytown", "Scott's Addition",
        "Church Hill", "VCU", "Monument Avenue", "First Friday", "Shockoe", "Main Street",
        "Capital One", "Lamplighter", "Maymont", "VMFA", "The National", "Hardywood"
    ]
    richmond_count = sum(1 for keyword in richmond_keywords if keyword.lower() in story.lower())
    analysis["richmond_specificity"] = richmond_count
    
    # Check for emotional words
    emotion_words = [
        "felt", "realized", "discovered", "transformed", "inspired", "proud",
        "community", "together", "belonging", "home", "connection", "meaningful"
    ]
    emotion_count = sum(1 for word in emotion_words if word in story.lower())
    analysis["emotional_resonance"] = emotion_count
    
    # Check for story structure markers
    structure_markers = [
        "began", "started", "then", "after", "finally", "now", "today",
        "but", "however", "despite", "because", "when", "while"
    ]
    structure_count = sum(1 for marker in structure_markers if marker in story.lower())
    analysis["narrative_structure"] = structure_count
    
    # Check for conversational elements
    conversational = [
        "you", "we", "I've", "you've", "we've", "let's", "here's",
        "n't", "'ll", "'re", "'m", "!", "?"
    ]
    conversational_count = sum(1 for element in conversational if element in story)
    analysis["unique_voice"] = conversational_count
    
    # Check for calls to action
    cta_phrases = [
        "join", "visit", "explore", "connect", "share", "discover",
        "next time", "try", "consider", "imagine", "what if"
    ]
    cta_count = sum(1 for phrase in cta_phrases if phrase in story.lower())
    analysis["actionable_ending"] = cta_count
    
    # Word count and sentence analysis
    word_count = len(story.split())
    sentence_count = story.count('.') + story.count('!') + story.count('?')
    avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
    
    # Print analysis
    print(f"📊 Metrics:")
    print(f"   Words: {word_count}")
    print(f"   Sentences: {sentence_count}")
    print(f"   Avg sentence length: {avg_sentence_length:.1f} words")
    print(f"\n✨ Quality Indicators:")
    print(f"   Richmond references: {analysis['richmond_specificity']}")
    print(f"   Emotional words: {analysis['emotional_resonance']}")
    print(f"   Structure markers: {analysis['narrative_structure']}")
    print(f"   Conversational elements: {analysis['unique_voice']}")
    print(f"   Action phrases: {analysis['actionable_ending']}")
    
    # Overall quality score (simple weighted average)
    quality_score = (
        analysis['richmond_specificity'] * 3 +  # Richmond focus is important
        analysis['emotional_resonance'] * 2 +
        analysis['narrative_structure'] * 1.5 +
        analysis['unique_voice'] * 2 +
        analysis['actionable_ending'] * 1.5
    ) / 10
    
    print(f"\n🎯 Overall Quality Score: {quality_score:.1f}/10")
    
    return analysis, quality_score

def display_story_excerpt(story, max_chars=800):
    """Display a formatted excerpt of the story"""
    print_section("Story Excerpt")
    
    if len(story) <= max_chars:
        print(story)
    else:
        # Find a good break point
        excerpt = story[:max_chars]
        last_period = excerpt.rfind('.')
        if last_period > max_chars * 0.8:
            excerpt = excerpt[:last_period + 1]
        else:
            excerpt = excerpt.strip() + "..."
        
        print(excerpt)
        print(f"\n[Story continues... Total length: {len(story)} characters]")

def save_results(results):
    """Save test results to a file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"story_quality_test_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {filename}")

def main():
    """Run story quality tests"""
    print_header("Richmond Storyline Generator - Story Quality Test")
    
    # Check if API is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ API is not running! Start it with: python app.py")
            return
    except:
        print("❌ Cannot connect to API! Start it with: python app.py")
        return
    
    print("✅ API is running\n")
    
    # Run tests
    all_results = []
    total_quality_score = 0
    
    for i, test_idea in enumerate(TEST_IDEAS, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}/{len(TEST_IDEAS)}")
        
        # Generate story
        result = test_story_generation(test_idea)
        if not result:
            continue
        
        # Display excerpt
        display_story_excerpt(result["story"])
        
        # Analyze quality
        analysis, quality_score = analyze_story_quality(result["story"])
        total_quality_score += quality_score
        
        # Store results
        test_result = {
            "test": test_idea,
            "story": result["story"],
            "metadata": result["metadata"],
            "generation_time": result["generation_time"],
            "analysis": analysis,
            "quality_score": quality_score
        }
        all_results.append(test_result)
        
        # Brief pause between tests
        if i < len(TEST_IDEAS):
            print("\n⏳ Waiting before next test...")
            time.sleep(2)
    
    # Summary
    print_header("Test Summary")
    
    if all_results:
        avg_quality = total_quality_score / len(all_results)
        avg_time = sum(r["generation_time"] for r in all_results) / len(all_results)
        
        print(f"📊 Overall Results:")
        print(f"   Tests completed: {len(all_results)}/{len(TEST_IDEAS)}")
        print(f"   Average quality score: {avg_quality:.1f}/10")
        print(f"   Average generation time: {avg_time:.2f} seconds")
        
        print(f"\n📈 Quality Breakdown:")
        for i, result in enumerate(all_results, 1):
            print(f"   Test {i} ({result['test']['style']}): {result['quality_score']:.1f}/10")
        
        # Save results
        save_results({
            "test_date": datetime.now().isoformat(),
            "summary": {
                "tests_run": len(all_results),
                "average_quality": avg_quality,
                "average_time": avg_time
            },
            "detailed_results": all_results
        })
    
    print("\n✨ Quality test complete!")

if __name__ == "__main__":
    main()