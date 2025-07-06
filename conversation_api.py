"""
Conversational API endpoints for multi-turn story development
"""
from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, ValidationError
from api_utils import handle_errors, log_request, validate_request, APIError, logger
from session_manager import (
    Session, SessionStatus, ConversationStage, session_store
)
from conversation_engine import ConversationEngine
import uuid
import json

# Create Blueprint
conversation_bp = Blueprint('conversation', __name__, url_prefix='/conversation')

# Initialize conversation engine
conversation_engine = ConversationEngine()


# Request schemas
class StartConversationSchema(Schema):
    """Schema for starting a new conversation"""
    user_id = fields.Str(required=False)
    initial_idea = fields.Str(required=True, validate=lambda x: len(x) > 10)
    voice_data = fields.Dict(required=False)  # For future voice support


class ContinueConversationSchema(Schema):
    """Schema for continuing a conversation"""
    session_id = fields.Str(required=True)
    user_response = fields.Str(required=True)
    response_type = fields.Str(missing="text", validate=lambda x: x in ["text", "voice"])


class GenerateFinalStorySchema(Schema):
    """Schema for generating final story"""
    session_id = fields.Str(required=True)
    style = fields.Str(missing="short_post", 
                      validate=lambda x: x in ["short_post", "long_post", "blog_post"])


class SelectOptionSchema(Schema):
    """Schema for selecting from multiple options (hooks, CTAs)"""
    session_id = fields.Str(required=True)
    selection_type = fields.Str(required=True, 
                                validate=lambda x: x in ["hook", "cta"])
    selected_index = fields.Int(required=True, validate=lambda x: 0 <= x <= 2)


