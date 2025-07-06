"""
Voice processing module for handling audio input and transcription
Uses OpenAI's Whisper API for speech-to-text
"""
import os
import logging
import tempfile
import wave
import json
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
import openai
from config import config

logger = logging.getLogger('storygen.voice')


class VoiceProcessor:
    """Handles voice recording processing and transcription"""
    
    def __init__(self):
        """Initialize voice processor with OpenAI API key"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        openai.api_key = self.api_key
        self.supported_formats = ['.wav', '.mp3', '.m4a', '.webm', '.mp4']
        self.max_file_size = 25 * 1024 * 1024  # 25MB limit for Whisper
    
    def validate_audio_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate audio file format and size
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        path = Path(file_path)
        
        # Check if file exists
        if not path.exists():
            return False, "File does not exist"
        
        # Check file extension
        if path.suffix.lower() not in self.supported_formats:
            return False, f"Unsupported format. Supported: {', '.join(self.supported_formats)}"
        
        # Check file size
        file_size = path.stat().st_size
        if file_size > self.max_file_size:
            return False, f"File too large. Maximum size: 25MB, got {file_size / 1024 / 1024:.1f}MB"
        
        # For WAV files, check if they're valid
        if path.suffix.lower() == '.wav':
            try:
                with wave.open(str(path), 'rb') as wav_file:
                    # Just opening it validates the format
                    pass
            except wave.Error as e:
                return False, f"Invalid WAV file: {str(e)}"
        
        return True, None
    
    def transcribe_audio(self, file_path: str, 
                        language: str = "en",
                        prompt: Optional[str] = None) -> Dict[str, any]:
        """
        Transcribe audio file using OpenAI Whisper
        
        Args:
            file_path: Path to audio file
            language: Language code (default: "en" for English)
            prompt: Optional prompt to guide transcription
            
        Returns:
            Dict with transcription results
        """
        # Validate file
        is_valid, error_msg = self.validate_audio_file(file_path)
        if not is_valid:
            raise ValueError(f"Audio validation failed: {error_msg}")
        
        logger.info(f"Transcribing audio file: {file_path}")
        
        try:
            with open(file_path, "rb") as audio_file:
                # Call Whisper API
                response = openai.Audio.transcribe(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    prompt=prompt or "This is a story idea for Richmond, Virginia.",
                    response_format="verbose_json"  # Get detailed response
                )
            
            logger.info(f"Transcription successful. Duration: {response.get('duration', 0):.1f}s")
            
            return {
                "text": response["text"],
                "language": response.get("language", language),
                "duration": response.get("duration", 0),
                "segments": response.get("segments", []),
                "success": True
            }
            
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise ValueError(f"Transcription failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during transcription: {str(e)}")
            raise
    
    def process_audio_upload(self, audio_data: bytes, 
                           filename: str,
                           session_id: str) -> Dict[str, any]:
        """
        Process uploaded audio data
        
        Args:
            audio_data: Raw audio bytes
            filename: Original filename
            session_id: Session ID for storage
            
        Returns:
            Dict with file info and transcription
        """
        # Create temporary file
        file_ext = Path(filename).suffix.lower()
        if file_ext not in self.supported_formats:
            raise ValueError(f"Unsupported audio format: {file_ext}")
        
        # Save to temporary location
        temp_dir = Path(tempfile.gettempdir()) / "storygen_audio"
        temp_dir.mkdir(exist_ok=True)
        
        temp_path = temp_dir / f"{session_id}{file_ext}"
        
        try:
            # Write audio data
            with open(temp_path, 'wb') as f:
                f.write(audio_data)
            
            logger.info(f"Saved audio to temporary file: {temp_path}")
            
            # Transcribe
            transcription = self.transcribe_audio(str(temp_path))
            
            # Add file info
            transcription["file_info"] = {
                "original_filename": filename,
                "size_bytes": len(audio_data),
                "format": file_ext,
                "temp_path": str(temp_path)
            }
            
            return transcription
            
        except Exception as e:
            # Clean up on error
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    def extract_story_context(self, transcription: Dict) -> Dict[str, any]:
        """
        Extract story context from transcription
        
        Analyzes the transcription to identify:
        - Main story idea
        - Emotional tone
        - Key themes
        - Richmond connections
        """
        text = transcription["text"]
        
        # Basic analysis (could be enhanced with NLP)
        context = {
            "full_text": text,
            "word_count": len(text.split()),
            "duration_seconds": transcription.get("duration", 0)
        }
        
        # Check for Richmond mentions
        richmond_keywords = ["Richmond", "RVA", "James River", "VCU", "Fan District", 
                           "Carytown", "Scott's Addition", "Church Hill"]
        richmond_mentions = [kw for kw in richmond_keywords if kw.lower() in text.lower()]
        context["richmond_mentions"] = richmond_mentions
        
        # Detect emotional words
        emotion_indicators = ["feel", "felt", "believe", "love", "hate", "excited", 
                            "worried", "happy", "sad", "proud", "frustrated"]
        emotion_count = sum(1 for word in emotion_indicators if word in text.lower())
        context["emotional_content"] = emotion_count > 2
        
        # Extract potential story themes
        if "community" in text.lower() or "together" in text.lower():
            context["themes"] = context.get("themes", []) + ["community"]
        if "tech" in text.lower() or "startup" in text.lower():
            context["themes"] = context.get("themes", []) + ["technology"]
        if "change" in text.lower() or "transform" in text.lower():
            context["themes"] = context.get("themes", []) + ["transformation"]
        
        return context
    
    def cleanup_temp_files(self, session_id: str):
        """Clean up temporary audio files for a session"""
        temp_dir = Path(tempfile.gettempdir()) / "storygen_audio"
        if temp_dir.exists():
            for file_path in temp_dir.glob(f"{session_id}*"):
                try:
                    file_path.unlink()
                    logger.info(f"Cleaned up temporary file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up {file_path}: {str(e)}")


class AudioStorageManager:
    """Manages audio file storage in S3"""
    
    def __init__(self):
        """Initialize S3 client"""
        import boto3
        self.s3_client = boto3.client('s3', region_name=config.AWS_REGION)
        self.bucket_name = os.getenv("AUDIO_STORAGE_BUCKET", "storygen-audio")
    
    def upload_audio(self, file_path: str, session_id: str, 
                    metadata: Optional[Dict] = None) -> str:
        """
        Upload audio file to S3
        
        Args:
            file_path: Local file path
            session_id: Session ID for organization
            metadata: Optional metadata to attach
            
        Returns:
            S3 URL of uploaded file
        """
        file_ext = Path(file_path).suffix
        s3_key = f"audio/{session_id}/original{file_ext}"
        
        try:
            # Prepare metadata
            s3_metadata = {
                "session_id": session_id,
                "upload_timestamp": str(int(time.time()))
            }
            if metadata:
                s3_metadata.update(metadata)
            
            # Upload file
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    "Metadata": s3_metadata,
                    "ContentType": self._get_content_type(file_ext)
                }
            )
            
            # Generate URL
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Uploaded audio to S3: {s3_url}")
            
            return s3_url
            
        except Exception as e:
            logger.error(f"Failed to upload audio to S3: {str(e)}")
            raise
    
    def _get_content_type(self, file_ext: str) -> str:
        """Get MIME type for file extension"""
        mime_types = {
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.m4a': 'audio/mp4',
            '.webm': 'audio/webm',
            '.mp4': 'audio/mp4'
        }
        return mime_types.get(file_ext.lower(), 'audio/mpeg')
    
    def get_audio_url(self, session_id: str, expiration: int = 3600) -> Optional[str]:
        """
        Get presigned URL for audio file
        
        Args:
            session_id: Session ID
            expiration: URL expiration in seconds
            
        Returns:
            Presigned URL or None if not found
        """
        # Try different extensions
        for ext in ['.wav', '.mp3', '.m4a', '.webm', '.mp4']:
            s3_key = f"audio/{session_id}/original{ext}"
            
            try:
                # Check if object exists
                self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
                
                # Generate presigned URL
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': s3_key},
                    ExpiresIn=expiration
                )
                return url
                
            except self.s3_client.exceptions.NoSuchKey:
                continue
            except Exception as e:
                logger.error(f"Error generating presigned URL: {str(e)}")
                
        return None


# Global instances
voice_processor = VoiceProcessor()
audio_storage = AudioStorageManager()