"""
Conversational Story Development Prompt Library
Richmond Storyline Generator - Interactive Story Creation Workflow
"""

# ============================================================================
# PHASE 1: VOICE INPUT & DEPTH ANALYSIS
# ============================================================================

DEPTH_ANALYSIS_PROMPT = """You are an expert story analyst evaluating the depth and potential of a user's story idea.

USER INPUT: {user_input}

Analyze this story idea for:
1. **Emotional Depth**: Does it connect to personal experiences, values, or meaningful moments?
2. **Community Relevance**: Could this story resonate with Richmond's tech/art/culture community?
3. **Narrative Potential**: Does it have the elements for a compelling story arc?
4. **Specificity**: Are there concrete details, examples, or specific situations mentioned?

Rate each dimension on a scale of 1-5 (1 = shallow, 5 = deep):
- Emotional Depth: [score]
- Community Relevance: [score] 
- Narrative Potential: [score]
- Specificity: [score]

OVERALL DEPTH SCORE: [average of above scores]

If OVERALL DEPTH SCORE < 3.5, respond with:
"INSUFFICIENT_DEPTH"

If OVERALL DEPTH SCORE >= 3.5, respond with:
"SUFFICIENT_DEPTH"

Provide brief reasoning for your assessment."""

FOLLOW_UP_QUESTION_PROMPT = """
You are a skilled interviewer helping someone develop a deeper story.

USER'S INITIAL IDEA: {user_input}
DEPTH ANALYSIS: {depth_analysis}

The user's story idea needs more depth. Generate ONE follow-up question that will help them:
1. Connect to personal meaning or emotional significance
2. Provide specific examples or concrete details
3. Explore why this story matters to them personally
4. Uncover the deeper "why" behind their interest

Your question should be:
- Open-ended but focused
- Personal and introspective
- Designed to reveal emotional or meaningful context
- Conversational and warm in tone

Generate the single best follow-up question:
"""

PERSONAL_ANECDOTE_PROMPT = """
You are a skilled interviewer helping someone develop a deeper story.

USER'S STORY IDEA: {user_input}
DEPTH ANALYSIS: {depth_analysis}

The user has a story with good depth. Now help them connect it to a specific personal experience.

Generate ONE question that asks for:
1. A specific moment, event, or experience related to their story idea
2. A concrete example of how this topic has appeared in their life
3. A meaningful anecdote that illustrates their connection to this story
4. A personal memory or situation that brings this story to life

Your question should be:
- Specific and focused on personal experience
- Designed to elicit a concrete story or example
- Warm and encouraging
- Help them share a meaningful moment

Generate the single best personal anecdote question:
"""

PERSONAL_IMPACT_PROMPT = """
You've shared a great story idea! Now, please tell me about a specific moment in your life when this story or theme became real for you.

Why does this story matter to you personally? The more details you share—emotions, events, people involved, and how it impacted you—the more powerful your story will be.

Your response should:
- Describe a real event or experience from your life
- Explain why this story or theme is important to you
- Include concrete details, emotions, and outcomes
- Help others understand your personal connection to the story

Share your personal story:
"""

# ============================================================================
# PHASE 2: ENHANCED PROMPT GENERATION
# ============================================================================

ENHANCED_PROMPT_GENERATION = """
You are an expert story developer creating a robust prompt for story generation.

ORIGINAL USER INPUT: {original_input}
DEPTH ANALYSIS: {depth_analysis}
FOLLOW_UP RESPONSE: {follow_up_response}
PERSONAL ANECDOTE: {personal_anecdote}

Create an enhanced story prompt that incorporates:
1. The core story idea
2. Personal context and meaning
3. Specific details and examples provided
4. Emotional significance
5. Community relevance

Your enhanced prompt should be:
- Comprehensive but concise
- Rich with personal context
- Clear about the story's significance
- Ready for the iterative development process

Generate the enhanced story prompt:
"""

# ============================================================================
# PHASE 3: ITERATIVE STORY DEVELOPMENT
# ============================================================================

