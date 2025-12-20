"""
PDF Processing API Routes

Provides endpoints for PDF form filling using the proven desktop logic.
"""
import os
import tempfile
import logging
import zipfile
import shutil
import time
from typing import List, Optional
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Header, Request
from fastapi.responses import FileResponse, StreamingResponse
import aiofiles

from ..core.pdf_processor import process_pdf_batch
from ..core.progress_tracker import progress_tracker
from ..core.user_limits import get_user_limits_from_user, get_anonymous_user_limits, validate_file_size
from ..core.file_manager import file_manager
from ..core.activity_logger import activity_logger
from ..auth import current_active_user
from ..models import User
from ..database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/pdf", tags=["PDF Processing"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_optional_current_user(
    request: Request
) -> Optional[User]:
    """
    Optional authentication dependency - returns User if authenticated, None if not.
    This allows endpoints to work for both authenticated and anonymous users.
    """
    logger.info("=== AUTH DEPENDENCY CALLED ===")
    authorization = request.headers.get("Authorization")
    logger.info(f"Authorization header: {authorization}")
    
    if not authorization or not authorization.startswith("Bearer "):
        logger.info("No valid authorization header found")
        return None
    
    try:
        # Use FastAPI-Users dependency system
        from ..auth import fastapi_users, get_user_manager, get_user_db
        from ..database import get_async_session
        
        # Get dependencies
        async for session in get_async_session():
            async for user_db in get_user_db(session):
                async for user_manager in get_user_manager(user_db):
                    # Get the JWT strategy from auth_backend
                    from ..auth import auth_backend
                    strategy = auth_backend.get_strategy()
                    token = authorization.replace("Bearer ", "")
                    logger.info(f"Attempting to validate token: {token[:20]}...")
                    
                    # Validate token and get user
                    user = await strategy.read_token(token, user_manager)
                    if user and user.is_active:
                        logger.info(f"User authenticated successfully: {user.email}")
                        return user
                    else:
                        logger.info("Token validation failed or user inactive")
                        return None
    except Exception as e:
        logger.error(f"Authentication error: {e}")
    
    return None


