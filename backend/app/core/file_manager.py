"""
File Management System for PDF Form Filler SaaS

Handles file storage, naming, organization, and cleanup with user linking.
"""
import os
import hashlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import User, UploadedFile, ProcessingJob
from ..database import get_async_session


class FileManager:
    """Manages file storage and organization for the PDF processing system."""
    
    def __init__(self):
        self.base_storage_path = Path("/app/storage")
        self.templates_path = self.base_storage_path / "templates"
        self.csv_files_path = self.base_storage_path / "csv_files"
        self.outputs_path = self.base_storage_path / "outputs"
        
        # Create directories if they don't exist
        for path in [self.templates_path, self.csv_files_path, self.outputs_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def validate_filename_security(self, filename: str) -> Tuple[bool, str]:
        """
        Validate filename for security issues.
        
        Returns:
            (is_valid, error_message)
        """
        # Check for path traversal attempts
        dangerous_patterns = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for pattern in dangerous_patterns:
            if pattern in filename:
                return False, f"Filename contains dangerous characters: {pattern}"
        
        # Check for extremely long filenames
        if len(filename) > 255:  # Filesystem limit
            return False, "Filename too long (max 255 characters)"
        
        # Check for empty or only whitespace
        if not filename.strip():
            return False, "Filename cannot be empty"
        
        # Check for reserved names (Windows)
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                         'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
                         'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            return False, f"Filename uses reserved system name: {name_without_ext}"
        
        return True, ""

    def generate_filename(self, original_filename: str, file_type: str, user: Optional[User] = None) -> str:
        """
        Generate a standardized filename with ddmmyyyy format.
        
        Format: ddmmyyyy_HHMMSS_[userref].[ext]
        Example: 27092025_143022_user123.pdf
        
        Original filename is stored in database for user display.
        This keeps filesystem names short and predictable.
        """
        now = datetime.now()
        date_str = now.strftime("%d%m%Y")  # ddmmyyyy format as requested
        time_str = now.strftime("%H%M%S")
        
        # Get file extension and validate it
        extension = Path(original_filename).suffix.lower()
        allowed_extensions = ['.pdf', '.csv']
        if extension not in allowed_extensions:
            extension = '.pdf' if file_type == 'pdf' else '.csv'
        
        # User reference (shortened for filesystem)
        if user:
            user_ref = str(user.id)[:8]  # First 8 chars of UUID only
        else:
            user_ref = "anon"
        
        # Generate short filename: ddmmyyyy_HHMMSS_userref.ext
        filename = f"{date_str}_{time_str}_{user_ref}{extension}"
        
        # Ensure filename doesn't exceed 150 characters (safe limit)
        if len(filename) > 150:
            # Truncate user_ref if needed, but keep date/time intact
            max_user_ref_len = 150 - len(f"{date_str}_{time_str}_") - len(extension)
            user_ref = user_ref[:max_user_ref_len]
            filename = f"{date_str}_{time_str}_{user_ref}{extension}"
        
        return filename
    
    def get_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file for deduplication."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    async def store_uploaded_file(
        self, 
        file_content: bytes, 
        original_filename: str, 
        file_type: str,
        user: Optional[User] = None,
        session: Optional[AsyncSession] = None,
        upload_ip: Optional[str] = None
    ) -> UploadedFile:
        """
        Store an uploaded file and create database record.
        
        Args:
            file_content: The file content as bytes
            original_filename: Original filename from upload
            file_type: 'pdf' or 'csv'
            user: User object if authenticated
            session: Database session
            upload_ip: IP address for anonymous tracking
        
        Returns:
            UploadedFile database record
        
        Raises:
            ValueError: If file validation fails
        """
        # Validate filename security first (this should be caught by frontend, but double-check)
        is_valid, error_msg = self.validate_filename_security(original_filename)
        if not is_valid:
            raise ValueError(f"Invalid filename: {error_msg}. Please rename your file and try again.")
        
        # Validate file content
        is_valid, error_msg = self.validate_file_content(file_content, file_type)
        if not is_valid:
            raise ValueError(f"File validation failed: {error_msg}")
        
        # Generate standardized filename
        stored_filename = self.generate_filename(original_filename, file_type, user)
        
        # Determine storage path
        if file_type == 'pdf':
            storage_dir = self.templates_path
        elif file_type == 'csv':
            storage_dir = self.csv_files_path
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        file_path = storage_dir / stored_filename
        
        # Write file to storage
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Calculate file hash
        file_hash = self.get_file_hash(str(file_path))
        
        # Create database record
        uploaded_file = UploadedFile(
            user_id=user.id if user else None,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            file_type=file_type,
            file_size_bytes=len(file_content),
            file_hash=file_hash,
            upload_ip=upload_ip,
            mime_type=self._get_mime_type(original_filename)
        )
        
        if session:
            session.add(uploaded_file)
            await session.commit()
            await session.refresh(uploaded_file)
        
        return uploaded_file
    
    def validate_file_content(self, file_content: bytes, expected_type: str) -> Tuple[bool, str]:
        """
        Validate file content matches expected type.
        
        Args:
            file_content: File content as bytes
            expected_type: 'pdf' or 'csv'
        
        Returns:
            (is_valid, error_message)
        """
        if not file_content:
            return False, "File is empty"
        
        # Check file size limits
        max_sizes = {
            'pdf': 10 * 1024 * 1024,  # 10MB
            'csv': 5 * 1024 * 1024    # 5MB
        }
        
        if len(file_content) > max_sizes.get(expected_type, 10 * 1024 * 1024):
            return False, f"File too large (max {max_sizes[expected_type] // (1024*1024)}MB)"
        
        # Validate file signatures (magic numbers)
        if expected_type == 'pdf':
            # PDF files start with %PDF
            if not file_content.startswith(b'%PDF'):
                return False, "File does not appear to be a valid PDF"
        
        elif expected_type == 'csv':
            # CSV files should be text and contain common delimiters
            try:
                # Try to decode as text
                text_content = file_content.decode('utf-8', errors='ignore')
                # Check for common CSV delimiters
                if not any(delim in text_content for delim in [',', ';', '\t']):
                    return False, "File does not appear to be a valid CSV (no delimiters found)"
            except UnicodeDecodeError:
                return False, "File does not appear to be valid text (CSV)"
        
        return True, ""

    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type based on file extension."""
        ext = Path(filename).suffix.lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.csv': 'text/csv'
        }
        return mime_types.get(ext, 'application/octet-stream')
    
    def generate_session_id(self, user: Optional[User] = None) -> str:
        """Generate a session ID for processing jobs."""
        now = datetime.now()
        date_str = now.strftime("%d%m%Y_%H%M%S")  # ddmmyyyy_HHMMSS format
        
        if user:
            user_ref = str(user.id)[:8]
            return f"sess_{date_str}_{user_ref}"
        else:
            return f"sess_{date_str}_anon"
    
    def generate_zip_filename(self, session_id: str, template_name: str = None) -> str:
        """Generate user-friendly ZIP filename."""
        # Extract date and time from session_id (format: sess_ddmmyyyy_HHMMSS_userref)
        parts = session_id.split('_')
        if len(parts) >= 3:
            date_part = parts[1]  # ddmmyyyy
            time_part = parts[2]  # HHMMSS
            
            if template_name:
                # Clean template name for filename (remove extension, limit length)
                clean_name = Path(template_name).stem
                clean_name = "".join(c for c in clean_name if c.isalnum() or c in '_-')[:20]
                # Format: MVHR_PDFs_27092025_143022.zip
                return f"{clean_name}_PDFs_{date_part}_{time_part}.zip"
            else:
                # Format: PDFs_27092025_143022.zip (more user-friendly)
                return f"PDFs_{date_part}_{time_part}.zip"
        else:
            # Fallback to original format if parsing fails
            return f"generated_pdfs_{session_id}.zip"
    
    def cleanup_individual_pdfs(self, output_dir: str, generated_files: list) -> None:
        """
        Delete individual PDF files after ZIP creation.
        
        Args:
            output_dir: Directory containing the files
            generated_files: List of PDF filenames to delete
        """
        for filename in generated_files:
            if filename.endswith('.pdf'):
                file_path = os.path.join(output_dir, filename)
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Deleted individual PDF: {filename}")
                except Exception as e:
                    print(f"Failed to delete {filename}: {e}")
    
    async def create_processing_job_record(
        self,
        session: AsyncSession,
        user: Optional[User],
        template_file: UploadedFile,
        csv_file: UploadedFile,
        session_id: str,
        result: dict,
        processing_ip: Optional[str] = None
    ) -> ProcessingJob:
        """Create a processing job record in the database."""
        
        # Calculate credits consumed
        credits_consumed = 0
        if user:
            # You can implement credit calculation logic here
            # For now, let's say 1 credit per successful PDF
            credits_consumed = result.get('successful_count', 0)
        
        job = ProcessingJob(
            user_id=user.id if user else None,
            template_file_id=template_file.id,
            csv_file_id=csv_file.id,
            template_filename=template_file.original_filename,
            csv_filename=csv_file.original_filename,
            pdf_count=result.get('total_count', 0),
            successful_count=result.get('successful_count', 0),
            failed_count=result.get('failed_count', 0),
            processing_time_seconds=str(result.get('processing_time', 0)),
            zip_filename=result.get('zip_file'),
            zip_file_path=result.get('zip_path'),
            status='completed' if result.get('success') else 'failed',
            error_message=result.get('error_message'),
            credits_consumed=credits_consumed,
            session_id=session_id,
            processing_ip=processing_ip,
            completed_at=datetime.now()
        )
        
        session.add(job)
        await session.commit()
        await session.refresh(job)
        
        # Update file usage counts
        template_file.usage_count += 1
        template_file.last_used = datetime.now()
        csv_file.usage_count += 1
        csv_file.last_used = datetime.now()
        
        await session.commit()
        
        return job
    
    async def get_user_files(
        self, 
        session: AsyncSession, 
        user: User, 
        file_type: Optional[str] = None
    ) -> list[UploadedFile]:
        """Get all files uploaded by a user."""
        query = select(UploadedFile).where(UploadedFile.user_id == user.id)
        
        if file_type:
            query = query.where(UploadedFile.file_type == file_type)
        
        query = query.order_by(UploadedFile.uploaded_at.desc())
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def get_user_processing_history(
        self,
        session: AsyncSession,
        user: User,
        limit: int = 50
    ) -> list[ProcessingJob]:
        """Get processing history for a user."""
        query = (select(ProcessingJob)
                .where(ProcessingJob.user_id == user.id)
                .order_by(ProcessingJob.created_at.desc())
                .limit(limit))
        
        result = await session.execute(query)
        return result.scalars().all()


# Global file manager instance
file_manager = FileManager()

