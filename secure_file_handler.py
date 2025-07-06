"""
Secure File Upload Handler for Richmond Storyline Generator
Comprehensive file upload security with virus scanning and validation
"""

import os
import uuid
import hashlib
import tempfile
import subprocess
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import magic
import shutil
import json
from datetime import datetime, timedelta
import mimetypes

logger = logging.getLogger(__name__)


class FileSecurityConfig:
    """File security configuration"""
    
    # Storage settings
    UPLOAD_DIRECTORY = os.getenv('UPLOAD_DIRECTORY', './uploads')
    QUARANTINE_DIRECTORY = os.getenv('QUARANTINE_DIRECTORY', './quarantine')
    MAX_STORAGE_SIZE = int(os.getenv('MAX_STORAGE_SIZE', str(1024 * 1024 * 1024)))  # 1GB
    
    # File size limits
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', str(25 * 1024 * 1024)))  # 25MB
    MAX_TOTAL_SIZE_PER_USER = int(os.getenv('MAX_TOTAL_SIZE_PER_USER', str(100 * 1024 * 1024)))  # 100MB
    
    # Allowed file types
    ALLOWED_EXTENSIONS = {
        'documents': ['txt', 'pdf', 'md', 'rtf'],
        'images': ['png', 'jpg', 'jpeg', 'gif', 'webp'],
        'audio': ['mp3', 'wav', 'ogg', 'flac', 'm4a'],
        'data': ['json', 'csv', 'xml']
    }
    
    # Allowed MIME types
    ALLOWED_MIME_TYPES = {
        'text/plain', 'application/pdf', 'text/markdown',
        'image/png', 'image/jpeg', 'image/gif', 'image/webp',
        'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/flac',
        'application/json', 'text/csv', 'application/xml'
    }
    
    # Dangerous file patterns
    DANGEROUS_EXTENSIONS = {
        'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 'jar',
        'app', 'deb', 'pkg', 'dmg', 'iso', 'bin', 'run', 'msi',
        'ps1', 'sh', 'bash', 'zsh', 'fish', 'csh', 'tcsh'
    }
    
    # Virus scanning settings
    ENABLE_VIRUS_SCAN = os.getenv('ENABLE_VIRUS_SCAN', 'true').lower() == 'true'
    CLAMAV_PATH = os.getenv('CLAMAV_PATH', '/usr/bin/clamscan')
    VIRUS_SCAN_TIMEOUT = int(os.getenv('VIRUS_SCAN_TIMEOUT', '30'))
    
    # File retention
    FILE_RETENTION_DAYS = int(os.getenv('FILE_RETENTION_DAYS', '30'))
    TEMP_FILE_RETENTION_HOURS = int(os.getenv('TEMP_FILE_RETENTION_HOURS', '24'))


