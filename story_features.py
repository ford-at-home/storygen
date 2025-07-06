"""
Advanced story features including templates, versioning, and export
"""
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger('storygen.features')


class StoryTemplate(Enum):
    """Pre-defined story templates"""
    PERSONAL_JOURNEY = "personal_journey"
    COMMUNITY_IMPACT = "community_impact"
    INNOVATION_STORY = "innovation_story"
    CULTURAL_BRIDGE = "cultural_bridge"
    TRANSFORMATION_TALE = "transformation_tale"
    HOMECOMING_NARRATIVE = "homecoming_narrative"


class StoryVersion:
    """Represents a version of a story"""
    def __init__(self, version_id: str = None, content: str = "", 
                 metadata: Dict = None):
        self.version_id = version_id or str(uuid.uuid4())
        self.content = content
        self.timestamp = datetime.utcnow()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict:
        return {
            "version_id": self.version_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class StoryTemplateManager:
    """Manages story templates and provides structured guidance"""
    
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[StoryTemplate, Dict]:
        """Load pre-defined story templates"""
        return {
            StoryTemplate.PERSONAL_JOURNEY: {
                "name": "Personal Journey",
                "description": "A story of individual growth and discovery in Richmond",
                "structure": {
                    "opening": "Start with a moment of realization or decision",
                    "development": "Show the journey with specific Richmond touchpoints",
                    "climax": "The breakthrough or transformation moment",
                    "resolution": "How Richmond became part of your identity"
                },
                "prompts": [
                    "What brought you to this moment in Richmond?",
                    "How did the city challenge or support you?",
                    "What Richmond places became meaningful to you?",
                    "How are you different because of this journey?"
                ],
                "richmond_elements": ["personal_landmarks", "community_connections", "local_mentors"]
            },
            
            StoryTemplate.COMMUNITY_IMPACT: {
                "name": "Community Impact",
                "description": "How individuals or groups are making Richmond better",
                "structure": {
                    "opening": "Present the problem or opportunity",
                    "development": "Show the community coming together",
                    "climax": "The moment of collective achievement",
                    "resolution": "Lasting impact on Richmond"
                },
                "prompts": [
                    "What need did you see in Richmond?",
                    "Who joined you in addressing it?",
                    "What obstacles did the community overcome?",
                    "How has Richmond changed as a result?"
                ],
                "richmond_elements": ["local_organizations", "neighborhood_specifics", "civic_pride"]
            },
            
            StoryTemplate.INNOVATION_STORY: {
                "name": "Innovation Story",
                "description": "Creating something new in Richmond's evolving landscape",
                "structure": {
                    "opening": "The spark of an idea",
                    "development": "Building with Richmond resources",
                    "climax": "Launch or breakthrough moment",
                    "resolution": "Richmond's role in success"
                },
                "prompts": [
                    "What inspired your innovation in Richmond?",
                    "How did Richmond's ecosystem support you?",
                    "What unique advantages did Richmond offer?",
                    "How is your innovation giving back to Richmond?"
                ],
                "richmond_elements": ["tech_scene", "startup_culture", "local_resources"]
            },
            
            StoryTemplate.CULTURAL_BRIDGE: {
                "name": "Cultural Bridge",
                "description": "Connecting Richmond's diverse communities and traditions",
                "structure": {
                    "opening": "Two worlds in one city",
                    "development": "Finding common ground",
                    "climax": "Moment of connection",
                    "resolution": "Richmond enriched by diversity"
                },
                "prompts": [
                    "What cultures meet in your Richmond story?",
                    "How did you bridge different communities?",
                    "What surprised you about Richmond's diversity?",
                    "How does your story add to Richmond's tapestry?"
                ],
                "richmond_elements": ["cultural_districts", "community_events", "diverse_voices"]
            },
            
            StoryTemplate.TRANSFORMATION_TALE: {
                "name": "Transformation Tale",
                "description": "Richmond's changes reflected in personal experience",
                "structure": {
                    "opening": "Richmond then vs. now",
                    "development": "Parallel paths of change",
                    "climax": "Convergence of personal and city transformation",
                    "resolution": "New Richmond, new you"
                },
                "prompts": [
                    "How has Richmond changed during your time here?",
                    "What transformation did you undergo alongside the city?",
                    "Which Richmond changes matter most to you?",
                    "How do you see Richmond's future?"
                ],
                "richmond_elements": ["historic_change", "neighborhood_evolution", "future_vision"]
            },
            
            StoryTemplate.HOMECOMING_NARRATIVE: {
                "name": "Homecoming Narrative",
                "description": "Returning to Richmond with new perspective",
                "structure": {
                    "opening": "Why you left Richmond",
                    "development": "Experiences elsewhere and the pull home",
                    "climax": "The decision to return",
                    "resolution": "Richmond rediscovered"
                },
                "prompts": [
                    "What drew you away from Richmond?",
                    "What did you miss most while away?",
                    "What brought you back?",
                    "How do you see Richmond differently now?"
                ],
                "richmond_elements": ["hometown_pride", "changed_perspectives", "rediscovery"]
            }
        }
    
    def get_template(self, template_type: StoryTemplate) -> Dict:
        """Get a specific template"""
        return self.templates.get(template_type, {})
    
    def get_all_templates(self) -> List[Dict]:
        """Get all available templates"""
        return [
            {
                "id": template.value,
                "name": data["name"],
                "description": data["description"]
            }
            for template, data in self.templates.items()
        ]
    
    def apply_template(self, session_data: Dict, template_type: StoryTemplate) -> Dict:
        """Apply a template to guide story development"""
        template = self.get_template(template_type)
        if not template:
            return {}
        
        return {
            "template_id": template_type.value,
            "template_name": template["name"],
            "guided_prompts": template["prompts"],
            "structure_guide": template["structure"],
            "richmond_focus": template["richmond_elements"],
            "next_prompt": template["prompts"][0] if template["prompts"] else None
        }


class StoryEnhancer:
    """Enhances stories with additional features"""
    
    def __init__(self):
        self.enhancement_options = [
            "add_sensory_details",
            "strengthen_dialogue",
            "deepen_richmond_context",
            "improve_pacing",
            "enhance_emotional_impact"
        ]
    
    def suggest_enhancements(self, story: str) -> List[Dict]:
        """Analyze story and suggest enhancements"""
        suggestions = []
        
        # Check for sensory details
        sensory_words = ["see", "hear", "smell", "taste", "feel", "touch"]
        sensory_count = sum(1 for word in sensory_words if word in story.lower())
        if sensory_count < 3:
            suggestions.append({
                "type": "add_sensory_details",
                "priority": "high",
                "suggestion": "Add sensory details to make scenes more vivid",
                "example": "What did the coffee shop smell like? How did the river sound?"
            })
        
        # Check for dialogue
        if '"' not in story and "'" not in story:
            suggestions.append({
                "type": "strengthen_dialogue",
                "priority": "medium",
                "suggestion": "Add dialogue to bring characters to life",
                "example": "Include actual conversations to show character voice"
            })
        
        # Check Richmond specificity
        richmond_places = ["Fan District", "Carytown", "Scott's Addition", "Church Hill", 
                          "Monument Avenue", "James River", "VCU", "Main Street"]
        richmond_count = sum(1 for place in richmond_places if place.lower() in story.lower())
        if richmond_count < 2:
            suggestions.append({
                "type": "deepen_richmond_context",
                "priority": "high",
                "suggestion": "Add specific Richmond locations and references",
                "example": "Name specific streets, businesses, or landmarks"
            })
        
        # Check pacing (simple analysis)
        sentences = story.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        if avg_sentence_length > 25:
            suggestions.append({
                "type": "improve_pacing",
                "priority": "medium",
                "suggestion": "Vary sentence length for better rhythm",
                "example": "Mix short, punchy sentences with longer descriptive ones"
            })
        
        return suggestions
    
    def apply_enhancement(self, story: str, enhancement_type: str) -> str:
        """Apply a specific enhancement to the story"""
        # This would integrate with the LLM to enhance specific aspects
        # For now, return the original story with a note
        logger.info(f"Applying enhancement: {enhancement_type}")
        return story  # In production, this would call LLM with enhancement prompt


class StoryExporter:
    """Export stories in various formats"""
    
    def __init__(self):
        self.supported_formats = ["markdown", "html", "json", "pdf"]
    
    def export_story(self, session_id: str, story_data: Dict, 
                    format: str = "markdown") -> str:
        """Export story in specified format"""
        if format not in self.supported_formats:
            raise ValueError(f"Unsupported format: {format}")
        
        if format == "markdown":
            return self._export_markdown(story_data)
        elif format == "html":
            return self._export_html(story_data)
        elif format == "json":
            return self._export_json(story_data)
        elif format == "pdf":
            return self._export_pdf(story_data)
    
    def _export_markdown(self, story_data: Dict) -> str:
        """Export as Markdown"""
        md_content = f"""# {story_data.get('title', 'Richmond Story')}

*Generated on {datetime.now().strftime('%B %d, %Y')}*

## Story

{story_data.get('story', '')}

---

### Story Elements

**Core Idea:** {story_data.get('core_idea', 'N/A')}

**Hook:** {story_data.get('hook', 'N/A')}

**Richmond Quote:** {story_data.get('quote', 'N/A')}

**Call to Action:** {story_data.get('cta', 'N/A')}

---

*Created with Richmond Storyline Generator*
"""
        return md_content
    
    def _export_html(self, story_data: Dict) -> str:
        """Export as HTML"""
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{story_data.get('title', 'Richmond Story')}</title>
    <style>
        body {{ font-family: Georgia, serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        .meta {{ color: #666; font-style: italic; }}
        .story {{ margin: 30px 0; }}
        .elements {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .footer {{ text-align: center; color: #999; margin-top: 40px; }}
    </style>
</head>
<body>
    <h1>{story_data.get('title', 'Richmond Story')}</h1>
    <p class="meta">Generated on {datetime.now().strftime('%B %d, %Y')}</p>
    
    <div class="story">
        {story_data.get('story', '').replace(chr(10), '<br><br>')}
    </div>
    
    <div class="elements">
        <h3>Story Elements</h3>
        <p><strong>Core Idea:</strong> {story_data.get('core_idea', 'N/A')}</p>
        <p><strong>Hook:</strong> {story_data.get('hook', 'N/A')}</p>
        <p><strong>Richmond Quote:</strong> {story_data.get('quote', 'N/A')}</p>
        <p><strong>Call to Action:</strong> {story_data.get('cta', 'N/A')}</p>
    </div>
    
    <p class="footer">Created with Richmond Storyline Generator</p>
</body>
</html>"""
        return html_content
    
    def _export_json(self, story_data: Dict) -> str:
        """Export as JSON"""
        export_data = {
            "title": story_data.get('title', 'Richmond Story'),
            "generated_at": datetime.now().isoformat(),
            "story": story_data.get('story', ''),
            "metadata": {
                "core_idea": story_data.get('core_idea', ''),
                "hook": story_data.get('hook', ''),
                "quote": story_data.get('quote', ''),
                "cta": story_data.get('cta', ''),
                "style": story_data.get('style', 'short_post'),
                "word_count": len(story_data.get('story', '').split())
            }
        }
        return json.dumps(export_data, indent=2)
    
    def _export_pdf(self, story_data: Dict) -> str:
        """Export as PDF (placeholder - would use reportlab or similar)"""
        # This would generate actual PDF in production
        return "PDF export not yet implemented"


class StoryVersionManager:
    """Manage story versions and edits"""
    
    def __init__(self):
        self.versions: Dict[str, List[StoryVersion]] = {}
    
    def save_version(self, session_id: str, content: str, 
                    metadata: Optional[Dict] = None) -> str:
        """Save a new version of a story"""
        if session_id not in self.versions:
            self.versions[session_id] = []
        
        version = StoryVersion(content=content, metadata=metadata or {})
        self.versions[session_id].append(version)
        
        logger.info(f"Saved version {version.version_id} for session {session_id}")
        return version.version_id
    
    def get_versions(self, session_id: str) -> List[Dict]:
        """Get all versions for a session"""
        if session_id not in self.versions:
            return []
        
        return [v.to_dict() for v in self.versions[session_id]]
    
    def get_version(self, session_id: str, version_id: str) -> Optional[Dict]:
        """Get a specific version"""
        if session_id not in self.versions:
            return None
        
        for version in self.versions[session_id]:
            if version.version_id == version_id:
                return version.to_dict()
        
        return None
    
    def compare_versions(self, session_id: str, version_id1: str, 
                        version_id2: str) -> Dict:
        """Compare two versions (basic implementation)"""
        v1 = self.get_version(session_id, version_id1)
        v2 = self.get_version(session_id, version_id2)
        
        if not v1 or not v2:
            return {"error": "Version not found"}
        
        # Simple comparison - in production would use diff algorithm
        return {
            "version_1": version_id1,
            "version_2": version_id2,
            "timestamp_1": v1["timestamp"],
            "timestamp_2": v2["timestamp"],
            "content_changed": v1["content"] != v2["content"],
            "word_count_1": len(v1["content"].split()),
            "word_count_2": len(v2["content"].split())
        }


# Global instances
template_manager = StoryTemplateManager()
story_enhancer = StoryEnhancer()
story_exporter = StoryExporter()
version_manager = StoryVersionManager()