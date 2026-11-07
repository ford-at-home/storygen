"""
API endpoints for advanced story features
"""
from flask import Blueprint, request, jsonify, send_file
from marshmallow import Schema, fields, ValidationError
from api_utils import handle_errors, log_request, validate_request, APIError, logger
from story_features import (
    template_manager, story_enhancer, story_exporter, version_manager,
    StoryTemplate
)
from session_manager import session_store
import io

# Create Blueprint
features_bp = Blueprint('features', __name__, url_prefix='/features')


# Request schemas
class ApplyTemplateSchema(Schema):
    """Schema for applying a story template"""
    session_id = fields.Str(required=True)
    template_id = fields.Str(required=True, validate=lambda x: x in [t.value for t in StoryTemplate])


class EnhanceStorySchema(Schema):
    """Schema for story enhancement"""
    session_id = fields.Str(required=True)
    enhancement_type = fields.Str(required=False)
    analyze_only = fields.Bool(missing=False)


class ExportStorySchema(Schema):
    """Schema for story export"""
    session_id = fields.Str(required=True)
    format = fields.Str(missing="markdown", validate=lambda x: x in ["markdown", "html", "json", "pdf"])
    include_metadata = fields.Bool(missing=True)


class SaveVersionSchema(Schema):
    """Schema for saving story version"""
    session_id = fields.Str(required=True)
    content = fields.Str(required=True)
    metadata = fields.Dict(missing={})


@features_bp.route('/templates', methods=['GET'])
@handle_errors
@log_request
def get_templates():
    """Get all available story templates"""
    templates = template_manager.get_all_templates()
    
    return jsonify({
        "templates": templates,
        "total": len(templates),
        "description": "Pre-defined story structures to guide narrative development"
    })


@features_bp.route('/templates/<template_id>', methods=['GET'])
@handle_errors
@log_request
def get_template_details(template_id):
    """Get detailed information about a specific template"""
    try:
        template_type = StoryTemplate(template_id)
        template = template_manager.get_template(template_type)
        
        if not template:
            raise APIError("Template not found", 404)
        
        return jsonify({
            "template_id": template_id,
            "details": template
        })
        
    except ValueError:
        raise APIError("Invalid template ID", 400)


@features_bp.route('/apply-template', methods=['POST'])
@handle_errors
@log_request
@validate_request(ApplyTemplateSchema)
def apply_template():
    """Apply a template to a session"""
    data = request.validated_data
    
    # Get session
    session = session_store.get(data['session_id'])
    if not session:
        raise APIError("Session not found", 404)
    
    try:
        # Apply template
        template_type = StoryTemplate(data['template_id'])
        template_guidance = template_manager.apply_template(
            session.to_dict(),
            template_type
        )
        
        # Store template choice in session metadata
        session.metadata['selected_template'] = data['template_id']
        session.metadata['template_guidance'] = template_guidance
        session_store.save(session)
        
        return jsonify({
            "session_id": data['session_id'],
            "template_applied": data['template_id'],
            "guidance": template_guidance,
            "next_action": "Use guided prompts to develop your story"
        })
        
    except Exception as e:
        logger.error(f"Failed to apply template: {str(e)}")
        raise APIError("Failed to apply template", 500)


@features_bp.route('/enhance', methods=['POST'])
@handle_errors
@log_request
@validate_request(EnhanceStorySchema)
def enhance_story():
    """Analyze or enhance a story"""
    data = request.validated_data
    
    # Get session
    session = session_store.get(data['session_id'])
    if not session:
        raise APIError("Session not found", 404)
    
    # Get the story
    story = session.story_elements.final_story
    if not story:
        raise APIError("No final story found in session", 400)
    
    try:
        if data['analyze_only']:
            # Just analyze and suggest enhancements
            suggestions = story_enhancer.suggest_enhancements(story)
            
            return jsonify({
                "session_id": data['session_id'],
                "suggestions": suggestions,
                "total_suggestions": len(suggestions),
                "priority_high": len([s for s in suggestions if s['priority'] == 'high'])
            })
        else:
            # Apply specific enhancement
            enhancement_type = data.get('enhancement_type')
            if not enhancement_type:
                raise APIError("Enhancement type required when analyze_only is false", 400)
            
            enhanced_story = story_enhancer.apply_enhancement(story, enhancement_type)
            
            # Save as new version
            version_id = version_manager.save_version(
                data['session_id'],
                enhanced_story,
                {"enhancement_type": enhancement_type}
            )
            
            return jsonify({
                "session_id": data['session_id'],
                "enhancement_applied": enhancement_type,
                "version_id": version_id,
                "enhanced_story": enhanced_story
            })
            
    except Exception as e:
        logger.error(f"Failed to enhance story: {str(e)}")
        raise APIError("Failed to enhance story", 500)