class VirusScanner:
    """Virus scanning functionality"""
    
    def __init__(self):
        self.clamav_available = self._check_clamav()
        self.scan_enabled = FileSecurityConfig.ENABLE_VIRUS_SCAN and self.clamav_available
        
        if FileSecurityConfig.ENABLE_VIRUS_SCAN and not self.clamav_available:
            logger.warning("⚠️  ClamAV not available - virus scanning disabled")
    
    def _check_clamav(self) -> bool:
        """Check if ClamAV is available"""
        try:
            result = subprocess.run(
                [FileSecurityConfig.CLAMAV_PATH, '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def scan_file(self, file_path: str) -> Dict[str, Any]:
        """
        Scan file for viruses
        
        Args:
            file_path: Path to file to scan
            
        Returns:
            Dict with scan results
        """
        if not self.scan_enabled:
            return {
                'scanned': False,
                'clean': True,
                'message': 'Virus scanning disabled'
            }
        
        try:
            # Run ClamAV scan
            result = subprocess.run(
                [FileSecurityConfig.CLAMAV_PATH, '--stdout', '--no-summary', file_path],
                capture_output=True,
                text=True,
                timeout=FileSecurityConfig.VIRUS_SCAN_TIMEOUT
            )
            
            if result.returncode == 0:
                return {
                    'scanned': True,
                    'clean': True,
                    'message': 'File is clean'
                }
            else:
                # Virus found
                return {
                    'scanned': True,
                    'clean': False,
                    'message': f'Virus detected: {result.stdout.strip()}',
                    'details': result.stdout
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Virus scan timeout for {file_path}")
            return {
                'scanned': False,
                'clean': False,
                'message': 'Virus scan timeout'
            }
        except Exception as e:
            logger.error(f"❌ Virus scan error for {file_path}: {e}")
            return {
                'scanned': False,
                'clean': False,
                'message': f'Virus scan error: {str(e)}'
            }


class SecureFileHandler:
    """Secure file upload and management"""
    
    def __init__(self):
        self.upload_dir = Path(FileSecurityConfig.UPLOAD_DIRECTORY)
        self.quarantine_dir = Path(FileSecurityConfig.QUARANTINE_DIRECTORY)
        self.virus_scanner = VirusScanner()
        
        # Create directories
        self._setup_directories()
    
    def _setup_directories(self):
        """Set up required directories with proper permissions"""
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)
            
            # Set restrictive permissions
            os.chmod(self.upload_dir, 0o750)
            os.chmod(self.quarantine_dir, 0o750)
            
            logger.info(f"✅ Upload directories created: {self.upload_dir}, {self.quarantine_dir}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create upload directories: {e}")
            raise
    
    def validate_file(self, file: FileStorage, user_id: str = None) -> Dict[str, Any]:
        """
        Comprehensive file validation
        
        Args:
            file: Uploaded file
            user_id: User identifier for quota checking
            
        Returns:
            Validation result dictionary
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'metadata': {},
            'security_checks': {}
        }
        
        if not file or not file.filename:
            result['errors'].append("No file provided")
            return result
        
        # Basic file info
        original_filename = file.filename
        file_size = self._get_file_size(file)
        
        result['metadata'] = {
            'original_filename': original_filename,
            'file_size': file_size,
            'upload_timestamp': datetime.utcnow().isoformat()
        }
        
        # File size validation
        if file_size > FileSecurityConfig.MAX_FILE_SIZE:
            result['errors'].append(f"File too large: {file_size} bytes (max: {FileSecurityConfig.MAX_FILE_SIZE})")
            return result
        
        # User quota validation
        if user_id and not self._check_user_quota(user_id, file_size):
            result['errors'].append("User storage quota exceeded")
            return result
        
        # Filename validation
        filename_validation = self._validate_filename(original_filename)
        if not filename_validation['valid']:
            result['errors'].extend(filename_validation['errors'])
            return result
        
        sanitized_filename = filename_validation['sanitized_filename']
        file_extension = filename_validation['extension']
        
        # Extension validation
        if not self._is_extension_allowed(file_extension):
            result['errors'].append(f"File extension not allowed: {file_extension}")
            return result
        
        # MIME type validation
        mime_validation = self._validate_mime_type(file)
        if not mime_validation['valid']:
            result['errors'].extend(mime_validation['errors'])
            return result
        
        # Content validation
        content_validation = self._validate_file_content(file)
        if not content_validation['valid']:
            result['errors'].extend(content_validation['errors'])
            if content_validation['quarantine']:
                result['quarantine'] = True
            return result
        
        # Update metadata
        result['metadata'].update({
            'sanitized_filename': sanitized_filename,
            'file_extension': file_extension,
            'mime_type': mime_validation['mime_type'],
            'file_hash': content_validation['file_hash']
        })
        
        result['security_checks'] = {
            'filename_validation': filename_validation,
            'mime_validation': mime_validation,
            'content_validation': content_validation
        }
        
        result['valid'] = True
        return result
    
    def save_file(self, file: FileStorage, user_id: str, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Securely save uploaded file
        
        Args:
            file: Uploaded file
            user_id: User identifier
            validation_result: File validation result
            
        Returns:
            Save result dictionary
        """
        if not validation_result['valid']:
            return {
                'success': False,
                'error': 'File validation failed',
                'details': validation_result['errors']
            }
        
        try:
            # Generate unique filename
            unique_id = str(uuid.uuid4())
            original_filename = validation_result['metadata']['sanitized_filename']
            file_extension = validation_result['metadata']['file_extension']
            
            stored_filename = f"{unique_id}_{secure_filename(original_filename)}"
            
            # Create user directory
            user_dir = self.upload_dir / user_id
            user_dir.mkdir(exist_ok=True)
            os.chmod(user_dir, 0o750)
            
            # Save file
            file_path = user_dir / stored_filename
            file.save(str(file_path))
            
            # Set restrictive permissions
            os.chmod(file_path, 0o640)
            
            # Virus scan
            scan_result = self.virus_scanner.scan_file(str(file_path))
            
            if not scan_result['clean']:
                # Move to quarantine
                self._quarantine_file(file_path, scan_result)
                return {
                    'success': False,
                    'error': 'File failed security scan',
                    'details': scan_result['message']
                }
            
            # Create file metadata
            metadata = {
                'file_id': unique_id,
                'user_id': user_id,
                'original_filename': original_filename,
                'stored_filename': stored_filename,
                'file_path': str(file_path),
                'file_size': validation_result['metadata']['file_size'],
                'file_hash': validation_result['metadata']['file_hash'],
                'mime_type': validation_result['metadata']['mime_type'],
                'upload_timestamp': validation_result['metadata']['upload_timestamp'],
                'virus_scan_result': scan_result,
                'status': 'active'
            }
            
            # Save metadata
            self._save_file_metadata(metadata)
            
            logger.info(f"✅ File saved successfully: {stored_filename} for user {user_id}")
            
            return {
                'success': True,
                'file_id': unique_id,
                'filename': stored_filename,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Error saving file: {e}")
            return {
                'success': False,
                'error': 'File save failed',
                'details': str(e)
            }
    
    def get_file(self, file_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata and path
        
        Args:
            file_id: File identifier
            user_id: User identifier
            
        Returns:
            File metadata or None
        """
        try:
            metadata = self._load_file_metadata(file_id)
            
            if not metadata:
                return None
            
            # Check user ownership
            if metadata['user_id'] != user_id:
                logger.warning(f"⚠️  Unauthorized file access attempt: {file_id} by user {user_id}")
                return None
            
            # Check if file exists
            file_path = Path(metadata['file_path'])
            if not file_path.exists():
                logger.warning(f"⚠️  File not found: {file_path}")
                return None
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Error retrieving file {file_id}: {e}")
            return None
    
    def delete_file(self, file_id: str, user_id: str) -> bool:
        """
        Delete file securely
        
        Args:
            file_id: File identifier
            user_id: User identifier
            
        Returns:
            True if successful
        """
        try:
            metadata = self.get_file(file_id, user_id)
            if not metadata:
                return False
            
            file_path = Path(metadata['file_path'])
            
            # Secure deletion
            if file_path.exists():
                # Overwrite file with random data before deletion
                self._secure_delete_file(file_path)
            
            # Remove metadata
            self._delete_file_metadata(file_id)
            
            logger.info(f"✅ File deleted successfully: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting file {file_id}: {e}")
            return False
    
    def cleanup_old_files(self) -> int:
        """
        Clean up old files based on retention policy
        
        Returns:
            Number of files cleaned up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=FileSecurityConfig.FILE_RETENTION_DAYS)
            cleaned_count = 0
            
            # Get all file metadata
            metadata_files = self._get_all_metadata_files()
            
            for metadata_file in metadata_files:
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    upload_date = datetime.fromisoformat(metadata['upload_timestamp'])
                    
                    if upload_date < cutoff_date:
                        # Delete file
                        file_path = Path(metadata['file_path'])
                        if file_path.exists():
                            self._secure_delete_file(file_path)
                        
                        # Delete metadata
                        os.remove(metadata_file)
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error processing metadata file {metadata_file}: {e}")
            
            logger.info(f"✅ Cleaned up {cleaned_count} old files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up old files: {e}")
            return 0
    
    def _get_file_size(self, file: FileStorage) -> int:
        """Get file size"""
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)     # Reset to beginning
        return size
    
    def _check_user_quota(self, user_id: str, additional_size: int) -> bool:
        """Check if user has quota for additional file"""
        try:
            user_dir = self.upload_dir / user_id
            if not user_dir.exists():
                return True
            
            total_size = sum(f.stat().st_size for f in user_dir.rglob('*') if f.is_file())
            
            return (total_size + additional_size) <= FileSecurityConfig.MAX_TOTAL_SIZE_PER_USER
            
        except Exception as e:
            logger.error(f"❌ Error checking user quota: {e}")
            return False
    
    def _validate_filename(self, filename: str) -> Dict[str, Any]:
        """Validate and sanitize filename"""
        result = {
            'valid': True,
            'errors': [],
            'sanitized_filename': '',
            'extension': ''
        }
        
        if not filename:
            result['valid'] = False
            result['errors'].append("Empty filename")
            return result
        
        # Get file extension
        parts = filename.lower().split('.')
        extension = parts[-1] if len(parts) > 1 else ''
        
        # Check for dangerous extensions
        if extension in FileSecurityConfig.DANGEROUS_EXTENSIONS:
            result['valid'] = False
            result['errors'].append(f"Dangerous file extension: {extension}")
            return result
        
        # Sanitize filename
        sanitized = secure_filename(filename)
        if not sanitized:
            sanitized = f"file_{int(time.time())}"
        
        result['sanitized_filename'] = sanitized
        result['extension'] = extension
        
        return result
    
    def _is_extension_allowed(self, extension: str) -> bool:
        """Check if file extension is allowed"""
        all_allowed = set()
        for category in FileSecurityConfig.ALLOWED_EXTENSIONS.values():
            all_allowed.update(category)
        
        return extension.lower() in all_allowed
    
    def _validate_mime_type(self, file: FileStorage) -> Dict[str, Any]:
        """Validate MIME type"""
        result = {
            'valid': True,
            'errors': [],
            'mime_type': ''
        }
        
        try:
            # Read first 1KB for MIME detection
            file_content = file.read(1024)
            file.seek(0)  # Reset
            
            mime_type = magic.from_buffer(file_content, mime=True)
            result['mime_type'] = mime_type
            
            if mime_type not in FileSecurityConfig.ALLOWED_MIME_TYPES:
                result['valid'] = False
                result['errors'].append(f"MIME type not allowed: {mime_type}")
            
        except Exception as e:
            logger.error(f"❌ MIME type validation error: {e}")
            result['valid'] = False
            result['errors'].append(f"MIME type validation failed: {str(e)}")
        
        return result
    
    def _validate_file_content(self, file: FileStorage) -> Dict[str, Any]:
        """Validate file content for security"""
        result = {
            'valid': True,
            'errors': [],
            'quarantine': False,
            'file_hash': ''
        }
        
        try:
            # Calculate file hash
            file_hash = hashlib.sha256()
            file.seek(0)
            
            while True:
                chunk = file.read(8192)
                if not chunk:
                    break
                file_hash.update(chunk)
            
            file.seek(0)  # Reset
            result['file_hash'] = file_hash.hexdigest()
            
            # Check for executable signatures
            file_content = file.read(1024)
            file.seek(0)  # Reset
            
            # Check for PE/EXE headers
            if file_content.startswith(b'MZ'):
                result['valid'] = False
                result['quarantine'] = True
                result['errors'].append("Executable file detected")
                return result
            
            # Check for script signatures
            script_signatures = [
                b'#!/bin/sh', b'#!/bin/bash', b'#!/usr/bin/env python',
                b'<script', b'<?php', b'<%'
            ]
            
            for signature in script_signatures:
                if signature in file_content:
                    result['valid'] = False
                    result['quarantine'] = True
                    result['errors'].append("Script content detected")
                    return result
            
        except Exception as e:
            logger.error(f"❌ Content validation error: {e}")
            result['valid'] = False
            result['errors'].append(f"Content validation failed: {str(e)}")
        
        return result
    
    def _quarantine_file(self, file_path: Path, scan_result: Dict[str, Any]):
        """Move file to quarantine"""
        try:
            quarantine_filename = f"quarantine_{int(time.time())}_{file_path.name}"
            quarantine_path = self.quarantine_dir / quarantine_filename
            
            shutil.move(str(file_path), str(quarantine_path))
            
            # Save quarantine metadata
            quarantine_metadata = {
                'original_path': str(file_path),
                'quarantine_path': str(quarantine_path),
                'quarantine_timestamp': datetime.utcnow().isoformat(),
                'scan_result': scan_result
            }
            
            metadata_path = quarantine_path.with_suffix('.metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(quarantine_metadata, f, indent=2)
            
            logger.warning(f"⚠️  File quarantined: {quarantine_filename}")
            
        except Exception as e:
            logger.error(f"❌ Error quarantining file: {e}")
    
    def _save_file_metadata(self, metadata: Dict[str, Any]):
        """Save file metadata"""
        try:
            metadata_dir = self.upload_dir / '.metadata'
            metadata_dir.mkdir(exist_ok=True)
            
            metadata_file = metadata_dir / f"{metadata['file_id']}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            os.chmod(metadata_file, 0o640)
            
        except Exception as e:
            logger.error(f"❌ Error saving metadata: {e}")
    
    def _load_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Load file metadata"""
        try:
            metadata_file = self.upload_dir / '.metadata' / f"{file_id}.json"
            
            if not metadata_file.exists():
                return None
            
            with open(metadata_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"❌ Error loading metadata: {e}")
            return None
    
    def _delete_file_metadata(self, file_id: str):
        """Delete file metadata"""
        try:
            metadata_file = self.upload_dir / '.metadata' / f"{file_id}.json"
            if metadata_file.exists():
                os.remove(metadata_file)
                
        except Exception as e:
            logger.error(f"❌ Error deleting metadata: {e}")
    
    def _get_all_metadata_files(self) -> List[Path]:
        """Get all metadata files"""
        try:
            metadata_dir = self.upload_dir / '.metadata'
            if not metadata_dir.exists():
                return []
            
            return list(metadata_dir.glob('*.json'))
            
        except Exception as e:
            logger.error(f"❌ Error getting metadata files: {e}")
            return []
    
    def _secure_delete_file(self, file_path: Path):
        """Securely delete file by overwriting with random data"""
        try:
            if not file_path.exists():
                return
            
            file_size = file_path.stat().st_size
            
            # Overwrite with random data
            with open(file_path, 'r+b') as f:
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())
            
            # Delete file
            os.remove(file_path)
            
        except Exception as e:
            logger.error(f"❌ Error securely deleting file: {e}")
            # Fallback to regular deletion
            try:
                os.remove(file_path)
            except:
                pass


# Global file handler instance
secure_file_handler = SecureFileHandler()


def get_file_handler() -> SecureFileHandler:
    """Get the global file handler instance"""
    return secure_file_handler


import time