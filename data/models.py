"""
Data models for Richmond Storyline Generator
Defines all database entities and their relationships
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
from dataclasses import dataclass, field, asdict
import json


# Enums
class UserRole(Enum):
    """User roles for access control"""
    ANONYMOUS = "anonymous"
    REGISTERED = "registered"
    PREMIUM = "premium"
    ADMIN = "admin"


class StoryStyle(Enum):
    """Available story styles"""
    SHORT_POST = "short_post"
    LONG_POST = "long_post"
    BLOG_POST = "blog_post"
    THREAD = "thread"
    NEWSLETTER = "newsletter"


class StoryStatus(Enum):
    """Story generation status"""
    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    PUBLISHED = "published"


class TemplateCategory(Enum):
    """Template categories"""
    BUSINESS = "business"
    PERSONAL = "personal"
    COMMUNITY = "community"
    TECH = "tech"
    CULTURE = "culture"
    CUSTOM = "custom"


# Data Models
@dataclass
class User:
    """User model with profile and preferences"""
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: Optional[str] = None
    username: Optional[str] = None
    role: UserRole = UserRole.ANONYMOUS
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Profile
    profile: Dict[str, Any] = field(default_factory=lambda: {
        "full_name": None,
        "bio": None,
        "location": "Richmond, VA",
        "interests": [],
        "industry": None,
        "company": None,
        "avatar_url": None
    })
    
    # Preferences
    preferences: Dict[str, Any] = field(default_factory=lambda: {
        "default_style": StoryStyle.SHORT_POST.value,
        "voice_enabled": True,
        "auto_save": True,
        "email_notifications": False,
        "richmond_context": True,
        "preferred_themes": []
    })
    
    # Stats
    stats: Dict[str, int] = field(default_factory=lambda: {
        "stories_created": 0,
        "stories_published": 0,
        "total_words": 0,
        "sessions_started": 0,
        "sessions_completed": 0
    })
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "username": self.username,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "profile": self.profile,
            "preferences": self.preferences,
            "stats": self.stats,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        """Create User from dictionary"""
        user = cls(
            user_id=data["user_id"],
            email=data.get("email"),
            username=data.get("username"),
            role=UserRole(data["role"])
        )
        user.created_at = datetime.fromisoformat(data["created_at"])
        user.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("last_login"):
            user.last_login = datetime.fromisoformat(data["last_login"])
        user.profile = data.get("profile", user.profile)
        user.preferences = data.get("preferences", user.preferences)
        user.stats = data.get("stats", user.stats)
        user.metadata = data.get("metadata", {})
        return user


@dataclass
class Story:
    """Story model representing generated content"""
    story_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = None
    session_id: Optional[str] = None
    
    # Content
    title: Optional[str] = None
    content: str = ""
    style: StoryStyle = StoryStyle.SHORT_POST
    status: StoryStatus = StoryStatus.DRAFT
    
    # Story elements
    elements: Dict[str, Any] = field(default_factory=lambda: {
        "core_idea": None,
        "hook": None,
        "personal_anecdote": None,
        "richmond_quote": None,
        "cta": None,
        "tags": [],
        "themes": []
    })
    
    # Richmond context
    richmond_context: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metrics
    metrics: Dict[str, Any] = field(default_factory=lambda: {
        "word_count": 0,
        "char_count": 0,
        "reading_time_minutes": 0,
        "sentiment_score": None,
        "depth_score": None,
        "engagement_score": None
    })
    
    # Generation details
    generation_details: Dict[str, Any] = field(default_factory=lambda: {
        "model": "claude-3-sonnet",
        "temperature": 0.7,
        "max_tokens": None,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "generation_time_seconds": 0,
        "retry_count": 0
    })
    
    # Publishing
    published_at: Optional[datetime] = None
    published_to: List[str] = field(default_factory=list)  # ["blog", "twitter", "linkedin"]
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Version control
    version: int = 1
    versions: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "story_id": self.story_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "title": self.title,
            "content": self.content,
            "style": self.style.value,
            "status": self.status.value,
            "elements": self.elements,
            "richmond_context": self.richmond_context,
            "metrics": self.metrics,
            "generation_details": self.generation_details,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "published_to": self.published_to,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "versions": self.versions
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Story':
        """Create Story from dictionary"""
        story = cls(
            story_id=data["story_id"],
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            title=data.get("title"),
            content=data.get("content", ""),
            style=StoryStyle(data["style"]),
            status=StoryStatus(data["status"])
        )
        story.elements = data.get("elements", story.elements)
        story.richmond_context = data.get("richmond_context", [])
        story.metrics = data.get("metrics", story.metrics)
        story.generation_details = data.get("generation_details", story.generation_details)
        if data.get("published_at"):
            story.published_at = datetime.fromisoformat(data["published_at"])
        story.published_to = data.get("published_to", [])
        story.created_at = datetime.fromisoformat(data["created_at"])
        story.updated_at = datetime.fromisoformat(data["updated_at"])
        story.version = data.get("version", 1)
        story.versions = data.get("versions", [])
        return story
    
    def create_version(self):
        """Create a new version of the story"""
        version_data = {
            "version": self.version,
            "content": self.content,
            "elements": self.elements.copy(),
            "updated_at": self.updated_at.isoformat()
        }
        self.versions.append(version_data)
        self.version += 1
        self.updated_at = datetime.utcnow()


@dataclass
class Template:
    """Story template for quick starts"""
    template_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: TemplateCategory = TemplateCategory.CUSTOM
    
    # Template structure
    structure: Dict[str, Any] = field(default_factory=lambda: {
        "hook_template": None,
        "body_template": None,
        "cta_template": None,
        "prompts": [],
        "example_elements": {}
    })
    
    # Usage
    usage_count: int = 0
    rating: float = 0.0
    ratings_count: int = 0
    
    # Metadata
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_public: bool = True
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "structure": self.structure,
            "usage_count": self.usage_count,
            "rating": self.rating,
            "ratings_count": self.ratings_count,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_public": self.is_public,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Template':
        """Create Template from dictionary"""
        template = cls(
            template_id=data["template_id"],
            name=data["name"],
            description=data["description"],
            category=TemplateCategory(data["category"])
        )
        template.structure = data.get("structure", template.structure)
        template.usage_count = data.get("usage_count", 0)
        template.rating = data.get("rating", 0.0)
        template.ratings_count = data.get("ratings_count", 0)
        template.created_by = data.get("created_by")
        template.created_at = datetime.fromisoformat(data["created_at"])
        template.updated_at = datetime.fromisoformat(data["updated_at"])
        template.is_public = data.get("is_public", True)
        template.tags = data.get("tags", [])
        return template


@dataclass
class RichmondContent:
    """Richmond context content for vector search"""
    content_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_file: str = ""
    content_type: str = ""  # quotes, culture, economy, stories, news
    
    # Content
    title: Optional[str] = None
    content: str = ""
    chunk_index: int = 0
    total_chunks: int = 1
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        "author": None,
        "date": None,
        "source_url": None,
        "tags": [],
        "themes": [],
        "entities": []  # People, places, organizations
    })
    
    # Vector search
    embedding_id: Optional[str] = None
    embedding_model: str = "titan-embed-text-v1"
    
    # Usage tracking
    usage_count: int = 0
    last_used: Optional[datetime] = None
    relevance_scores: List[float] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None  # For time-sensitive content
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "content_id": self.content_id,
            "source_file": self.source_file,
            "content_type": self.content_type,
            "title": self.title,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "metadata": self.metadata,
            "embedding_id": self.embedding_id,
            "embedding_model": self.embedding_model,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "relevance_scores": self.relevance_scores,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RichmondContent':
        """Create RichmondContent from dictionary"""
        content = cls(
            content_id=data["content_id"],
            source_file=data["source_file"],
            content_type=data["content_type"],
            title=data.get("title"),
            content=data["content"],
            chunk_index=data.get("chunk_index", 0),
            total_chunks=data.get("total_chunks", 1)
        )
        content.metadata = data.get("metadata", content.metadata)
        content.embedding_id = data.get("embedding_id")
        content.embedding_model = data.get("embedding_model", "titan-embed-text-v1")
        content.usage_count = data.get("usage_count", 0)
        if data.get("last_used"):
            content.last_used = datetime.fromisoformat(data["last_used"])
        content.relevance_scores = data.get("relevance_scores", [])
        content.created_at = datetime.fromisoformat(data["created_at"])
        content.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("expires_at"):
            content.expires_at = datetime.fromisoformat(data["expires_at"])
        return content


@dataclass
class Analytics:
    """Analytics event for tracking user behavior"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Event details
    event_type: str = ""  # page_view, story_generated, voice_input, etc.
    event_category: str = ""  # interaction, conversion, error, etc.
    event_action: str = ""
    event_label: Optional[str] = None
    event_value: Optional[float] = None
    
    # Context
    context: Dict[str, Any] = field(default_factory=lambda: {
        "user_agent": None,
        "ip_address": None,
        "referrer": None,
        "utm_source": None,
        "utm_medium": None,
        "utm_campaign": None,
        "device_type": None,
        "browser": None,
        "os": None,
        "location": {}
    })
    
    # Custom properties
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamp
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "event_id": self.event_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "event_category": self.event_category,
            "event_action": self.event_action,
            "event_label": self.event_label,
            "event_value": self.event_value,
            "context": self.context,
            "properties": self.properties,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Analytics':
        """Create Analytics from dictionary"""
        event = cls(
            event_id=data["event_id"],
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            event_type=data["event_type"],
            event_category=data["event_category"],
            event_action=data["event_action"],
            event_label=data.get("event_label"),
            event_value=data.get("event_value")
        )
        event.context = data.get("context", event.context)
        event.properties = data.get("properties", {})
        event.timestamp = datetime.fromisoformat(data["timestamp"])
        return event


# Helper functions
def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix"""
    unique_id = str(uuid.uuid4())
    return f"{prefix}_{unique_id}" if prefix else unique_id


def calculate_reading_time(text: str, wpm: int = 200) -> float:
    """Calculate reading time in minutes"""
    word_count = len(text.split())
    return round(word_count / wpm, 1)


def extract_themes(text: str) -> List[str]:
    """Extract themes from text (placeholder for NLP)"""
    # This would be replaced with actual NLP theme extraction
    themes = []
    theme_keywords = {
        "technology": ["tech", "software", "startup", "innovation", "AI"],
        "community": ["community", "together", "local", "Richmond", "neighborhood"],
        "business": ["business", "entrepreneur", "company", "market", "growth"],
        "culture": ["culture", "art", "music", "food", "heritage"],
        "personal": ["story", "journey", "experience", "life", "personal"]
    }
    
    text_lower = text.lower()
    for theme, keywords in theme_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            themes.append(theme)
    
    return themes