@router.post("/process-batch")
async def process_pdf_batch_endpoint(
    request: Request,
    template: UploadFile = File(..., description="PDF template file"),
    csv_data: UploadFile = File(..., description="CSV data file"),
    output_name: Optional[str] = Form(None, description="Custom output directory name"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Process a batch of PDFs using template and CSV data.
    
    This endpoint uses the exact same logic as the desktop application
    to ensure consistent, compatible PDF output.
    
    File size limits are enforced based on user subscription tier.
    """
    logger.info(f"=== PROCESSING REQUEST START ===")
    logger.info(f"Processing request - current_user: {current_user.email if current_user else 'None'}")
    logger.info(f"Processing request - current_user type: {type(current_user)}")
    logger.info(f"Processing request - current_user id: {current_user.id if current_user else 'None'}")
    
    temp_dir = None
    try:
        # Validate file types
        if not template.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Template must be a PDF file")
        
        if not csv_data.filename.lower().endswith('.csv'):
            raise HTTPException(status_code=400, detail="Data file must be a CSV file")
        
        # Determine user limits based on authentication status
        if current_user:
            user_limits = get_user_limits_from_user(current_user)
            if current_user.custom_limits_enabled:
                user_type = f"authenticated user ({current_user.subscription_tier} tier + custom limits)"
            else:
                user_type = f"authenticated user ({current_user.subscription_tier} tier)"
        else:
            user_limits = get_anonymous_user_limits()
            user_type = "anonymous user"
        
        logger.info(f"Processing request for {user_type}")
        
        # Validate file sizes
        if template.size:
            is_valid, error_msg = validate_file_size(template.size, user_limits.max_pdf_size, "PDF template")
            if not is_valid:
                raise HTTPException(status_code=413, detail=error_msg)
        
        if csv_data.size:
            is_valid, error_msg = validate_file_size(csv_data.size, user_limits.max_csv_size, "CSV data")
            if not is_valid:
                raise HTTPException(status_code=413, detail=error_msg)
        
        # Store uploaded files with proper naming and database tracking
        template_content = await template.read()
        csv_content = await csv_data.read()
        
        # Store template file
        template_file = await file_manager.store_uploaded_file(
            file_content=template_content,
            original_filename=template.filename,
            file_type='pdf',
            user=current_user,
            session=session
        )
        
        # Store CSV file
        csv_file = await file_manager.store_uploaded_file(
            file_content=csv_content,
            original_filename=csv_data.filename,
            file_type='csv',
            user=current_user,
            session=session
        )
        
        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp()
        
        # Copy stored files to temp directory for processing
        template_path = os.path.join(temp_dir, template.filename)
        csv_path = os.path.join(temp_dir, csv_data.filename)
        
        shutil.copy2(template_file.file_path, template_path)
        shutil.copy2(csv_file.file_path, csv_path)
        
        # Generate session ID with ddmmyyyy format
        session_id = file_manager.generate_session_id(current_user)
        output_dir = os.path.join("/app/storage/outputs", session_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Process PDFs using the proven desktop logic
        logger.info(f"Starting PDF batch processing: {template.filename} with {csv_data.filename}")
        
        # Track processing start time
        processing_start = time.time()
        result = process_pdf_batch(template_path, csv_path, output_dir)
        processing_time = time.time() - processing_start
        
        # Add timing information to result
        result["processing_time"] = processing_time
        if result.get("total_count", 0) > 0:
            result["avg_time_per_file"] = processing_time / result["total_count"]
        
        if result["success"] and result["successful_count"] > 0:
            # List generated files
            generated_files = []
            if os.path.exists(output_dir):
                generated_files = [f for f in os.listdir(output_dir) if f.endswith('.pdf')]
            
            if generated_files:
                # Create ZIP file containing all generated PDFs
                zip_filename = file_manager.generate_zip_filename(session_id, template.filename)
                zip_path = os.path.join(output_dir, zip_filename)
                
                try:
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for filename in generated_files:
                            file_path = os.path.join(output_dir, filename)
                            zipf.write(file_path, filename)
                    
                    result["zip_file"] = zip_filename
                    result["zip_path"] = zip_path
                    result["generated_files"] = generated_files
                    result["session_id"] = session_id
                    
                    logger.info(f"Created ZIP file: {zip_filename} with {len(generated_files)} PDFs")
                    
                    # Clean up individual PDF files after ZIP creation
                    file_manager.cleanup_individual_pdfs(output_dir, generated_files)
                    logger.info(f"Cleaned up {len(generated_files)} individual PDF files")
                    
                except Exception as zip_error:
                    logger.error(f"Failed to create ZIP file: {zip_error}")
                    result["zip_error"] = str(zip_error)
            
            logger.info(f"Batch processing completed: {result['successful_count']} of {result['total_count']} PDFs")
            
        # Extract IP address for logging
        processing_ip = None
        if request:
            req_meta = activity_logger.extract_request_metadata(request)
            processing_ip = req_meta.get("ip_address")
        
        # Create processing job record for tracking and history
        job = await file_manager.create_processing_job_record(
            session=session,
            user=current_user,
            template_file=template_file,
            csv_file=csv_file,
            session_id=session_id,
            result=result,
            processing_ip=processing_ip
        )
        
        # Log the activity
        await activity_logger.log_pdf_processed(
            session=session,
            user_id=current_user.id if current_user else None,
            job_id=job.id,
            pdf_count=result.get('total_count', 0),
            successful_count=result.get('successful_count', 0),
            request=request,
            additional_metadata={
                "template_filename": template_file.original_filename,
                "csv_filename": csv_file.original_filename,
                "processing_time": result.get('processing_time', 0),
            }
        )
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions (like file size errors) without modification
        raise
    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
    finally:
        # Cleanup will happen when temp_dir goes out of scope
        # In production, you might want to schedule cleanup or use a job queue
        pass




@router.get("/download-zip/{zip_filename}")
async def download_generated_zip(
    zip_filename: str,
    session_id: Optional[str] = None
):
    """
    Download a ZIP file containing all generated PDFs.
    
    This provides a single download for all processed PDFs.
    
    Args:
        zip_filename: Name of the ZIP file to download
        session_id: Optional session ID to narrow search (if provided, only searches that directory)
    """
    try:
        # Basic filename validation for security
        if '..' in zip_filename or '/' in zip_filename or '\\' in zip_filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        if not zip_filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        # Look for the ZIP file in output directories
        # Session directories are named with format: sess_ddmmyyyy_HHMMSS_userref
        outputs_base = "/app/storage/outputs"
        
        # Check if outputs_base exists
        if not os.path.exists(outputs_base):
            logger.error(f"Outputs base directory does not exist: {outputs_base}")
            raise HTTPException(status_code=404, detail="Output directory not found")
        
        zip_path = None
        
        # If session_id is provided, check that specific directory first
        if session_id:
            # Validate session_id for security
            if '..' in session_id or '/' in session_id or '\\' in session_id:
                raise HTTPException(status_code=400, detail="Invalid session ID")
            
            specific_dir = os.path.join(outputs_base, session_id)
            if os.path.exists(specific_dir) and os.path.isdir(specific_dir):
                potential_path = os.path.join(specific_dir, zip_filename)
                if os.path.exists(potential_path):
                    zip_path = potential_path
                    logger.info(f"Found ZIP file in specified session directory: {zip_path}")
        
        # If not found and no session_id, or session_id didn't work, search all directories
        if not zip_path:
            # Look for directories starting with 'sess_' (not 'session_')
            try:
                session_dirs = [d for d in os.listdir(outputs_base) 
                              if d.startswith('sess_') and os.path.isdir(os.path.join(outputs_base, d))]
                
                for session_dir in session_dirs:
                    potential_path = os.path.join(outputs_base, session_dir, zip_filename)
                    if os.path.exists(potential_path):
                        zip_path = potential_path
                        logger.info(f"Found ZIP file at: {zip_path}")
                        break
            except Exception as list_error:
                logger.error(f"Error listing output directories: {list_error}")
                raise HTTPException(status_code=500, detail="Error accessing output directory")
        
        # If still not found, log available directories for debugging
        if not zip_path:
            try:
                available_dirs = [d for d in os.listdir(outputs_base) if os.path.isdir(os.path.join(outputs_base, d))]
                logger.warning(f"ZIP file {zip_filename} not found. Available directories: {available_dirs}")
            except:
                pass
            raise HTTPException(status_code=404, detail="ZIP file not found or expired")
        
        # Verify the file exists and is readable
        if not os.path.exists(zip_path) or not os.path.isfile(zip_path):
            raise HTTPException(status_code=404, detail="ZIP file not found or expired")
        
        # Return the ZIP file
        return FileResponse(
            path=zip_path,
            filename=zip_filename,
            media_type='application/zip'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading ZIP file: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"ZIP download failed: {str(e)}")


@router.get("/user-limits")
async def get_user_limits_endpoint(
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Get the file size limits and other restrictions for the current user.
    
    Returns limits based on subscription tier for authenticated users,
    or anonymous user limits for unauthenticated requests.
    """
    try:
        if current_user:
            limits = get_user_limits_from_user(current_user)
            tier = current_user.subscription_tier
            has_custom_limits = current_user.custom_limits_enabled
        else:
            limits = get_anonymous_user_limits()
            tier = "anonymous"
            has_custom_limits = False
        
        from ..core.user_limits import format_file_size
        
        return {
            "subscription_tier": tier,
            "has_custom_limits": has_custom_limits,
            "max_pdf_size_bytes": limits.max_pdf_size,
            "max_csv_size_bytes": limits.max_csv_size,
            "max_pdf_size_display": format_file_size(limits.max_pdf_size),
            "max_csv_size_display": format_file_size(limits.max_csv_size),
            "max_daily_jobs": limits.max_daily_jobs,
            "max_monthly_jobs": limits.max_monthly_jobs,
            "max_files_per_job": limits.max_files_per_job,
            "can_save_templates": limits.can_save_templates,
            "can_use_api": limits.can_use_api,
            "priority_processing": limits.priority_processing,
            "max_saved_templates": limits.max_saved_templates,
            "max_total_storage_mb": limits.max_total_storage_mb,
        }
        
    except Exception as e:
        logger.error(f"Error getting user limits: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user limits: {str(e)}")


@router.get("/progress/{job_id}")
async def get_processing_progress(job_id: str):
    """
    Get the current progress of a PDF processing job.
    
    Returns real-time progress information including:
    - Current file being processed
    - Progress percentage
    - Time estimates
    - Success/error counts
    """
    try:
        progress_data = progress_tracker.get_progress(job_id)
        
        if not progress_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Format time estimates for better display
        if progress_data.get('estimated_remaining'):
            remaining_seconds = progress_data['estimated_remaining']
            if remaining_seconds > 60:
                progress_data['estimated_remaining_display'] = f"{remaining_seconds/60:.1f} minutes"
            else:
                progress_data['estimated_remaining_display'] = f"{remaining_seconds:.0f} seconds"
        
        return progress_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@router.get("/user-files")
async def get_user_uploaded_files(
    file_type: Optional[str] = None,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get all files uploaded by the current user.
    
    Args:
        file_type: Optional filter for 'pdf' or 'csv' files
    """
    try:
        files = await file_manager.get_user_files(session, current_user, file_type)
        
        result = []
        for file in files:
            result.append({
                "id": str(file.id),
                "original_filename": file.original_filename,
                "stored_filename": file.stored_filename,
                "file_type": file.file_type,
                "file_size_bytes": file.file_size_bytes,
                "file_size_display": format_file_size(file.file_size_bytes),
                "uploaded_at": file.uploaded_at.isoformat(),
                "usage_count": file.usage_count,
                "last_used": file.last_used.isoformat() if file.last_used else None
            })
        
        return {
            "files": result,
            "total_count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error getting user files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user files: {str(e)}")


@router.get("/processing-history")
async def get_user_processing_history(
    limit: int = 50,
    current_user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get processing history for the current user.
    
    Args:
        limit: Maximum number of records to return (default 50)
    """
    try:
        jobs = await file_manager.get_user_processing_history(session, current_user, limit)
        
        result = []
        for job in jobs:
            result.append({
                "id": str(job.id),
                "session_id": job.session_id,
                "template_filename": job.template_filename,
                "csv_filename": job.csv_filename,
                "pdf_count": job.pdf_count,
                "successful_count": job.successful_count,
                "failed_count": job.failed_count,
                "processing_time_seconds": job.processing_time_seconds,
                "zip_filename": job.zip_filename,
                "status": job.status,
                "credits_consumed": job.credits_consumed,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            })
        
        return {
            "processing_history": result,
            "total_count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error getting processing history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get processing history: {str(e)}")

