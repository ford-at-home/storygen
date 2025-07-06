"""
Voice API endpoints for audio upload and transcription
"""
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from marshmallow import Schema, fields, ValidationError
from api_utils import handle_errors, log_request, validate_request, APIError, logger
from voice_processor import voice_processor, audio_storage
from session_manager import session_store, Session
from conversation_engine import ConversationEngine
import os
import tempfile

# Create Blueprint
voice_bp = Blueprint('voice', __name__, url_prefix='/voice')

# Initialize conversation engine
conversation_engine = ConversationEngine()

# Request schemas
class VoiceUploadSchema(Schema):
    """Schema for voice upload"""
    session_id = fields.Str(required=False)  # Optional - create new session if not provided
    user_id = fields.Str(required=False)
    language = fields.Str(missing="en")
    save_audio = fields.Bool(missing=True)  # Save to S3


class VoiceTranscribeSchema(Schema):
    """Schema for voice transcription from URL"""
    audio_url = fields.Url(required=True)
    session_id = fields.Str(required=False)
    language = fields.Str(missing="en")


@voice_bp.route('/upload', methods=['POST'])
@handle_errors
@log_request
def upload_voice():
    """Upload and transcribe voice recording"""
    # Check for audio file
    if 'audio' not in request.files:
        raise APIError("No audio file provided", 400)
    
    audio_file = request.files['audio']
    if audio_file.filename == '':
        raise APIError("No file selected", 400)
    
    # Validate other form data
    try:
        # Get form data
        form_data = {
            'session_id': request.form.get('session_id'),
            'user_id': request.form.get('user_id'),
            'language': request.form.get('language', 'en'),
            'save_audio': request.form.get('save_audio', 'true').lower() == 'true'
        }
        
        # Validate with schema
        schema = VoiceUploadSchema()
        data = schema.load(form_data)
    except ValidationError as e:
        return jsonify({
            "error": "Validation error",
            "details": e.messages
        }), 400
    
    # Create or retrieve session
    if data.get('session_id'):
        session = session_store.get(data['session_id'])
        if not session:
            raise APIError("Session not found", 404)
    else:
        # Create new session
        session = Session(user_id=data.get('user_id'))
        logger.info(f"Created new session for voice upload: {session.session_id}")
    
    try:
        # Save uploaded file temporarily
        filename = secure_filename(audio_file.filename)
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, filename)
        audio_file.save(temp_path)
        
        logger.info(f"Saved uploaded audio to: {temp_path}")
        
        # Process and transcribe
        audio_data = open(temp_path, 'rb').read()
        transcription = voice_processor.process_audio_upload(
            audio_data=audio_data,
            filename=filename,
            session_id=session.session_id
        )
        
        # Extract story context
        context = voice_processor.extract_story_context(transcription)
        
        # Save audio to S3 if requested
        s3_url = None
        if data['save_audio']:
            try:
                s3_url = audio_storage.upload_audio(
                    file_path=temp_path,
                    session_id=session.session_id,
                    metadata={
                        'original_filename': filename,
                        'transcription_language': transcription['language'],
                        'duration_seconds': str(transcription['duration'])
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to upload audio to S3: {str(e)}")
        
        # Clean up temp file
        try:
            os.unlink(temp_path)
            os.rmdir(temp_dir)
        except:
            pass
        
        # Process transcription through conversation engine
        from conversation_engine import ConversationStage
        response = conversation_engine.process_turn(
            session=session,
            user_input=transcription['text'],
            stage=ConversationStage.KICKOFF
        )
        
        # Save session
        session_store.save(session)
        
        return jsonify({
            "session_id": session.session_id,
            "transcription": {
                "text": transcription['text'],
                "language": transcription['language'],
                "duration": transcription['duration'],
                "word_count": context['word_count']
            },
            "context_analysis": {
                "richmond_mentions": context.get('richmond_mentions', []),
                "emotional_content": context.get('emotional_content', False),
                "themes": context.get('themes', [])
            },
            "conversation_response": response,
            "audio_stored": s3_url is not None,
            "s3_url": s3_url
        })
        
    except ValueError as e:
        logger.error(f"Voice processing error: {str(e)}")
        raise APIError(str(e), 400)
    except Exception as e:
        logger.error(f"Unexpected error processing voice: {str(e)}")
        raise APIError("Failed to process voice recording", 500)
    finally:
        # Clean up any remaining temp files
        voice_processor.cleanup_temp_files(session.session_id)


@voice_bp.route('/transcribe-url', methods=['POST'])
@handle_errors
@log_request
@validate_request(VoiceTranscribeSchema)
def transcribe_from_url():
    """Transcribe audio from a URL"""
    data = request.validated_data
    
    # This endpoint would be used for audio files already stored
    # Implementation would download from URL and transcribe
    # For now, return not implemented
    raise APIError("URL transcription not yet implemented", 501)


@voice_bp.route('/session/<session_id>/audio', methods=['GET'])
@handle_errors
@log_request
def get_session_audio(session_id):
    """Get audio URL for a session"""
    # Verify session exists
    session = session_store.get(session_id)
    if not session:
        raise APIError("Session not found", 404)
    
    try:
        # Get presigned URL
        audio_url = audio_storage.get_audio_url(session_id)
        
        if audio_url:
            return jsonify({
                "session_id": session_id,
                "audio_url": audio_url,
                "expires_in": 3600  # 1 hour
            })
        else:
            raise APIError("No audio found for this session", 404)
            
    except Exception as e:
        logger.error(f"Failed to get audio URL: {str(e)}")
        raise APIError("Failed to retrieve audio", 500)


@voice_bp.route('/supported-formats', methods=['GET'])
def get_supported_formats():
    """Get list of supported audio formats"""
    return jsonify({
        "formats": voice_processor.supported_formats,
        "max_file_size_mb": 25,
        "supported_languages": ["en"],  # Could be expanded
        "notes": {
            "wav": "Recommended for best quality",
            "mp3": "Good compression, widely supported",
            "m4a": "Apple devices default",
            "webm": "Web recordings",
            "mp4": "Video files with audio"
        }
    })


# Error handlers specific to voice endpoints
@voice_bp.errorhandler(413)
def file_too_large(error):
    """Handle file too large errors"""
    return jsonify({
        "error": "File too large",
        "message": "Audio file must be less than 25MB",
        "max_size_mb": 25
    }), 413