@conversation_bp.route('/start', methods=['POST'])
@handle_errors
@log_request
@validate_request(StartConversationSchema)
def start_conversation():
    """Start a new story development conversation"""
    data = request.validated_data
    
    # Create new session
    session = Session(user_id=data.get('user_id'))
    session.story_elements.core_idea = data['initial_idea']
    
    try:
        # Get initial response from conversation engine
        response = conversation_engine.process_turn(
            session=session,
            user_input=data['initial_idea'],
            stage=ConversationStage.KICKOFF
        )
        
        # Save session
        session_store.save(session)
        
        return jsonify({
            "session_id": session.session_id,
            "status": session.status.value,
            "current_stage": session.current_stage.value,
            "response": response["message"],
            "response_type": response["type"],
            "options": response.get("options"),
            "metadata": {
                "conversation_progress": response.get("progress", 0.1),
                "next_action": response.get("next_action", "respond")
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to start conversation: {str(e)}")
        raise APIError("Failed to start conversation", 500)


@conversation_bp.route('/continue', methods=['POST'])
@handle_errors
@log_request
@validate_request(ContinueConversationSchema)
def continue_conversation():
    """Continue an existing conversation"""
    data = request.validated_data
    
    # Retrieve session
    session = session_store.get(data['session_id'])
    if not session:
        raise APIError("Session not found", 404)
    
    if session.status != SessionStatus.ACTIVE:
        raise APIError(f"Session is {session.status.value}", 400)
    
    try:
        # Process the user's response
        response = conversation_engine.process_turn(
            session=session,
            user_input=data['user_response'],
            stage=session.current_stage
        )
        
        # Save updated session
        session_store.save(session)
        
        return jsonify({
            "session_id": session.session_id,
            "status": session.status.value,
            "current_stage": session.current_stage.value,
            "response": response["message"],
            "response_type": response["type"],
            "options": response.get("options"),
            "metadata": {
                "conversation_progress": response.get("progress", 0.5),
                "next_action": response.get("next_action", "respond"),
                "turns_completed": len(session.conversation_history)
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to continue conversation {data['session_id']}: {str(e)}")
        raise APIError("Failed to continue conversation", 500)


@conversation_bp.route('/select-option', methods=['POST'])
@handle_errors
@log_request
@validate_request(SelectOptionSchema)
def select_option():
    """Select from multiple options (hooks or CTAs)"""
    data = request.validated_data
    
    # Retrieve session
    session = session_store.get(data['session_id'])
    if not session:
        raise APIError("Session not found", 404)
    
    try:
        # Handle selection
        if data['selection_type'] == 'hook':
            if not session.story_elements.available_hooks:
                raise APIError("No hooks available to select from", 400)
            
            selected = session.story_elements.available_hooks[data['selected_index']]
            session.story_elements.selected_hook = selected
            next_stage = ConversationStage.ARC_DEVELOPMENT
            
        elif data['selection_type'] == 'cta':
            if not session.story_elements.available_ctas:
                raise APIError("No CTAs available to select from", 400)
            
            selected = session.story_elements.available_ctas[data['selected_index']]
            session.story_elements.selected_cta = selected
            next_stage = ConversationStage.FINAL_STORY
        
        # Advance to next stage
        session.current_stage = next_stage
        
        # Get next response
        response = conversation_engine.process_turn(
            session=session,
            user_input=f"Selected {data['selection_type']}: {selected}",
            stage=next_stage
        )
        
        # Save session
        session_store.save(session)
        
        return jsonify({
            "session_id": session.session_id,
            "status": "selection_confirmed",
            "selected": selected,
            "response": response["message"],
            "next_stage": next_stage.value
        })
        
    except Exception as e:
        logger.error(f"Failed to process selection: {str(e)}")
        raise APIError("Failed to process selection", 500)


@conversation_bp.route('/generate-final', methods=['POST'])
@handle_errors
@log_request
@validate_request(GenerateFinalStorySchema)
def generate_final_story():
    """Generate the final story from the conversation"""
    data = request.validated_data
    
    # Retrieve session
    session = session_store.get(data['session_id'])
    if not session:
        raise APIError("Session not found", 404)
    
    # Check if ready for final generation
    required_elements = [
        session.story_elements.core_idea,
        session.story_elements.personal_anecdote,
        session.story_elements.selected_hook,
        session.story_elements.selected_cta
    ]
    
    if not all(required_elements):
        raise APIError("Conversation incomplete - missing required story elements", 400)
    
    try:
        # Generate final story
        final_story = conversation_engine.generate_final_story(
            session=session,
            style=data['style']
        )
        
        # Update session
        session.story_elements.final_story = final_story
        session.complete()
        session_store.save(session)
        
        return jsonify({
            "session_id": session.session_id,
            "story": final_story,
            "style": data['style'],
            "metadata": {
                "conversation_duration": session.metadata['session_duration'],
                "total_turns": len(session.conversation_history),
                "story_elements": {
                    "core_idea": session.story_elements.core_idea,
                    "hook": session.story_elements.selected_hook,
                    "quote": session.story_elements.richmond_quote,
                    "cta": session.story_elements.selected_cta
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to generate final story: {str(e)}")
        raise APIError("Failed to generate final story", 500)


@conversation_bp.route('/session/<session_id>', methods=['GET'])
@handle_errors
@log_request
def get_session(session_id):
    """Get session details"""
    session = session_store.get(session_id)
    if not session:
        raise APIError("Session not found", 404)
    
    return jsonify({
        "session_id": session.session_id,
        "status": session.status.value,
        "current_stage": session.current_stage.value,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "conversation_history": [
            {
                "turn": turn.turn,
                "stage": turn.stage,
                "timestamp": turn.timestamp,
                "has_user_input": bool(turn.user_input),
                "has_llm_response": bool(turn.llm_response)
            }
            for turn in session.conversation_history
        ],
        "story_elements": {
            "has_core_idea": bool(session.story_elements.core_idea),
            "has_personal_anecdote": bool(session.story_elements.personal_anecdote),
            "has_selected_hook": bool(session.story_elements.selected_hook),
            "has_selected_cta": bool(session.story_elements.selected_cta),
            "has_final_story": bool(session.story_elements.final_story)
        },
        "metadata": session.metadata
    })


@conversation_bp.route('/session/<session_id>/export', methods=['GET'])
@handle_errors
@log_request
def export_session(session_id):
    """Export session as JSON"""
    session_json = session_store.export_session(session_id)
    if not session_json:
        raise APIError("Session not found", 404)
    
    return jsonify({
        "session_id": session_id,
        "export": json.loads(session_json)
    })


@conversation_bp.route('/sessions/active', methods=['GET'])
@handle_errors
@log_request
def get_active_sessions():
    """Get list of active sessions"""
    active_sessions = session_store.get_active_sessions()
    
    return jsonify({
        "active_sessions": [
            {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "current_stage": session.current_stage.value,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.metadata["last_activity"],
                "turns": len(session.conversation_history)
            }
            for session in active_sessions
        ],
        "total": len(active_sessions)
    })