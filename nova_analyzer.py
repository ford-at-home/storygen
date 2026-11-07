"""
Nova depth analyzer for advanced story analysis
Uses Amazon Nova for deeper insight extraction
"""
import boto3
import json
import logging
from typing import Dict, List, Optional, Tuple
from config import config

logger = logging.getLogger('storygen.nova')


class NovaAnalyzer:
    """Advanced story depth analysis using Amazon Nova"""
    
    def __init__(self):
        """Initialize Nova client via Bedrock"""
        self.bedrock_client = boto3.client(
            "bedrock-runtime", 
            region_name=config.AWS_REGION
        )
        # Nova model IDs (these are hypothetical - replace with actual when available)
        self.nova_model_id = "amazon.nova-pro-v1:0"
        self.analysis_temperature = 0.3  # Lower temp for more focused analysis
    
    def analyze_story_depth(self, story_idea: str, 
                          conversation_context: Optional[str] = None) -> Dict:
        """
        Perform deep analysis of story idea using Nova
        
        Args:
            story_idea: The user's story idea
            conversation_context: Optional previous conversation
            
        Returns:
            Comprehensive depth analysis
        """
        prompt = self._build_analysis_prompt(story_idea, conversation_context)
        
        try:
            response = self.bedrock_client.invoke_model(
                modelId=self.nova_model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "prompt": prompt,
                    "max_tokens": 2000,
                    "temperature": self.analysis_temperature,
                    "top_p": 0.9
                })
            )
            
            result = json.loads(response["body"].read())
            analysis_text = result.get("completion", "")
            
            # Parse the structured analysis
            return self._parse_analysis(analysis_text)
            
        except Exception as e:
            logger.error(f"Nova analysis failed: {str(e)}")
            # Fallback to basic analysis
            return self._basic_analysis(story_idea)
    
    def extract_key_themes(self, text: str) -> List[str]:
        """Extract key themes and concepts from text"""
        prompt = f"""Analyze this text and extract the key themes, concepts, and emotional undertones.

Text: {text}

Provide a structured analysis with:
1. Primary themes (max 3)
2. Emotional undertones
3. Narrative potential
4. Connection opportunities

Format your response as JSON."""

        try:
            response = self.bedrock_client.invoke_model(
                modelId=self.nova_model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "prompt": prompt,
                    "max_tokens": 500,
                    "temperature": 0.5
                })
            )
            
            result = json.loads(response["body"].read())
            completion = result.get("completion", "{}")
            
            # Try to parse JSON response
            try:
                themes_data = json.loads(completion)
                return themes_data.get("primary_themes", [])
            except:
                # Fallback to simple extraction
                return self._extract_themes_simple(text)
                
        except Exception as e:
            logger.error(f"Theme extraction failed: {str(e)}")
            return self._extract_themes_simple(text)
    
    def suggest_story_angles(self, story_idea: str, themes: List[str]) -> List[Dict]:
        """Suggest different angles for developing the story"""
        prompt = f"""Given this story idea and themes, suggest 3 unique angles for developing it into a compelling Richmond story.

Story idea: {story_idea}
Themes: {', '.join(themes)}

For each angle provide:
1. A compelling hook
2. The unique perspective
3. Richmond connection opportunity
4. Emotional resonance

Format as JSON with an array of angles."""

        try:
            response = self.bedrock_client.invoke_model(
                modelId=self.nova_model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "prompt": prompt,
                    "max_tokens": 1000,
                    "temperature": 0.7
                })
            )
            
            result = json.loads(response["body"].read())
            completion = result.get("completion", "[]")
            
            try:
                angles = json.loads(completion)
                return angles if isinstance(angles, list) else []
            except:
                return []
                
        except Exception as e:
            logger.error(f"Story angle generation failed: {str(e)}")
            return self._default_story_angles(story_idea)
    
    def enhance_personal_connection(self, story_idea: str, 
                                  personal_anecdote: str) -> Dict:
        """Enhance the personal connection in the story"""
        prompt = f"""Analyze how this personal anecdote enhances the story idea and suggest ways to deepen the connection.

Story idea: {story_idea}
Personal anecdote: {personal_anecdote}

Provide:
1. Emotional core of the connection
2. Universal themes that resonate
3. Specific details that add authenticity
4. Ways to strengthen the personal element

Format your response as structured text."""

        try:
            response = self.bedrock_client.invoke_model(
                modelId=self.nova_model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "prompt": prompt,
                    "max_tokens": 800,
                    "temperature": 0.6
                })
            )
            
            result = json.loads(response["body"].read())
            enhancement = result.get("completion", "")
            
            return {
                "enhanced_connection": enhancement,
                "strength_score": self._calculate_connection_strength(personal_anecdote),
                "improvement_suggestions": self._extract_suggestions(enhancement)
            }
            
        except Exception as e:
            logger.error(f"Personal connection enhancement failed: {str(e)}")
            return {
                "enhanced_connection": "Focus on specific moments and emotions in your story.",
                "strength_score": 3.0,
                "improvement_suggestions": []
            }
    
    def _build_analysis_prompt(self, story_idea: str, context: Optional[str]) -> str:
        """Build comprehensive analysis prompt"""
        base_prompt = f"""Perform a deep analysis of this story idea for a Richmond, Virginia narrative.

Story idea: {story_idea}
"""
        
        if context:
            base_prompt += f"\nPrevious context: {context}\n"
        
        base_prompt += """
Analyze the following dimensions:

1. NARRATIVE DEPTH (1-5 scale)
   - Personal stakes and emotional investment
   - Conflict or transformation potential
   - Specificity and concrete details
   - Universal themes that resonate

2. RICHMOND CONNECTION (1-5 scale)
   - Local relevance and authenticity
   - Community impact potential
   - Cultural or historical ties
   - Economic or social significance

3. AUDIENCE ENGAGEMENT (1-5 scale)
   - Relatability and accessibility
   - Emotional hook strength
   - Call-to-action potential
   - Shareability factor

4. DEVELOPMENT POTENTIAL (1-5 scale)
   - Story arc possibilities
   - Character development opportunities
   - Multiple angle potential
   - Expansion possibilities

Provide specific examples and suggestions for each dimension.
Include an overall depth score and specific recommendations for story development.
"""
        return base_prompt
    
    def _parse_analysis(self, analysis_text: str) -> Dict:
        """Parse Nova's analysis into structured data"""
        # This would parse the detailed analysis
        # For now, return a structured response
        analysis = {
            "overall_depth_score": 0,
            "dimensions": {
                "narrative_depth": {"score": 0, "analysis": ""},
                "richmond_connection": {"score": 0, "analysis": ""},
                "audience_engagement": {"score": 0, "analysis": ""},
                "development_potential": {"score": 0, "analysis": ""}
            },
            "recommendations": [],
            "strengths": [],
            "areas_for_improvement": [],
            "suggested_next_steps": []
        }
        
        # Extract scores using regex or parsing
        # This is simplified - real implementation would be more robust
        import re
        
        # Look for scores
        score_pattern = r"(\w+[\s\w]*?):\s*(\d+(?:\.\d+)?)/5"
        scores = re.findall(score_pattern, analysis_text)
        
        for dimension, score in scores:
            dim_key = dimension.lower().replace(" ", "_")
            if dim_key in analysis["dimensions"]:
                analysis["dimensions"][dim_key]["score"] = float(score)
        
        # Calculate overall score
        total_score = sum(d["score"] for d in analysis["dimensions"].values())
        analysis["overall_depth_score"] = total_score / len(analysis["dimensions"])
        
        # Extract recommendations (simplified)
        if "recommend" in analysis_text.lower():
            rec_section = analysis_text.split("recommend")[1][:500]
            analysis["recommendations"] = [rec.strip() for rec in rec_section.split("-")[1:4]]
        
        return analysis
    
    def _basic_analysis(self, story_idea: str) -> Dict:
        """Fallback basic analysis without Nova"""
        word_count = len(story_idea.split())
        has_personal = any(word in story_idea.lower() for word in ["i", "my", "me", "we", "our"])
        has_richmond = "richmond" in story_idea.lower() or "rva" in story_idea.lower()
        
        depth_score = 2.0
        if word_count > 20:
            depth_score += 0.5
        if has_personal:
            depth_score += 1.0
        if has_richmond:
            depth_score += 0.5
        
        return {
            "overall_depth_score": min(depth_score, 5.0),
            "dimensions": {
                "narrative_depth": {
                    "score": 3.0 if has_personal else 2.0,
                    "analysis": "Personal connection detected" if has_personal else "Consider adding personal elements"
                },
                "richmond_connection": {
                    "score": 4.0 if has_richmond else 2.0,
                    "analysis": "Richmond context present" if has_richmond else "Add Richmond-specific elements"
                },
                "audience_engagement": {
                    "score": 3.0,
                    "analysis": "Has potential for audience connection"
                },
                "development_potential": {
                    "score": 3.5,
                    "analysis": "Good foundation for story development"
                }
            },
            "recommendations": [
                "Add specific Richmond locations or landmarks",
                "Include personal anecdotes or experiences",
                "Consider the broader community impact"
            ],
            "strengths": ["Clear concept", "Potential for local relevance"],
            "areas_for_improvement": ["Add more specific details", "Deepen personal connection"],
            "suggested_next_steps": ["Share a specific moment", "Connect to Richmond's culture"]
        }
    
    def _extract_themes_simple(self, text: str) -> List[str]:
        """Simple theme extraction without Nova"""
        themes = []
        
        theme_keywords = {
            "community": ["community", "together", "neighbor", "local"],
            "innovation": ["tech", "startup", "innovation", "create", "build"],
            "transformation": ["change", "transform", "grow", "evolve", "become"],
            "heritage": ["history", "tradition", "legacy", "past", "heritage"],
            "resilience": ["overcome", "challenge", "strong", "persist", "resilient"]
        }
        
        text_lower = text.lower()
        for theme, keywords in theme_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                themes.append(theme)
        
        return themes[:3]  # Return top 3 themes
    
    def _calculate_connection_strength(self, anecdote: str) -> float:
        """Calculate strength of personal connection"""
        score = 2.0
        
        # Check for specific details
        if any(char.isdigit() for char in anecdote):  # Has numbers/dates
            score += 0.5
        if len(anecdote.split()) > 50:  # Substantial length
            score += 0.5
        if any(word in anecdote.lower() for word in ["felt", "realized", "moment", "remember"]):
            score += 1.0
        
        return min(score, 5.0)
    
    def _extract_suggestions(self, text: str) -> List[str]:
        """Extract improvement suggestions from text"""
        suggestions = []
        
        # Look for suggestion patterns
        patterns = ["consider", "try", "could", "might", "add", "include"]
        sentences = text.split(".")
        
        for sentence in sentences:
            if any(pattern in sentence.lower() for pattern in patterns):
                suggestions.append(sentence.strip())
        
        return suggestions[:3]
    
    def _default_story_angles(self, story_idea: str) -> List[Dict]:
        """Default story angles when Nova is unavailable"""
        return [
            {
                "hook": "Personal transformation through community connection",
                "perspective": "Individual journey within Richmond's evolving landscape",
                "richmond_connection": "Tie to specific neighborhoods or local initiatives",
                "emotional_resonance": "The feeling of finding your place in a community"
            },
            {
                "hook": "Richmond as a character in your story",
                "perspective": "The city's influence on personal growth and decisions",
                "richmond_connection": "Historic locations that mirror personal journey",
                "emotional_resonance": "Place-based identity and belonging"
            },
            {
                "hook": "Building something new in an old city",
                "perspective": "Innovation rooted in tradition",
                "richmond_connection": "Contrast between historic Richmond and future vision",
                "emotional_resonance": "Hope and possibility in familiar places"
            }
        ]


# Global instance
nova_analyzer = NovaAnalyzer()