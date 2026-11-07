"""
Enhanced session management with persistent storage
Uses DynamoDB and Redis caching for scalable session handling
"""
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import logging
import asyncio

# Import from existing session manager
from session_manager import (
    SessionStatus, ConversationStage, ConversationTurn, 
    StoryElements, Session
)

# Import data layer components
try:
    from data import (
        SessionRepository, entity_cache, cache_manager,
        track_event, save_session as persist_session,
        get_session as retrieve_session
    )
    USE_PERSISTENT_STORAGE = True
except ImportError:
    logger.warning("Data persistence layer not available, falling back to in-memory storage")
    USE_PERSISTENT_STORAGE = False

logger = logging.getLogger('storygen.session.persistent')


class PersistentSessionStore:
    """Session store with persistent storage backend"""
    
    def __init__(self, use_persistent: bool = True):
        self.use_persistent = use_persistent and USE_PERSISTENT_STORAGE
        
        if self.use_persistent:
            self.repository = SessionRepository()
            logger.info("Using persistent session storage (DynamoDB + Redis)")
        else:
            # Fall back to in-memory storage
            from session_manager import SessionStore
            self._fallback_store = SessionStore()
            logger.info("Using in-memory session storage")
        
        # Local cache for active sessions (L1 cache)
        self._local_cache: Dict[str, Session] = {}
        self._cache_ttl = 300  # 5 minutes
        self._cache_timestamps: Dict[str, float] = {}
        
        # Cleanup settings
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
        
        # Background tasks
        self._background_tasks = []
    
    async def save(self, session: Session) -> bool:
        """Save session with caching and persistence"""
        try:
            # Update local cache
            self._local_cache[session.session_id] = session
            self._cache_timestamps[session.session_id] = time.time()
            
            if self.use_persistent:
                # Save to persistent storage
                success = await asyncio.get_event_loop().run_in_executor(
                    None, self.repository.save, session
                )
                
                if success:
                    # Update Redis cache
                    entity_cache.set_session(session)
                    
                    # Track analytics
                    track_event(
                        "session_updated",
                        user_id=session.user_id,
                        session_id=session.session_id,
                        properties={
                            "stage": session.current_stage.value,
                            "turns": len(session.conversation_history)
                        }
                    )
                    
                    logger.info(f"Saved session {session.session_id} to persistent storage")
                else:
                    logger.error(f"Failed to save session {session.session_id}")
                
                return success
            else:
                # Use fallback store
                self._fallback_store.save(session)
                return True
                
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")
            return False
    
    def get(self, session_id: str) -> Optional[Session]:
        """Get session with multi-layer caching"""
        try:
            # Check L1 cache
            if session_id in self._local_cache:
                cache_age = time.time() - self._cache_timestamps.get(session_id, 0)
                if cache_age < self._cache_ttl:
                    session = self._local_cache[session_id]
                    if not session.is_expired():
                        return session
            
            if self.use_persistent:
                # Check L2 cache (Redis)
                session = entity_cache.get_session(session_id)
                if session:
                    # Update L1 cache
                    self._local_cache[session_id] = session
                    self._cache_timestamps[session_id] = time.time()
                    return session
                
                # Load from database
                session = self.repository.get(session_id)
                if session:
                    # Update caches
                    self._local_cache[session_id] = session
                    self._cache_timestamps[session_id] = time.time()
                    entity_cache.set_session(session)
                    return session
            else:
                # Use fallback store
                return self._fallback_store.get(session_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    def delete(self, session_id: str) -> bool:
        """Delete session from all storage layers"""
        try:
            # Remove from L1 cache
            self._local_cache.pop(session_id, None)
            self._cache_timestamps.pop(session_id, None)
            
            if self.use_persistent:
                # Remove from L2 cache
                entity_cache.invalidate_session(session_id)
                
                # Delete from database
                success = self.repository.delete(session_id)
                
                # Track analytics
                track_event(
                    "session_deleted",
                    session_id=session_id
                )
                
                return success
            else:
                # Use fallback store
                self._fallback_store.delete(session_id)
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def get_active_sessions(self, limit: int = 100) -> List[Session]:
        """Get all active sessions"""
        try:
            if self.use_persistent:
                # Get from database with caching
                sessions = self.repository.get_active_sessions(limit=limit)
                
                # Update local cache
                for session in sessions:
                    self._local_cache[session.session_id] = session
                    self._cache_timestamps[session.session_id] = time.time()
                
                return sessions
            else:
                # Use fallback store
                return self._fallback_store.get_active_sessions()
                
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []
    
    def get_user_sessions(self, user_id: str, status: Optional[SessionStatus] = None) -> List[Session]:
        """Get all sessions for a user"""
        try:
            if self.use_persistent:
                return self.repository.get_user_sessions(user_id, status)
            else:
                # Filter from in-memory store
                all_sessions = self._fallback_store._sessions.values()
                user_sessions = [s for s in all_sessions if s.user_id == user_id]
                if status:
                    user_sessions = [s for s in user_sessions if s.status == status]
                return user_sessions
                
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []
    
    async def update_status(self, session_id: str, status: SessionStatus) -> bool:
        """Update session status"""
        try:
            session = self.get(session_id)
            if not session:
                return False
            
            # Update status
            old_status = session.status
            session.status = status
            session.updated_at = datetime.utcnow()
            
            # Save changes
            success = await self.save(session)
            
            if success:
                # Track status change
                track_event(
                    "session_status_changed",
                    session_id=session_id,
                    properties={
                        "old_status": old_status.value,
                        "new_status": status.value
                    }
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update session status: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        try:
            cleaned = 0
            
            # Clean L1 cache
            expired_cache_ids = []
            current_time = time.time()
            
            for session_id, timestamp in self._cache_timestamps.items():
                if current_time - timestamp > self._cache_ttl:
                    expired_cache_ids.append(session_id)
            
            for session_id in expired_cache_ids:
                self._local_cache.pop(session_id, None)
                self._cache_timestamps.pop(session_id, None)
                cleaned += 1
            
            if self.use_persistent:
                # Get and update expired sessions
                active_sessions = self.get_active_sessions(limit=1000)
                
                for session in active_sessions:
                    if session.is_expired():
                        asyncio.create_task(
                            self.update_status(session.session_id, SessionStatus.EXPIRED)
                        )
                        cleaned += 1
            else:
                # Use fallback cleanup
                self._fallback_store._cleanup_expired_sessions()
            
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} expired sessions")
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Failed to cleanup sessions: {e}")
            return 0
    
    def export_session(self, session_id: str) -> Optional[str]:
        """Export session as JSON"""
        session = self.get(session_id)
        if session:
            return json.dumps(session.to_dict(), indent=2)
        return None
    
    async def import_session(self, session_json: str) -> Optional[Session]:
        """Import session from JSON"""
        try:
            data = json.loads(session_json)
            session = Session.from_dict(data)
            
            # Save to persistent storage
            success = await self.save(session)
            
            if success:
                return session
            else:
                logger.error("Failed to import session")
                return None
                
        except Exception as e:
            logger.error(f"Failed to import session: {e}")
            return None
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        try:
            stats = {
                "l1_cache_size": len(self._local_cache),
                "l1_cache_hit_rate": 0,  # Would need to track hits/misses
                "active_sessions": len(self.get_active_sessions()),
                "storage_backend": "persistent" if self.use_persistent else "in-memory"
            }
            
            if self.use_persistent:
                # Add cache stats
                cache_stats = cache_manager.get_stats()
                stats["cache_stats"] = {
                    "hit_rate": cache_stats.get("hit_rate", 0),
                    "redis_memory": cache_stats.get("redis_used_memory", "N/A")
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {}
    
    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        # Periodic cleanup
        async def cleanup_task():
            while True:
                try:
                    await asyncio.sleep(self._cleanup_interval)
                    self.cleanup_expired_sessions()
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")
        
        # Session persistence check
        async def persistence_check():
            while True:
                try:
                    await asyncio.sleep(60)  # Every minute
                    
                    # Check for sessions that need saving
                    for session_id, session in self._local_cache.items():
                        if session.status == SessionStatus.ACTIVE:
                            # Re-save to extend TTL
                            await self.save(session)
                            
                except Exception as e:
                    logger.error(f"Persistence check error: {e}")
        
        # Start tasks
        self._background_tasks = [
            asyncio.create_task(cleanup_task()),
            asyncio.create_task(persistence_check())
        ]
        
        logger.info("Started session background tasks")
    
    def stop_background_tasks(self):
        """Stop background tasks"""
        for task in self._background_tasks:
            task.cancel()
        
        logger.info("Stopped session background tasks")


# Enhanced session factory with persistence
class SessionFactory:
    """Factory for creating sessions with proper initialization"""
    
    @staticmethod
    async def create_session(user_id: Optional[str] = None, 
                           initial_idea: Optional[str] = None) -> Session:
        """Create a new session with persistence"""
        session = Session(user_id=user_id)
        
        if initial_idea:
            session.story_elements.core_idea = initial_idea
        
        # Save to persistent storage
        if USE_PERSISTENT_STORAGE:
            await persist_session(session)
            
            # Track session creation
            track_event(
                "session_created",
                user_id=user_id,
                session_id=session.session_id,
                properties={
                    "has_initial_idea": bool(initial_idea)
                }
            )
        
        logger.info(f"Created session {session.session_id}")
        return session
    
    @staticmethod
    def create_session_sync(user_id: Optional[str] = None,
                           initial_idea: Optional[str] = None) -> Session:
        """Synchronous version of create_session"""
        return asyncio.run(SessionFactory.create_session(user_id, initial_idea))


# Global persistent session store instance
persistent_session_store = PersistentSessionStore(use_persistent=True)

# For backward compatibility, also expose as session_store
session_store = persistent_session_store