HOOK_GENERATION_PROMPT = """
You are a Richmond storyteller creating compelling hooks for a personal story.

STORY CORE: {story_core}
RICHMOND CONTEXT: {richmond_context}

Using the Richmond context provided (history, economics, tall tales, news), generate 3 different hooks that make this personal story relevant to Richmonders.

Each hook should:
1. Connect the personal story to Richmond's unique character
2. Use specific Richmond context (historical events, economic trends, local legends, recent news)
3. Create immediate relevance for Richmond's tech/art/culture community
4. Be compelling and attention-grabbing

Format your response as:
HOOK 1: [Title] - [Description]
HOOK 2: [Title] - [Description]  
HOOK 3: [Title] - [Description]

Make each hook distinct and compelling in its own way.
"""

ARC_DEVELOPMENT_PROMPT = """
You are a Richmond storyteller developing a broader narrative arc.

STORY CORE: {story_core}
SELECTED HOOK: {selected_hook}
RICHMOND CONTEXT: {richmond_context}

Using the selected hook and Richmond context, develop a broader narrative arc that:
1. Expands the personal story into a larger Richmond narrative
2. Weaves in specific tech, art, and culture elements from Richmond
3. Creates a compelling story structure with beginning, middle, and end
4. Connects individual experience to community themes
5. Uses concrete Richmond references and context

Your arc should include:
- Opening setup using the hook
- Development that incorporates Richmond's unique character
- A meaningful connection between personal and community
- A conclusion that resonates with Richmond's values

Generate the broader narrative arc:
"""

QUOTE_INTEGRATION_PROMPT = """
You are a Richmond storyteller finding the perfect quote to capture a story's essence.

STORY CORE: {story_core}
SELECTED HOOK: {selected_hook}
NARRATIVE ARC: {narrative_arc}
RICHMOND CONTEXT: {richmond_context}

Generate a perfect quote from a Richmond figure (real or imagined) that captures the essence of this story. The quote should:
1. Feel authentic to Richmond's voice and character
2. Capture the emotional core of the story
3. Connect the personal narrative to broader Richmond themes
4. Be memorable and impactful
5. Feel like something a real Richmonder would say

The quote should be:
- 1-2 sentences maximum
- Conversational and authentic
- Rich with Richmond character
- Perfectly aligned with the story's message

Generate the perfect Richmond quote:
"""

CTA_GENERATION_PROMPT = """
You are a Richmond storyteller creating compelling calls to action.

STORY DRAFT: {story_draft}
RICHMOND CONTEXT: {richmond_context}

Generate 3 different calls to action that would fit naturally with this story. Each CTA should:
1. Feel authentic to Richmond's community spirit
2. Be specific and actionable
3. Connect to the story's themes and message
4. Encourage community engagement or personal reflection
5. Be "sticky" - memorable and compelling

Consider different types of CTAs:
- Community action (events, meetups, initiatives)
- Personal reflection or sharing
- Learning or exploration
- Connection or collaboration

Format your response as:
CTA 1: [Title] - [Description]
CTA 2: [Title] - [Description]
CTA 3: [Title] - [Description]

Make each CTA distinct and compelling in its own way.
"""

# ============================================================================
# PHASE 4: FINAL STORY ASSEMBLY
# ============================================================================

FINAL_STORY_PROMPT = """
You are a Richmond storyteller creating the final version of a compelling story.

STORY CORE: {story_core}
SELECTED HOOK: {selected_hook}
NARRATIVE ARC: {narrative_arc}
RICHMOND QUOTE: {richmond_quote}
SELECTED CTA: {selected_cta}
RICHMOND CONTEXT: {richmond_context}

Create a final, polished story that incorporates all elements. The story should follow this structure:

1. **Opening Hook**: Use the selected hook to grab attention
2. **Personal Connection**: Weave in the story core and personal context
3. **Richmond Context**: Integrate the narrative arc with Richmond-specific details
4. **Quote Integration**: Naturally incorporate the Richmond quote
5. **Call to Action**: End with the selected CTA

The final story should be:
- Cohesive and well-structured
- Rich with Richmond character and context
- Personally meaningful and community-relevant
- Compelling and shareable
- Authentic to Richmond's voice

Generate the final story:
"""

