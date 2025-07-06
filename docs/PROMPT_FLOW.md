# 📝 Prompt Flow Documentation

This document outlines the prompt design and flow for the Richmond Storyline Generator's conversational story development system.

---

## 🎯 Overview

The system uses a multi-stage prompt flow to guide users through story development, from initial voice input to final story generation. Each stage has specific prompts designed to elicit the right information and guide the conversation effectively.

---

## 🔄 Conversation Flow Stages

### Stage 1: Voice Input & Depth Analysis

**Purpose**: Evaluate the depth and potential of the user's initial story idea

**Prompt**: `DEPTH_ANALYSIS_PROMPT`
- Analyzes emotional depth, community relevance, narrative potential, and specificity
- Returns a depth score and classification (SUFFICIENT_DEPTH or INSUFFICIENT_DEPTH)
- Provides reasoning for the assessment

**Example Flow**:
```
User Input: "I want to tell a story about local zoning laws for backyard egg hens"
Analysis: Emotional Depth: 2, Community Relevance: 4, Narrative Potential: 3, Specificity: 2
Result: INSUFFICIENT_DEPTH
```

### Stage 2: Follow-up Questions

**Purpose**: Deepen insufficient story ideas or gather personal anecdotes for sufficient ones

**Prompts**: 
- `FOLLOW_UP_QUESTION_PROMPT` (for insufficient depth)
- `PERSONAL_ANECDOTE_PROMPT` (for sufficient depth)
- `PERSONAL_IMPACT_PROMPT` (for personal connection)

**Example Questions**:
- "For you, why does this story about zoning laws mean something?"
- "What's a quick anecdote where this has appeared in a meaningful way in your life?"

### Stage 3: Enhanced Prompt Generation

**Purpose**: Create a comprehensive prompt for the iterative story development process

**Prompt**: `ENHANCED_PROMPT_GENERATION`
- Combines original input, depth analysis, and follow-up responses
- Creates a robust foundation for story development
- Includes personal context and emotional significance

### Stage 4: Iterative Story Development

#### 4.1 Hook Generation
**Prompt**: `HOOK_GENERATION_PROMPT`
- Uses Richmond context to generate 3 compelling hooks
- Each hook connects personal story to Richmond's unique character
- User selects their preferred hook

#### 4.2 Arc Development
**Prompt**: `ARC_DEVELOPMENT_PROMPT`
- Develops broader narrative arc using selected hook
- Weaves in Richmond tech/art/culture elements
- Creates compelling story structure

#### 4.3 Quote Integration
**Prompt**: `QUOTE_INTEGRATION_PROMPT`
- Generates perfect Richmond quote to capture story essence
- Feels authentic to Richmond's voice and character
- Aligns with story's emotional core

#### 4.4 Call-to-Action Generation
**Prompt**: `CTA_GENERATION_PROMPT`
- Creates 3 sticky calls to action
- User selects preferred CTA
- Encourages community engagement

### Stage 5: Final Story Assembly

**Purpose**: Combine all elements into a cohesive, polished story

**Prompt**: `FINAL_STORY_PROMPT`
- Integrates story core, hook, arc, quote, and CTA
- Follows structured narrative format
- Maintains Richmond authenticity and personal relevance

---

## 🧠 Prompt Design Principles

### 1. **Progressive Disclosure**
- Start with broad questions, narrow to specifics
- Build on previous responses
- Maintain conversation flow

### 2. **Richmond Authenticity**
- All prompts incorporate Richmond context
- Use local references and cultural elements
- Maintain community voice and character

### 3. **Personal Connection**
- Encourage personal anecdotes and experiences
- Connect individual stories to community themes
- Foster emotional engagement

### 4. **Iterative Refinement**
- Allow user choice at key decision points
- Provide multiple options for hooks and CTAs
- Enable story evolution through conversation

---

## 📋 Prompt Template Structure

Each prompt follows this structure:

```python
PROMPT_NAME = """
You are [role/context]

[Specific instructions and requirements]

[Input variables: {variable_name}]

[Expected output format]

[Additional guidance]
"""
```

### Template Variables

Common variables used across prompts:
- `{user_input}` - Original user story idea
- `{story_core}` - Enhanced story core with personal context
- `{richmond_context}` - Retrieved Richmond knowledge base content
- `{selected_hook}` - User-selected story hook
- `{narrative_arc}` - Developed story arc
- `{richmond_quote}` - Generated Richmond quote
- `{selected_cta}` - User-selected call to action

---

## 🔧 Utility Prompts

### Context Enhancement
**Prompt**: `CONTEXT_ENHANCEMENT_PROMPT`
- Suggests additional Richmond-specific elements
- Enhances story relevance and local connection

### Story Structure
**Prompt**: `STORY_STRUCTURE_PROMPT`
- Provides guidance for narrative structure
- Ensures consistent story format

### Conversation Flow Control
**Prompt**: `CONVERSATION_FLOW_PROMPT`
- Manages conversation progression
- Handles stage transitions and user responses

### Error Recovery
**Prompt**: `ERROR_RECOVERY_PROMPT`
- Gracefully handles unexpected responses
- Maintains conversation flow during issues

---

## 🚀 Implementation Notes

### Prompt Management
- All prompts stored in `prompts/conversation_prompts.py`
- Use `get_prompt_for_stage()` helper for easy access
- Template variables handled by `format_prompt()` function

### LLM Integration
- Claude 3 Sonnet for story generation and conversation
- Nova for depth analysis and assessment
- Consistent temperature and token limits per stage

### Context Integration
- Richmond knowledge base provides local context
- Vector search retrieves relevant information
- Context woven naturally into prompts

---

## 📈 Future Enhancements

- **Dynamic Prompt Adjustment**: Adapt prompts based on user behavior
- **Multi-language Support**: Extend prompts for different languages
- **Style Templates**: Add prompts for different story styles and tones
- **A/B Testing**: Test different prompt variations for effectiveness