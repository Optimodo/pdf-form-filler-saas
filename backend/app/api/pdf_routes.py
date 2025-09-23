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

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Header
from fastapi.responses import FileResponse, StreamingResponse
import aiofiles

from ..core.pdf_processor import process_pdf_batch
from ..core.progress_tracker import progress_tracker
from ..core.user_limits import get_user_limits_from_user, get_anonymous_user_limits, validate_file_size
from ..auth import current_active_user
from ..models import User

router = APIRouter(prefix="/api/pdf", tags=["PDF Processing"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_optional_current_user(
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """
    Optional authentication dependency - returns User if authenticated, None if not.
    This allows endpoints to work for both authenticated and anonymous users.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    try:
        # Extract token and validate
        from ..auth import fastapi_users, auth_backend
        strategy = auth_backend.get_strategy()
        token = authorization.replace("Bearer ", "")
        user = await strategy.read_token(token, None)
        if user and user.is_active:
            return user
    except Exception:
        pass
    
    return None


@router.post("/process-batch")
async def process_pdf_batch_endpoint(
    template: UploadFile = File(..., description="PDF template file"),
    csv_data: UploadFile = File(..., description="CSV data file"),
    output_name: Optional[str] = Form(None, description="Custom output directory name"),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Process a batch of PDFs using template and CSV data.
    
    This endpoint uses the exact same logic as the desktop application
    to ensure consistent, compatible PDF output.
    
    File size limits are enforced based on user subscription tier.
    """
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
        
        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp()
        
        # Save uploaded files
        template_path = os.path.join(temp_dir, template.filename)
        csv_path = os.path.join(temp_dir, csv_data.filename)
        
        # Save template file
        async with aiofiles.open(template_path, 'wb') as f:
            content = await template.read()
            await f.write(content)
        
        # Save CSV file
        async with aiofiles.open(csv_path, 'wb') as f:
            content = await csv_data.read()
            await f.write(content)
        
        # Set output directory - use mounted volume for accessibility
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = f"session_{timestamp}"
        output_dir = os.path.join("/app/outputs", session_dir)
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
                zip_filename = f"generated_pdfs_{timestamp}.zip"
                zip_path = os.path.join(output_dir, zip_filename)
                
                try:
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for filename in generated_files:
                            file_path = os.path.join(output_dir, filename)
                            zipf.write(file_path, filename)
                    
                    result["zip_file"] = zip_filename
                    result["zip_path"] = zip_path
                    result["generated_files"] = generated_files
                    
                    logger.info(f"Created ZIP file: {zip_filename} with {len(generated_files)} PDFs")
                    
                except Exception as zip_error:
                    logger.error(f"Failed to create ZIP file: {zip_error}")
                    result["zip_error"] = str(zip_error)
            
            logger.info(f"Batch processing completed: {result['successful_count']} of {result['total_count']} PDFs")
            
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
async def download_generated_zip(zip_filename: str):
    """
    Download a ZIP file containing all generated PDFs.
    
    This provides a single download for all processed PDFs.
    """
    try:
        # Basic filename validation for security
        if '..' in zip_filename or '/' in zip_filename or '\\' in zip_filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        if not zip_filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        # Look for the ZIP file in output directories
        outputs_base = "/app/outputs"
        session_dirs = [d for d in os.listdir(outputs_base) if d.startswith('session_') and os.path.isdir(os.path.join(outputs_base, d))]
        
        zip_path = None
        for session_dir in session_dirs:
            potential_path = os.path.join(outputs_base, session_dir, zip_filename)
            if os.path.exists(potential_path):
                zip_path = potential_path
                break
        
        if not zip_path or not os.path.exists(zip_path):
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

