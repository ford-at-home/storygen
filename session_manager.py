"""
Session management for multi-turn conversations
Handles session state persistence and lifecycle
"""
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger('storygen.session')


class SessionStatus(Enum):
    """Session status states"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    EXPIRED = "expired"


class ConversationStage(Enum):
    """Conversation stages"""
    KICKOFF = "kickoff"
    DEPTH_ANALYSIS = "depth_analysis"
    FOLLOW_UP = "follow_up"
    PERSONAL_ANECDOTE = "personal_anecdote"
    HOOK_GENERATION = "hook_generation"
    ARC_DEVELOPMENT = "arc_development"
    QUOTE_INTEGRATION = "quote_integration"
    CTA_GENERATION = "cta_generation"
    FINAL_STORY = "final_story"


class ConversationTurn:
    """Represents a single turn in the conversation"""
    def __init__(self, turn_number: int, stage: str, user_input: str = None, 
                 llm_response: str = None, context_used: List[str] = None):
        self.turn = turn_number
        self.stage = stage
        self.user_input = user_input
        self.llm_response = llm_response
        self.timestamp = datetime.utcnow().isoformat()
        self.context_used = context_used or []
    
    def to_dict(self) -> Dict:
        return {
            "turn": self.turn,
            "stage": self.stage,
            "user_input": self.user_input,
            "llm_response": self.llm_response,
            "timestamp": self.timestamp,
            "context_used": self.context_used
        }


class StoryElements:
    """Container for story elements collected during conversation"""
    def __init__(self):
        self.core_idea = None
        self.depth_score = None
        self.depth_analysis = None
        self.personal_anecdote = None
        self.selected_hook = None
        self.available_hooks = []
        self.narrative_arc = None
        self.richmond_quote = None
        self.selected_cta = None
        self.available_ctas = []
        self.final_story = None
    
    def to_dict(self) -> Dict:
        return {
            "core_idea": self.core_idea,
            "depth_score": self.depth_score,
            "depth_analysis": self.depth_analysis,
            "personal_anecdote": self.personal_anecdote,
            "selected_hook": self.selected_hook,
            "available_hooks": self.available_hooks,
            "narrative_arc": self.narrative_arc,
            "richmond_quote": self.richmond_quote,
            "selected_cta": self.selected_cta,
            "available_ctas": self.available_ctas,
            "final_story": self.final_story
        }
    
    def from_dict(self, data: Dict):
        """Load story elements from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


