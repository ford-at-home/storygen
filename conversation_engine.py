"""
Conversation engine for managing multi-turn story development
"""
import re
from typing import Dict, List, Optional, Any
from session_manager import Session, ConversationStage
from prompts.conversation_prompts import get_prompt_for_stage
from pinecone.vectorstore import retrieve_context
from bedrock.bedrock_llm import generate_story
from nova_analyzer import nova_analyzer
from config import config
import boto3
import json
import logging

logger = logging.getLogger('storygen.conversation')


class ConversationEngine:
    """Manages the conversation flow and LLM interactions"""
    
    def __init__(self):
        self.bedrock_client = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
    
    def process_turn(self, session: Session, user_input: str, 
                     stage: ConversationStage) -> Dict[str, Any]:
        """Process a conversation turn and return the appropriate response"""
        
        logger.info(f"Processing turn for session {session.session_id} in stage {stage.value}")
        
        # Route to appropriate handler based on stage
        handlers = {
            ConversationStage.KICKOFF: self._handle_kickoff,
            ConversationStage.DEPTH_ANALYSIS: self._handle_depth_analysis,
            ConversationStage.FOLLOW_UP: self._handle_follow_up,
            ConversationStage.PERSONAL_ANECDOTE: self._handle_personal_anecdote,
            ConversationStage.HOOK_GENERATION: self._handle_hook_generation,
            ConversationStage.ARC_DEVELOPMENT: self._handle_arc_development,
            ConversationStage.QUOTE_INTEGRATION: self._handle_quote_integration,
            ConversationStage.CTA_GENERATION: self._handle_cta_generation,
            ConversationStage.FINAL_STORY: self._handle_final_story
        }
        
        handler = handlers.get(stage)
        if not handler:
            raise ValueError(f"Unknown conversation stage: {stage}")
        
        return handler(session, user_input)
    
    def _handle_kickoff(self, session: Session, user_input: str) -> Dict[str, Any]:
        """Handle initial idea submission and depth analysis"""
        # Use Nova for advanced depth analysis
        try:
            nova_analysis = nova_analyzer.analyze_story_depth(user_input)
            depth_score = nova_analysis['overall_depth_score']
            
            # Store Nova analysis
            session.story_elements.depth_score = depth_score
            session.story_elements.depth_analysis = json.dumps(nova_analysis)
            
            # Extract themes for better conversation
            themes = nova_analyzer.extract_key_themes(user_input)
            session.metadata['story_themes'] = themes
            
            logger.info(f"Nova analysis complete. Depth score: {depth_score}")
            
        except Exception as e:
            logger.warning(f"Nova analysis failed, falling back to basic analysis: {str(e)}")
            # Fallback to original LLM-based analysis
            depth_prompt = get_prompt_for_stage('depth_analysis', user_input=user_input)
            depth_response = self._call_llm(depth_prompt)
            depth_score = self._extract_depth_score(depth_response)
            session.story_elements.depth_score = depth_score
            session.story_elements.depth_analysis = depth_response
        
        # Add turn to history
        session.add_turn(
            stage=ConversationStage.KICKOFF.value,
            user_input=user_input,
            llm_response=depth_response
        )
        
        # Determine next step based on depth
        if depth_score < 3.5:
            # Use Nova to suggest story angles if available
            story_angles = []
            if 'story_themes' in session.metadata:
                try:
                    story_angles = nova_analyzer.suggest_story_angles(
                        user_input, 
                        session.metadata['story_themes']
                    )
                except Exception as e:
                    logger.warning(f"Failed to get story angles: {str(e)}")
            
            # Generate follow-up question with Nova insights
            nova_insights = json.loads(session.story_elements.depth_analysis) if isinstance(session.story_elements.depth_analysis, str) else session.story_elements.depth_analysis
            follow_up_prompt = get_prompt_for_stage(
                'follow_up_question',
                user_input=user_input,
                depth_analysis=str(nova_insights)
            )
            follow_up_question = self._call_llm(follow_up_prompt)
            
            session.current_stage = ConversationStage.FOLLOW_UP
            
            return {
                "message": follow_up_question,
                "type": "question",
                "progress": 0.2,
                "next_action": "respond"
            }
        else:
            # Good depth - ask for personal anecdote
            anecdote_prompt = get_prompt_for_stage(
                'personal_anecdote',
                user_input=user_input,
                depth_analysis=depth_response
            )
            anecdote_question = self._call_llm(anecdote_prompt)
            
            session.current_stage = ConversationStage.PERSONAL_ANECDOTE
            
            return {
                "message": anecdote_question,
                "type": "question",
                "progress": 0.3,
                "next_action": "respond"
            }
    
    def _handle_follow_up(self, session: Session, user_input: str) -> Dict[str, Any]:
        """Handle follow-up responses to deepen the story"""
        # Store the enhanced idea
        original_idea = session.story_elements.core_idea
        enhanced_idea = f"{original_idea} - {user_input}"
        session.story_elements.core_idea = enhanced_idea
        
        # Add turn
        session.add_turn(
            stage=ConversationStage.FOLLOW_UP.value,
            user_input=user_input
        )
        
        # Now ask for personal anecdote
        anecdote_prompt = get_prompt_for_stage(
            'personal_anecdote',
            user_input=enhanced_idea,
            depth_analysis=session.story_elements.depth_analysis
        )
        anecdote_question = self._call_llm(anecdote_prompt)
        
        session.current_stage = ConversationStage.PERSONAL_ANECDOTE
        
        return {
            "message": anecdote_question,
            "type": "question",
            "progress": 0.4,
            "next_action": "respond"
        }
    
    def _handle_personal_anecdote(self, session: Session, user_input: str) -> Dict[str, Any]:
        """Handle personal anecdote submission"""
        # Store the anecdote
        session.story_elements.personal_anecdote = user_input
        
        # Retrieve Richmond context
        context = retrieve_context(f"{session.story_elements.core_idea} {user_input}")
        
        # Add turn
        session.add_turn(
            stage=ConversationStage.PERSONAL_ANECDOTE.value,
            user_input=user_input,
            context_used=["richmond_context"]
        )
        
        # Generate hooks
        hook_prompt = get_prompt_for_stage(
            'hook_generation',
            story_core=session.story_elements.core_idea,
            richmond_context=context
        )
        hooks_response = self._call_llm(hook_prompt)
        
        # Parse hooks
        hooks = self._parse_hooks(hooks_response)
        session.story_elements.available_hooks = hooks
        
        session.current_stage = ConversationStage.HOOK_GENERATION
        
        return {
            "message": "I've generated three different hooks for your story. Please select the one that resonates most with you:",
            "type": "selection",
            "options": hooks,
            "progress": 0.5,
            "next_action": "select_hook"
        }
    
    def _handle_hook_generation(self, session: Session, user_input: str) -> Dict[str, Any]:
        """Handle hook selection (this is typically handled by select-option endpoint)"""
        # This stage is usually handled by the select-option endpoint
        # But we include it here for completeness
        return self._handle_arc_development(session, user_input)
    
    def _handle_arc_development(self, session: Session, user_input: str) -> Dict[str, Any]:
        """Develop the narrative arc"""
        # Retrieve Richmond context
        context = retrieve_context(session.story_elements.selected_hook)
        
        # Generate narrative arc
        arc_prompt = get_prompt_for_stage(
            'arc_development',
            story_core=session.story_elements.core_idea,
            selected_hook=session.story_elements.selected_hook,
            richmond_context=context
        )
        arc_response = self._call_llm(arc_prompt)
        
        session.story_elements.narrative_arc = arc_response
        
        # Add turn
        session.add_turn(
            stage=ConversationStage.ARC_DEVELOPMENT.value,
            llm_response=arc_response,
            context_used=["richmond_context"]
        )
        
        # Generate quote
        quote_prompt = get_prompt_for_stage(
            'quote_integration',
            story_core=session.story_elements.core_idea,
            selected_hook=session.story_elements.selected_hook,
            narrative_arc=arc_response,
            richmond_context=context
        )
        quote_response = self._call_llm(quote_prompt)
        
        session.story_elements.richmond_quote = quote_response
        session.current_stage = ConversationStage.CTA_GENERATION
        
        # Generate CTAs
        cta_prompt = get_prompt_for_stage(
            'cta_generation',
            story_draft=f"{session.story_elements.selected_hook}\n\n{arc_response}",
            richmond_context=context
        )
        ctas_response = self._call_llm(cta_prompt)
        
        # Parse CTAs
        ctas = self._parse_ctas(ctas_response)
        session.story_elements.available_ctas = ctas
        
        return {
            "message": "Your story is taking shape beautifully! Now, let's choose a call to action that will inspire your readers:",
            "type": "selection",
            "options": ctas,
            "progress": 0.8,
            "next_action": "select_cta"
        }
    
    def _handle_quote_integration(self, session: Session, user_input: str) -> Dict[str, Any]:
        """Handle quote integration (usually automatic)"""
        return self._handle_cta_generation(session, user_input)
    
    def _handle_cta_generation(self, session: Session, user_input: str) -> Dict[str, Any]:
        """Handle CTA selection (typically handled by select-option endpoint)"""
        # This is usually handled by select-option endpoint
        return {
            "message": "Great choice! I'm now ready to create your final story. Click 'Generate Final Story' when you're ready.",
            "type": "ready_for_final",
            "progress": 0.9,
            "next_action": "generate_final"
        }
    
    def _handle_final_story(self, session: Session, user_input: str) -> Dict[str, Any]:
        """Generate the final story (typically handled by generate-final endpoint)"""
        return {
            "message": "Please use the /generate-final endpoint to create your polished story.",
            "type": "instruction",
            "progress": 1.0,
            "next_action": "use_generate_endpoint"
        }
    
    def generate_final_story(self, session: Session, style: str) -> str:
        """Generate the final polished story"""
        # Retrieve comprehensive Richmond context
        context_query = f"{session.story_elements.core_idea} {session.story_elements.personal_anecdote} {session.story_elements.selected_hook}"
        richmond_context = retrieve_context(context_query)
        
        # Generate final story
        final_prompt = get_prompt_for_stage(
            'final_story',
            story_core=session.story_elements.core_idea,
            selected_hook=session.story_elements.selected_hook,
            narrative_arc=session.story_elements.narrative_arc,
            richmond_quote=session.story_elements.richmond_quote,
            selected_cta=session.story_elements.selected_cta,
            richmond_context=richmond_context
        )
        
        # Use the existing generate_story function with the assembled prompt
        # This ensures consistency with token limits and formatting
        final_story = self._call_llm(final_prompt, max_tokens=config.TOKEN_LIMITS[style])
        
        return final_story
    
    def _call_llm(self, prompt: str, max_tokens: int = 1024) -> str:
        """Call the Bedrock LLM with a prompt"""
        try:
            response = self.bedrock_client.invoke_model(
                modelId=config.BEDROCK_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": config.DEFAULT_TEMPERATURE,
                })
            )
            
            result = json.loads(response["body"].read())
            return result.get("completion", "").strip()
            
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise
    
    def _extract_depth_score(self, depth_analysis: str) -> float:
        """Extract depth score from analysis response"""
        # Look for "OVERALL DEPTH SCORE: X.X" pattern
        match = re.search(r'OVERALL DEPTH SCORE:\s*(\d+(?:\.\d+)?)', depth_analysis)
        if match:
            return float(match.group(1))
        
        # Fallback - if we see SUFFICIENT_DEPTH, assume 4.0
        if "SUFFICIENT_DEPTH" in depth_analysis:
            return 4.0
        elif "INSUFFICIENT_DEPTH" in depth_analysis:
            return 2.5
        
        # Default to middle score
        return 3.0
    
    def _parse_hooks(self, hooks_response: str) -> List[str]:
        """Parse hook options from LLM response"""
        hooks = []
        
        # Look for "HOOK N:" pattern
        for i in range(1, 4):
            pattern = rf'HOOK {i}:\s*(.+?)(?=HOOK \d:|$)'
            match = re.search(pattern, hooks_response, re.DOTALL)
            if match:
                hook = match.group(1).strip()
                # Clean up the hook text
                hook = re.sub(r'\s+', ' ', hook)  # Normalize whitespace
                hooks.append(hook)
        
        # Fallback if parsing fails
        if len(hooks) < 3:
            logger.warning("Failed to parse all hooks, using defaults")
            default_hooks = [
                "Connect your story to Richmond's innovation ecosystem",
                "Frame your narrative within Richmond's cultural renaissance",
                "Position your experience as part of Richmond's economic transformation"
            ]
            hooks.extend(default_hooks[len(hooks):])
        
        return hooks[:3]
    
    def _parse_ctas(self, ctas_response: str) -> List[str]:
        """Parse CTA options from LLM response"""
        ctas = []
        
        # Look for "CTA N:" pattern
        for i in range(1, 4):
            pattern = rf'CTA {i}:\s*(.+?)(?=CTA \d:|$)'
            match = re.search(pattern, ctas_response, re.DOTALL)
            if match:
                cta = match.group(1).strip()
                # Clean up the CTA text
                cta = re.sub(r'\s+', ' ', cta)  # Normalize whitespace
                ctas.append(cta)
        
        # Fallback if parsing fails
        if len(ctas) < 3:
            logger.warning("Failed to parse all CTAs, using defaults")
            default_ctas = [
                "Share your Richmond story and inspire others to contribute to our community",
                "Join the conversation about Richmond's future at the next First Friday",
                "Connect with fellow Richmond innovators and builders in our growing ecosystem"
            ]
            ctas.extend(default_ctas[len(ctas):])
        
        return ctas[:3]