"""
Secure Session Management for Richmond Storyline Generator
Replaces in-memory sessions with Redis-based secure session storage
"""

import json
import uuid
import redis
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
import logging
import os
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    LOCKED = "locked"


@dataclass
class ConversationState:
    """Conversation state data structure"""
    session_id: str
    user_id: str
    messages: List[Dict[str, Any]]
    context: Dict[str, Any]
    created_at: str
    last_active: str
    status: str
    metadata: Dict[str, Any]


@dataclass
class SessionData:
    """Session data structure"""
    session_id: str
    user_id: str
    ip_address: str
    user_agent: str
    created_at: str
    last_active: str
    expires_at: str
    status: str
    conversation_state: Optional[ConversationState]
    security_flags: Dict[str, Any]


class SecureSessionManager:
    """Manages secure user sessions with Redis backend"""
    
    def __init__(self, redis_url: str = None):
        self.redis_client = None
        self.cipher_suite = None
        self.session_timeout = timedelta(hours=24)
        self.max_sessions_per_user = 5
        
        # Initialize Redis connection
        self._init_redis(redis_url)
        
        # Initialize encryption
        self._init_encryption()
    
    def _init_redis(self, redis_url: str = None):
        """Initialize Redis connection"""
        try:
            if not redis_url:
                redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
            
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis session store connected successfully")
            
            # Set up key expiration policies
            self._setup_redis_policies()
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            logger.error("⚠️  Session management will not be available")
            self.redis_client = None
    
    def _init_encryption(self):
        """Initialize encryption for session data"""
        encryption_key = os.getenv('SESSION_ENCRYPTION_KEY')
        if not encryption_key:
            encryption_key = Fernet.generate_key()
            logger.warning(f"⚠️  Generated new session encryption key: {encryption_key.decode()}")
            logger.warning("   Please set SESSION_ENCRYPTION_KEY environment variable for production")
        else:
            encryption_key = encryption_key.encode()
        
        self.cipher_suite = Fernet(encryption_key)
    
    def _setup_redis_policies(self):
        """Set up Redis key expiration policies"""
        if not self.redis_client:
            return
        
        try:
            # Set default TTL for session keys
            self.redis_client.config_set('maxmemory-policy', 'allkeys-lru')
            logger.info("✅ Redis session policies configured")
        except Exception as e:
            logger.warning(f"⚠️  Could not configure Redis policies: {e}")
    
    def create_session(self, user_id: str, ip_address: str, user_agent: str) -> str:
        """
        Create a new secure session
        
        Args:
            user_id: User identifier
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Session ID
        """
        if not self.redis_client:
            raise Exception("Redis not available - cannot create session")
        
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        expires_at = now + self.session_timeout
        
        # Create session data
        session_data = SessionData(
            session_id=session_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now.isoformat(),
            last_active=now.isoformat(),
            expires_at=expires_at.isoformat(),
            status=SessionStatus.ACTIVE.value,
            conversation_state=None,
            security_flags={
                "ip_changes": 0,
                "suspicious_activity": False,
                "failed_requests": 0
            }
        )
        
        # Clean up old sessions for this user
        self._cleanup_user_sessions(user_id)
        
        # Store session
        self._store_session(session_data)
        
        # Add to user's active sessions
        self._add_user_session(user_id, session_id)
        
        logger.info(f"✅ Created session {session_id} for user {user_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Retrieve session data
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionData object or None if not found
        """
        if not self.redis_client:
            return None
        
        try:
            encrypted_data = self.redis_client.get(f"session:{session_id}")
            if not encrypted_data:
                return None
            
            # Decrypt and deserialize
            decrypted_data = self.cipher_suite.decrypt(encrypted_data.encode())
            session_dict = json.loads(decrypted_data.decode())
            
            # Convert to SessionData object
            if 'conversation_state' in session_dict and session_dict['conversation_state']:
                session_dict['conversation_state'] = ConversationState(**session_dict['conversation_state'])
            
            session_data = SessionData(**session_dict)
            
            # Check if session is expired
            if datetime.fromisoformat(session_data.expires_at) < datetime.utcnow():
                self.revoke_session(session_id)
                return None
            
            return session_data
            
        except Exception as e:
            logger.error(f"❌ Error retrieving session {session_id}: {e}")
            return None
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update session data
        
        Args:
            session_id: Session identifier
            updates: Dictionary of updates to apply
            
        Returns:
            True if successful, False otherwise
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(session_data, key):
                setattr(session_data, key, value)
        
        # Update last active timestamp
        session_data.last_active = datetime.utcnow().isoformat()
        
        # Store updated session
        return self._store_session(session_data)
    
    def revoke_session(self, session_id: str) -> bool:
        """
        Revoke a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            session_data = self.get_session(session_id)
            if session_data:
                # Remove from user's active sessions
                self._remove_user_session(session_data.user_id, session_id)
            
            # Delete session data
            self.redis_client.delete(f"session:{session_id}")
            
            # Add to revoked sessions blacklist
            self.redis_client.setex(
                f"revoked_session:{session_id}",
                int(self.session_timeout.total_seconds()),
                "revoked"
            )
            
            logger.info(f"✅ Revoked session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error revoking session {session_id}: {e}")
            return False
    
    def validate_session(self, session_id: str, ip_address: str, user_agent: str) -> bool:
        """
        Validate session security
        
        Args:
            session_id: Session identifier
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            True if valid, False otherwise
        """
        if not self.redis_client:
            return False
        
        # Check if session is revoked
        if self.redis_client.exists(f"revoked_session:{session_id}"):
            return False
        
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        # Check session status
        if session_data.status != SessionStatus.ACTIVE.value:
            return False
        
        # Check for IP address changes
        if session_data.ip_address != ip_address:
            session_data.security_flags["ip_changes"] += 1
            
            # Allow limited IP changes (mobile users, etc.)
            if session_data.security_flags["ip_changes"] > 3:
                self.revoke_session(session_id)
                return False
            
            # Update IP address
            session_data.ip_address = ip_address
            self._store_session(session_data)
        
        # Check for user agent changes (more strict)
        if session_data.user_agent != user_agent:
            logger.warning(f"⚠️  User agent changed for session {session_id}")
            self.revoke_session(session_id)
            return False
        
        return True
    
    def get_user_sessions(self, user_id: str) -> List[str]:
        """
        Get all active sessions for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            List of session IDs
        """
        if not self.redis_client:
            return []
        
        try:
            session_ids = self.redis_client.smembers(f"user_sessions:{user_id}")
            return list(session_ids)
        except Exception as e:
            logger.error(f"❌ Error retrieving user sessions: {e}")
            return []
    
    def revoke_all_user_sessions(self, user_id: str) -> bool:
        """
        Revoke all sessions for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        session_ids = self.get_user_sessions(user_id)
        success = True
        
        for session_id in session_ids:
            if not self.revoke_session(session_id):
                success = False
        
        return success
    
    def store_conversation_state(self, session_id: str, messages: List[Dict[str, Any]], 
                               context: Dict[str, Any], metadata: Dict[str, Any] = None) -> bool:
        """
        Store conversation state in session
        
        Args:
            session_id: Session identifier
            messages: List of conversation messages
            context: Conversation context
            metadata: Additional metadata
            
        Returns:
            True if successful, False otherwise
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        # Create conversation state
        conversation_state = ConversationState(
            session_id=session_id,
            user_id=session_data.user_id,
            messages=messages,
            context=context,
            created_at=session_data.created_at,
            last_active=datetime.utcnow().isoformat(),
            status=SessionStatus.ACTIVE.value,
            metadata=metadata or {}
        )
        
        # Update session with conversation state
        session_data.conversation_state = conversation_state
        
        return self._store_session(session_data)
    
    def get_conversation_state(self, session_id: str) -> Optional[ConversationState]:
        """
        Get conversation state from session
        
        Args:
            session_id: Session identifier
            
        Returns:
            ConversationState object or None
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return None
        
        return session_data.conversation_state
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions
        
        Returns:
            Number of sessions cleaned up
        """
        if not self.redis_client:
            return 0
        
        try:
            # Get all session keys
            session_keys = self.redis_client.keys("session:*")
            cleaned_count = 0
            
            for key in session_keys:
                session_id = key.split(":", 1)[1]
                session_data = self.get_session(session_id)
                
                if not session_data:
                    cleaned_count += 1
                    continue
                
                # Check if expired
                if datetime.fromisoformat(session_data.expires_at) < datetime.utcnow():
                    self.revoke_session(session_id)
                    cleaned_count += 1
            
            logger.info(f"✅ Cleaned up {cleaned_count} expired sessions")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up sessions: {e}")
            return 0
    
    def _store_session(self, session_data: SessionData) -> bool:
        """Store session data in Redis"""
        if not self.redis_client:
            return False
        
        try:
            # Convert to dict for serialization
            session_dict = asdict(session_data)
            
            # Encrypt and store
            session_json = json.dumps(session_dict)
            encrypted_data = self.cipher_suite.encrypt(session_json.encode())
            
            # Store with TTL
            ttl_seconds = int(self.session_timeout.total_seconds())
            self.redis_client.setex(
                f"session:{session_data.session_id}",
                ttl_seconds,
                encrypted_data.decode()
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing session: {e}")
            return False
    
    def _add_user_session(self, user_id: str, session_id: str):
        """Add session to user's active sessions"""
        if not self.redis_client:
            return
        
        self.redis_client.sadd(f"user_sessions:{user_id}", session_id)
    
    def _remove_user_session(self, user_id: str, session_id: str):
        """Remove session from user's active sessions"""
        if not self.redis_client:
            return
        
        self.redis_client.srem(f"user_sessions:{user_id}", session_id)
    
    def _cleanup_user_sessions(self, user_id: str):
        """Clean up old sessions for user if exceeding limit"""
        if not self.redis_client:
            return
        
        session_ids = self.get_user_sessions(user_id)
        
        if len(session_ids) >= self.max_sessions_per_user:
            # Get session creation times and sort
            session_times = []
            for session_id in session_ids:
                session_data = self.get_session(session_id)
                if session_data:
                    session_times.append((session_id, session_data.created_at))
            
            # Sort by creation time (oldest first)
            session_times.sort(key=lambda x: x[1])
            
            # Remove oldest sessions
            sessions_to_remove = len(session_times) - self.max_sessions_per_user + 1
            for i in range(sessions_to_remove):
                self.revoke_session(session_times[i][0])
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        if not self.redis_client:
            return {"error": "Redis not available"}
        
        try:
            total_sessions = len(self.redis_client.keys("session:*"))
            revoked_sessions = len(self.redis_client.keys("revoked_session:*"))
            user_sessions = len(self.redis_client.keys("user_sessions:*"))
            
            return {
                "total_active_sessions": total_sessions,
                "revoked_sessions": revoked_sessions,
                "total_users_with_sessions": user_sessions,
                "redis_memory_usage": self.redis_client.memory_usage(),
                "redis_info": self.redis_client.info("memory")
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting session stats: {e}")
            return {"error": str(e)}


# Global session manager instance
session_manager = SecureSessionManager()


def get_session_manager() -> SecureSessionManager:
    """Get the global session manager instance"""
    return session_manager