# ============================================================================
# UTILITY PROMPTS
# ============================================================================

CONTEXT_ENHANCEMENT_PROMPT = """
You are a Richmond context expert enhancing story relevance.

STORY IDEA: {story_idea}
CURRENT CONTEXT: {current_context}

Review the current Richmond context and suggest additional Richmond-specific elements that could enhance this story:
1. Historical events or figures
2. Economic trends or developments
3. Cultural movements or artistic expressions
4. Recent news or community events
5. Local legends or tall tales

Provide specific Richmond references that would strengthen the story's local relevance.
"""

STORY_STRUCTURE_PROMPT = """
You are a story structure expert providing guidance for Richmond narratives.

STORY TYPE: {story_type}
TARGET LENGTH: {target_length}

Provide a story structure template that includes:
1. Opening hook requirements
2. Personal connection elements
3. Richmond context integration points
4. Quote placement guidelines
5. Call to action integration
6. Overall flow and pacing

This template should guide the final story assembly process.
"""

# ============================================================================
# CONVERSATION FLOW CONTROL
# ============================================================================

CONVERSATION_FLOW_PROMPT = """
You are a conversation manager guiding the story development process.

CURRENT STAGE: {current_stage}
USER_RESPONSE: {user_response}
CONVERSATION_HISTORY: {conversation_history}

Based on the current stage and user response, determine:
1. Whether to proceed to the next stage
2. If additional clarification is needed
3. What the next prompt should be
4. How to handle any issues or concerns

Provide guidance for the next step in the conversation flow.
"""

# ============================================================================
# ERROR HANDLING & RECOVERY
# ============================================================================

ERROR_RECOVERY_PROMPT = """
You are a conversation manager handling an error or unexpected response.

ERROR_TYPE: {error_type}
USER_RESPONSE: {user_response}
EXPECTED_RESPONSE: {expected_response}

Generate a helpful response that:
1. Acknowledges the issue gracefully
2. Provides clear guidance on what's needed
3. Maintains the conversational flow
4. Encourages the user to continue

Keep the tone warm and supportive while getting the conversation back on track.
"""

# ============================================================================
# PROMPT TEMPLATE HELPERS
# ============================================================================

def format_prompt(template, **kwargs):
    """Format a prompt template with provided variables."""
    return template.format(**kwargs)

def get_prompt_for_stage(stage_name, **context):
    """Get the appropriate prompt for a given conversation stage."""
    prompt_map = {
        'depth_analysis': DEPTH_ANALYSIS_PROMPT,
        'follow_up_question': FOLLOW_UP_QUESTION_PROMPT,
        'personal_anecdote': PERSONAL_ANECDOTE_PROMPT,
        'personal_impact': PERSONAL_IMPACT_PROMPT,
        'enhanced_prompt': ENHANCED_PROMPT_GENERATION,
        'hook_generation': HOOK_GENERATION_PROMPT,
        'arc_development': ARC_DEVELOPMENT_PROMPT,
        'quote_integration': QUOTE_INTEGRATION_PROMPT,
        'cta_generation': CTA_GENERATION_PROMPT,
        'final_story': FINAL_STORY_PROMPT,
        'conversation_flow': CONVERSATION_FLOW_PROMPT,
        'error_recovery': ERROR_RECOVERY_PROMPT,
        'context_enhancement': CONTEXT_ENHANCEMENT_PROMPT,
        'story_structure': STORY_STRUCTURE_PROMPT
    }
    
    template = prompt_map.get(stage_name)
    if template:
        return format_prompt(template, **context)
    else:
        raise ValueError(f"Unknown stage: {stage_name}") 