@features_bp.route('/export', methods=['POST'])
@handle_errors
@log_request
@validate_request(ExportStorySchema)
def export_story():
    """Export story in various formats"""
    data = request.validated_data
    
    # Get session
    session = session_store.get(data['session_id'])
    if not session:
        raise APIError("Session not found", 404)
    
    # Check for final story
    if not session.story_elements.final_story:
        raise APIError("No final story to export", 400)
    
    try:
        # Prepare story data
        story_data = {
            "title": f"Richmond Story - {session.created_at.strftime('%B %d, %Y')}",
            "story": session.story_elements.final_story,
            "core_idea": session.story_elements.core_idea,
            "hook": session.story_elements.selected_hook,
            "quote": session.story_elements.richmond_quote,
            "cta": session.story_elements.selected_cta,
            "style": session.metadata.get('style', 'short_post')
        }
        
        # Export in requested format
        exported_content = story_exporter.export_story(
            data['session_id'],
            story_data,
            data['format']
        )
        
        # Return appropriate response based on format
        if data['format'] == 'json':
            return jsonify(json.loads(exported_content))
        else:
            # Return as downloadable file
            filename = f"richmond_story_{data['session_id'][:8]}.{data['format']}"
            
            if data['format'] == 'html':
                mimetype = 'text/html'
            elif data['format'] == 'markdown':
                mimetype = 'text/markdown'
            else:
                mimetype = 'text/plain'
            
            return send_file(
                io.BytesIO(exported_content.encode('utf-8')),
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )
            
    except Exception as e:
        logger.error(f"Failed to export story: {str(e)}")
        raise APIError("Failed to export story", 500)


@features_bp.route('/versions', methods=['POST'])
@handle_errors
@log_request
@validate_request(SaveVersionSchema)
def save_version():
    """Save a version of a story"""
    data = request.validated_data
    
    # Verify session exists
    session = session_store.get(data['session_id'])
    if not session:
        raise APIError("Session not found", 404)
    
    try:
        # Save version
        version_id = version_manager.save_version(
            data['session_id'],
            data['content'],
            data['metadata']
        )
        
        return jsonify({
            "session_id": data['session_id'],
            "version_id": version_id,
            "message": "Version saved successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to save version: {str(e)}")
        raise APIError("Failed to save version", 500)


@features_bp.route('/versions/<session_id>', methods=['GET'])
@handle_errors
@log_request
def get_versions(session_id):
    """Get all versions for a session"""
    # Verify session exists
    session = session_store.get(session_id)
    if not session:
        raise APIError("Session not found", 404)
    
    versions = version_manager.get_versions(session_id)
    
    return jsonify({
        "session_id": session_id,
        "versions": versions,
        "total": len(versions)
    })


@features_bp.route('/versions/<session_id>/<version_id>', methods=['GET'])
@handle_errors
@log_request
def get_version(session_id, version_id):
    """Get a specific version"""
    version = version_manager.get_version(session_id, version_id)
    
    if not version:
        raise APIError("Version not found", 404)
    
    return jsonify({
        "session_id": session_id,
        "version": version
    })


@features_bp.route('/versions/compare', methods=['POST'])
@handle_errors
@log_request
def compare_versions():
    """Compare two versions"""
    data = request.get_json()
    
    if not all(k in data for k in ['session_id', 'version_id1', 'version_id2']):
        raise APIError("Missing required fields", 400)
    
    comparison = version_manager.compare_versions(
        data['session_id'],
        data['version_id1'],
        data['version_id2']
    )
    
    if 'error' in comparison:
        raise APIError(comparison['error'], 404)
    
    return jsonify(comparison)


@features_bp.route('/preview-export', methods=['POST'])
@handle_errors
@log_request
def preview_export():
    """Preview how a story will look when exported"""
    data = request.get_json()
    
    if 'content' not in data:
        raise APIError("Content required for preview", 400)
    
    format = data.get('format', 'markdown')
    if format not in story_exporter.supported_formats:
        raise APIError(f"Unsupported format: {format}", 400)
    
    # Create temporary story data
    story_data = {
        "title": data.get('title', 'Richmond Story Preview'),
        "story": data['content'],
        "core_idea": data.get('core_idea', ''),
        "hook": data.get('hook', ''),
        "quote": data.get('quote', ''),
        "cta": data.get('cta', '')
    }
    
    try:
        preview = story_exporter.export_story('preview', story_data, format)
        
        return jsonify({
            "format": format,
            "preview": preview if format == 'json' else preview[:1000] + '...' if len(preview) > 1000 else preview
        })
        
    except Exception as e:
        logger.error(f"Failed to generate preview: {str(e)}")
        raise APIError("Failed to generate preview", 500)