class Session:
    """Represents a story development session"""
    def __init__(self, session_id: str = None, user_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.status = SessionStatus.ACTIVE
        self.current_stage = ConversationStage.KICKOFF
        self.conversation_history: List[ConversationTurn] = []
        self.story_elements = StoryElements()
        self.metadata = {
            "session_duration": 0,
            "llm_calls": 0,
            "context_chunks_retrieved": 0,
            "last_activity": datetime.utcnow().isoformat()
        }
    
    def add_turn(self, stage: str, user_input: str = None, 
                 llm_response: str = None, context_used: List[str] = None):
        """Add a conversation turn"""
        turn_number = len(self.conversation_history) + 1
        turn = ConversationTurn(turn_number, stage, user_input, llm_response, context_used)
        self.conversation_history.append(turn)
        self.updated_at = datetime.utcnow()
        self.metadata["last_activity"] = self.updated_at.isoformat()
        self.metadata["llm_calls"] += 1 if llm_response else 0
        logger.info(f"Session {self.session_id}: Added turn {turn_number} in stage {stage}")
    
    def get_last_turn(self) -> Optional[ConversationTurn]:
        """Get the most recent conversation turn"""
        return self.conversation_history[-1] if self.conversation_history else None
    
    def get_conversation_context(self, max_turns: int = 5) -> str:
        """Get recent conversation context for LLM"""
        recent_turns = self.conversation_history[-max_turns:]
        context_parts = []
        
        for turn in recent_turns:
            if turn.user_input:
                context_parts.append(f"User: {turn.user_input}")
            if turn.llm_response:
                context_parts.append(f"Assistant: {turn.llm_response}")
        
        return "\n\n".join(context_parts)
    
    def advance_stage(self):
        """Move to the next conversation stage"""
        stage_order = [
            ConversationStage.KICKOFF,
            ConversationStage.DEPTH_ANALYSIS,
            ConversationStage.FOLLOW_UP,
            ConversationStage.PERSONAL_ANECDOTE,
            ConversationStage.HOOK_GENERATION,
            ConversationStage.ARC_DEVELOPMENT,
            ConversationStage.QUOTE_INTEGRATION,
            ConversationStage.CTA_GENERATION,
            ConversationStage.FINAL_STORY
        ]
        
        current_index = stage_order.index(self.current_stage)
        if current_index < len(stage_order) - 1:
            self.current_stage = stage_order[current_index + 1]
            logger.info(f"Session {self.session_id}: Advanced to stage {self.current_stage.value}")
    
    def complete(self):
        """Mark session as completed"""
        self.status = SessionStatus.COMPLETED
        self.updated_at = datetime.utcnow()
        duration = (self.updated_at - self.created_at).total_seconds()
        self.metadata["session_duration"] = duration
        logger.info(f"Session {self.session_id}: Completed after {duration:.1f} seconds")
    
    def abandon(self):
        """Mark session as abandoned"""
        self.status = SessionStatus.ABANDONED
        self.updated_at = datetime.utcnow()
        logger.warning(f"Session {self.session_id}: Abandoned")
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired due to inactivity"""
        last_activity = datetime.fromisoformat(self.metadata["last_activity"])
        return datetime.utcnow() - last_activity > timedelta(minutes=timeout_minutes)
    
    def to_dict(self) -> Dict:
        """Convert session to dictionary for storage"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
            "current_stage": self.current_stage.value,
            "conversation_history": [turn.to_dict() for turn in self.conversation_history],
            "story_elements": self.story_elements.to_dict(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Session':
        """Create session from dictionary"""
        session = cls(session_id=data["session_id"], user_id=data.get("user_id"))
        session.created_at = datetime.fromisoformat(data["created_at"])
        session.updated_at = datetime.fromisoformat(data["updated_at"])
        session.status = SessionStatus(data["status"])
        session.current_stage = ConversationStage(data["current_stage"])
        
        # Restore conversation history
        session.conversation_history = []
        for turn_data in data["conversation_history"]:
            turn = ConversationTurn(
                turn_data["turn"],
                turn_data["stage"],
                turn_data.get("user_input"),
                turn_data.get("llm_response"),
                turn_data.get("context_used", [])
            )
            turn.timestamp = turn_data["timestamp"]
            session.conversation_history.append(turn)
        
        # Restore story elements
        session.story_elements.from_dict(data["story_elements"])
        
        # Restore metadata
        session.metadata = data["metadata"]
        
        return session


class SessionStore:
    """In-memory session storage (to be replaced with DynamoDB)"""
    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def save(self, session: Session):
        """Save session to store"""
        self._sessions[session.session_id] = session
        self._maybe_cleanup()
        logger.info(f"Saved session {session.session_id}")
    
    def get(self, session_id: str) -> Optional[Session]:
        """Retrieve session by ID"""
        session = self._sessions.get(session_id)
        if session and session.is_expired():
            session.status = SessionStatus.EXPIRED
            logger.warning(f"Session {session_id} has expired")
        return session
    
    def delete(self, session_id: str):
        """Delete session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Deleted session {session_id}")
    
    def get_active_sessions(self) -> List[Session]:
        """Get all active sessions"""
        return [s for s in self._sessions.values() if s.status == SessionStatus.ACTIVE]
    
    def _maybe_cleanup(self):
        """Periodically clean up expired sessions"""
        if time.time() - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired_sessions()
            self._last_cleanup = time.time()
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions from memory"""
        expired_ids = []
        for session_id, session in self._sessions.items():
            if session.is_expired(timeout_minutes=60):  # 1 hour timeout for cleanup
                expired_ids.append(session_id)
        
        for session_id in expired_ids:
            self.delete(session_id)
        
        if expired_ids:
            logger.info(f"Cleaned up {len(expired_ids)} expired sessions")
    
    def export_session(self, session_id: str) -> Optional[str]:
        """Export session as JSON"""
        session = self.get(session_id)
        if session:
            return json.dumps(session.to_dict(), indent=2)
        return None
    
    def import_session(self, session_json: str) -> Optional[Session]:
        """Import session from JSON"""
        try:
            data = json.loads(session_json)
            session = Session.from_dict(data)
            self.save(session)
            return session
        except Exception as e:
            logger.error(f"Failed to import session: {str(e)}")
            return None


# Global session store instance
session_store = SessionStore()