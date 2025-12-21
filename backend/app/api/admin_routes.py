"""
Admin API Routes

Provides endpoints for administrative functions including:
- User management
- Subscription management
- System analytics
- Custom limits management
"""
import json
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, and_, cast, Float
from sqlalchemy.orm import selectinload
import os

from fastapi import Request

from ..auth import current_superuser
from ..models import User, ProcessingJob, UploadedFile, UserTemplate
from ..database import get_async_session
from ..core.admin_utils import (
    set_custom_user_limits,
    remove_custom_user_limits,
    get_user_limits_summary,
    apply_custom_limit_template,
    CUSTOM_LIMIT_TEMPLATES
)
from ..core.user_limits import format_file_size, refresh_tier_cache
from ..models import SubscriptionTier
from ..core.activity_logger import activity_logger

router = APIRouter(prefix="/api/admin", tags=["Admin"])

logger = logging.getLogger(__name__)


# Admin dependency - ensures user is superuser
async def get_current_admin(
    current_user: User = Depends(current_superuser)
) -> User:
    """Dependency to ensure the current user is an admin/superuser."""
    return current_user


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get overall system statistics for admin dashboard.
    
    Returns:
        Statistics including user counts, job counts, storage usage, etc.
    """
    try:
        # Total users
        total_users_result = await session.execute(
            select(func.count(User.id))
        )
        total_users = total_users_result.scalar() or 0
        
        # Active users (logged in within last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_users_result = await session.execute(
            select(func.count(User.id)).where(
                User.last_login >= thirty_days_ago
            )
        )
        active_users = active_users_result.scalar() or 0
        
        # Users by subscription tier
        tier_counts_result = await session.execute(
            select(User.subscription_tier, func.count(User.id))
            .group_by(User.subscription_tier)
        )
        users_by_tier = {tier: count for tier, count in tier_counts_result.all()}
        
        # Total processing jobs
        total_jobs_result = await session.execute(
            select(func.count(ProcessingJob.id))
        )
        total_jobs = total_jobs_result.scalar() or 0
        
        # Successful jobs
        successful_jobs_result = await session.execute(
            select(func.count(ProcessingJob.id))
            .where(ProcessingJob.status == 'completed')
        )
        successful_jobs = successful_jobs_result.scalar() or 0
        
        # Total PDFs processed
        total_pdfs_result = await session.execute(
            select(func.sum(ProcessingJob.successful_count))
        )
        total_pdfs = total_pdfs_result.scalar() or 0
        
        # Input file storage (templates and CSV files)
        input_storage_result = await session.execute(
            select(func.sum(UploadedFile.file_size_bytes))
        )
        input_storage_bytes = input_storage_result.scalar() or 0
        
        # Output file storage (PDF ZIP files)
        # Sum up file_size_mb from ProcessingJob and convert to bytes
        # Note: file_size_mb is stored as string, so we need to cast it
        output_storage_result = await session.execute(
            select(func.sum(cast(ProcessingJob.file_size_mb, Float)))
            .where(ProcessingJob.file_size_mb.isnot(None))
        )
        output_storage_mb = output_storage_result.scalar() or 0
        output_storage_bytes = int(output_storage_mb * 1024 * 1024) if output_storage_mb else 0
        
        # Total storage
        total_storage_bytes = input_storage_bytes + output_storage_bytes
        
        # Recent activity (last 24 hours)
        from datetime import datetime, timedelta
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_jobs_result = await session.execute(
            select(func.count(ProcessingJob.id))
            .where(ProcessingJob.created_at >= last_24h)
        )
        recent_jobs = recent_jobs_result.scalar() or 0
        
        # Analytics by tier: Jobs count
        jobs_by_tier_result = await session.execute(
            select(User.subscription_tier, func.count(ProcessingJob.id))
            .join(ProcessingJob, User.id == ProcessingJob.user_id)
            .group_by(User.subscription_tier)
        )
        jobs_by_tier = {tier: count for tier, count in jobs_by_tier_result.all()}
        
        # Anonymous jobs count
        anonymous_jobs_result = await session.execute(
            select(func.count(ProcessingJob.id))
            .where(ProcessingJob.user_id.is_(None))
        )
        anonymous_jobs = anonymous_jobs_result.scalar() or 0
        if anonymous_jobs > 0:
            jobs_by_tier['anonymous'] = anonymous_jobs
        
        # Analytics by tier: PDFs processed
        pdfs_by_tier_result = await session.execute(
            select(User.subscription_tier, func.sum(ProcessingJob.successful_count))
            .join(ProcessingJob, User.id == ProcessingJob.user_id)
            .group_by(User.subscription_tier)
        )
        pdfs_by_tier = {tier: (count or 0) for tier, count in pdfs_by_tier_result.all()}
        
        # Anonymous PDFs processed
        anonymous_pdfs_result = await session.execute(
            select(func.sum(ProcessingJob.successful_count))
            .where(ProcessingJob.user_id.is_(None))
        )
        anonymous_pdfs = anonymous_pdfs_result.scalar() or 0
        if anonymous_pdfs > 0:
            pdfs_by_tier['anonymous'] = anonymous_pdfs
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "by_tier": users_by_tier
            },
            "jobs": {
                "total": total_jobs,
                "successful": successful_jobs,
                "recent_24h": recent_jobs,
                "by_tier": jobs_by_tier
            },
            "processing": {
                "total_pdfs": total_pdfs or 0,
                "pdfs_by_tier": pdfs_by_tier
            },
            "storage": {
                "input_bytes": input_storage_bytes,
                "input_display": format_file_size(input_storage_bytes),
                "output_bytes": output_storage_bytes,
                "output_display": format_file_size(output_storage_bytes),
                "total_bytes": total_storage_bytes,
                "total_display": format_file_size(total_storage_bytes)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")


@router.get("/users")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    min_credits_used: Optional[int] = Query(None, description="Minimum lifetime credits used"),
    max_credits_used: Optional[int] = Query(None, description="Maximum lifetime credits used"),
    min_credits_remaining: Optional[int] = Query(None, description="Minimum remaining credits"),
    max_credits_remaining: Optional[int] = Query(None, description="Maximum remaining credits"),
    min_job_count: Optional[int] = Query(None, description="Minimum total PDF runs"),
    max_job_count: Optional[int] = Query(None, description="Maximum total PDF runs"),
    sort_by: Optional[str] = Query(None, description="Field to sort by (credits_used_total, credits_remaining, total_pdf_runs, created_at)"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    List all users with pagination and filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        search: Search term for email/name
        tier: Filter by subscription tier
        min_credits_used: Minimum lifetime credits used
        max_credits_used: Maximum lifetime credits used
        min_credits_remaining: Minimum remaining credits
        max_credits_remaining: Maximum remaining credits
        min_job_count: Minimum total PDF runs
        max_job_count: Maximum total PDF runs
    """
    try:
        query = select(User)
        
        # Apply text search filter
        if search:
            search_term = f"%{search}%"
            query = query.where(
                (User.email.ilike(search_term)) |
                (User.first_name.ilike(search_term)) |
                (User.last_name.ilike(search_term))
            )
        
        # Apply tier filter
        if tier:
            query = query.where(User.subscription_tier == tier)
        
        # Apply numeric filters
        if min_credits_used is not None:
            query = query.where(User.credits_used_total >= min_credits_used)
        if max_credits_used is not None:
            query = query.where(User.credits_used_total <= max_credits_used)
        if min_credits_remaining is not None:
            query = query.where(User.credits_remaining >= min_credits_remaining)
        if max_credits_remaining is not None:
            query = query.where(User.credits_remaining <= max_credits_remaining)
        if min_job_count is not None:
            query = query.where(User.total_pdf_runs >= min_job_count)
        if max_job_count is not None:
            query = query.where(User.total_pdf_runs <= max_job_count)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply sorting
        if sort_by:
            sort_field = None
            if sort_by == "credits_used_total":
                sort_field = User.credits_used_total
            elif sort_by == "credits_remaining":
                sort_field = User.credits_remaining
            elif sort_by == "total_pdf_runs":
                sort_field = User.total_pdf_runs
            elif sort_by == "created_at":
                sort_field = User.created_at
            
            if sort_field:
                if sort_order and sort_order.lower() == "asc":
                    query = query.order_by(sort_field)
                else:
                    query = query.order_by(desc(sort_field))
            else:
                # Default to created_at if invalid sort_by
                query = query.order_by(desc(User.created_at))
        else:
            # Default ordering by created_at
            query = query.order_by(desc(User.created_at))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await session.execute(query)
        users = result.scalars().all()
        
        # Format user data
        users_data = []
        for user in users:
            users_data.append({
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "subscription_tier": user.subscription_tier,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "is_premium": user.is_premium,
                "credits_remaining": user.credits_remaining,
                "credits_used_total": user.credits_used_total,
                "total_pdf_runs": user.total_pdf_runs,
                "custom_limits_enabled": user.custom_limits_enabled,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None
            })
        
        return {
            "users": users_data,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: UUID,
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed information about a specific user.
    
    Includes limits, usage statistics, and account history.
    """
    try:
        # Get user with relationships
        result = await session.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.processing_jobs),
                selectinload(User.uploaded_files),
                selectinload(User.templates)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get limits summary
        limits_summary = await get_user_limits_summary(session, str(user_id))
        
        # Get usage statistics
        jobs_count = len(user.processing_jobs) if user.processing_jobs else 0
        files_count = len(user.uploaded_files) if user.uploaded_files else 0
        templates_count = len(user.templates) if user.templates else 0
        
        # Get recent jobs
        recent_jobs = await session.execute(
            select(ProcessingJob)
            .where(ProcessingJob.user_id == user_id)
            .order_by(desc(ProcessingJob.created_at))
            .limit(10)
        )
        recent_jobs_list = recent_jobs.scalars().all()
        
        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "subscription_tier": user.subscription_tier,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "is_premium": user.is_premium,
                "credits_remaining": user.credits_remaining,
                "credits_rollover": user.credits_rollover,
                "credits_used_this_month": user.credits_used_this_month,
                "credits_used_total": user.credits_used_total,
                "total_pdf_runs": user.total_pdf_runs,
                "subscription_start_date": user.subscription_start_date.isoformat() if user.subscription_start_date else None,
                "subscription_end_date": user.subscription_end_date.isoformat() if user.subscription_end_date else None,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None
            },
            "limits": limits_summary,
            "statistics": {
                "total_pdf_runs": user.total_pdf_runs,
                "total_files": files_count,
                "total_templates": templates_count
            },
            "recent_jobs": [
                {
                    "id": str(job.id),
                    "template_filename": job.template_filename,
                    "csv_filename": job.csv_filename,
                    "pdf_count": job.pdf_count,
                    "successful_count": job.successful_count,
                    "status": job.status,
                    "created_at": job.created_at.isoformat()
                }
                for job in recent_jobs_list
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user details: {str(e)}")


@router.get("/users/{user_id}/jobs")
async def get_user_jobs(
    user_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get paginated processing jobs for a user with file information.
    
    Args:
        user_id: User ID
        page: Page number (1-indexed)
        limit: Number of jobs per page (max 100)
    """
    try:
        # Calculate offset
        offset = (page - 1) * limit
        
        # Get total count
        total_count_result = await session.execute(
            select(func.count(ProcessingJob.id))
            .where(ProcessingJob.user_id == user_id)
        )
        total_count = total_count_result.scalar() or 0
        
        # Get paginated jobs with file relationships
        jobs_result = await session.execute(
            select(ProcessingJob)
            .where(ProcessingJob.user_id == user_id)
            .options(
                selectinload(ProcessingJob.template_file),
                selectinload(ProcessingJob.csv_file)
            )
            .order_by(desc(ProcessingJob.created_at))
            .limit(limit)
            .offset(offset)
        )
        jobs = jobs_result.scalars().all()
        
        # Build response with file information
        jobs_list = []
        for job in jobs:
            job_data = {
                "id": str(job.id),
                "template_filename": job.template_filename,
                "csv_filename": job.csv_filename,
                "pdf_count": job.pdf_count,
                "successful_count": job.successful_count,
                "failed_count": job.failed_count,
                "status": job.status,
                "total_credits_consumed": job.total_credits_consumed,
                "subscription_credits_used": job.subscription_credits_used,
                "rollover_credits_used": job.rollover_credits_used,
                "topup_credits_used": job.topup_credits_used,
                "processing_time_seconds": float(job.processing_time_seconds) if job.processing_time_seconds else None,
                "file_size_mb": float(job.file_size_mb) if job.file_size_mb else None,
                "zip_filename": job.zip_filename,
                "session_id": job.session_id,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message,
                # File download information
                "template_file": None,
                "csv_file": None,
                "zip_file_path": job.zip_file_path
            }
            
            # Add template file info if available
            if job.template_file:
                job_data["template_file"] = {
                    "id": str(job.template_file.id),
                    "stored_filename": job.template_file.stored_filename,
                    "original_filename": job.template_file.original_filename,
                    "file_path": job.template_file.file_path
                }
            
            # Add CSV file info if available
            if job.csv_file:
                job_data["csv_file"] = {
                    "id": str(job.csv_file.id),
                    "stored_filename": job.csv_file.stored_filename,
                    "original_filename": job.csv_file.original_filename,
                    "file_path": job.csv_file.file_path
                }
            
            jobs_list.append(job_data)
        
        return {
            "jobs": jobs_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user jobs: {str(e)}")


@router.get("/files/{file_id}/download")
async def download_user_file(
    file_id: UUID,
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Download an uploaded file (PDF template or CSV) by file ID.
    
    This endpoint allows admins to download files for debugging.
    """
    try:
        result = await session.execute(
            select(UploadedFile).where(UploadedFile.id == file_id)
        )
        file = result.scalar_one_or_none()
        
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if file exists on disk
        if not os.path.exists(file.file_path):
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Return the file
        return FileResponse(
            path=file.file_path,
            filename=file.original_filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@router.get("/jobs/{job_id}/download-zip")
async def download_job_zip(
    job_id: UUID,
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Download the ZIP output file for a specific job.
    
    This endpoint allows admins to download job output files for debugging.
    """
    try:
        result = await session.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if not job.zip_file_path or not job.zip_filename:
            raise HTTPException(status_code=404, detail="ZIP file not available for this job")
        
        # Check if file exists on disk
        if not os.path.exists(job.zip_file_path):
            raise HTTPException(status_code=404, detail="ZIP file not found on disk")
        
        # Return the ZIP file
        return FileResponse(
            path=job.zip_file_path,
            filename=job.zip_filename,
            media_type='application/zip'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading job ZIP: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download job ZIP: {str(e)}")


# SECURITY NOTE: Admin write operations (PATCH, POST, DELETE) are exposed via API
# but should be considered UI-only operations. In production, consider adding:
# 1. IP whitelisting middleware
# 2. Origin/referer checking to ensure requests come from your UI
# 3. Rate limiting on admin endpoints
# 4. Enhanced audit logging with IP addresses
# 5. 2FA requirement for admin operations
#
# These endpoints require superuser authentication, but if a superuser token
# is compromised, these operations could be performed via API.


@router.patch("/users/{user_id}/subscription")
async def update_user_subscription(
    user_id: UUID,
    subscription_tier: str = Query(..., description="New subscription tier"),
    reason: Optional[str] = Query(None, description="Reason for subscription change"),
    request: Request = None,
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Update a user's subscription tier.
    
    SECURITY: This endpoint is intended for UI use only. Consider adding
    IP whitelisting or origin checking in production.
    
    Valid tiers: free, basic, pro, enterprise
    """
    try:
        # Get valid tiers from database (or use fallback list)
        result = await session.execute(
            select(SubscriptionTier.tier_key).where(SubscriptionTier.is_active == True)
        )
        valid_tiers = [row[0] for row in result.all()]
        if not valid_tiers:
            # Fallback if no tiers in database
            valid_tiers = ["free", "member", "pro", "enterprise"]
        
        if subscription_tier not in valid_tiers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid subscription tier. Must be one of: {', '.join(valid_tiers)}"
            )
        
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Capture old tier BEFORE making any changes
        old_tier = user.subscription_tier
        
        # When changing tier, remove custom limits and reset to tier defaults
        user.subscription_tier = subscription_tier
        user.custom_limits_enabled = False
        user.custom_max_pdf_size = None
        user.custom_max_csv_size = None
        user.custom_max_pdfs_per_run = None
        user.custom_can_save_templates = None
        user.custom_can_use_api = None
        user.custom_limits_reason = None
        
        await session.commit()
        await session.refresh(user)
        
        logger.warning(f"SECURITY: Admin {admin_user.email} (ID: {admin_user.id}) updated user {user.email} subscription to {subscription_tier} (custom limits removed)")
        
        # Log the activity (only if tier actually changed)
        if old_tier != subscription_tier:
            await activity_logger.log_subscription_change(
                session=session,
                user_id=user_id,
                old_tier=old_tier,
                new_tier=subscription_tier,
                reason=reason,
                actor_id=admin_user.id,
                request=request
            )
        
        return {
            "success": True,
            "message": f"Subscription updated to {subscription_tier}",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "subscription_tier": user.subscription_tier
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating subscription: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update subscription: {str(e)}")


@router.post("/users/{user_id}/custom-limits")
async def set_user_custom_limits(
    user_id: UUID,
    custom_limits: dict,
    reason: str = Query(..., description="Reason for applying custom limits"),
    request: Request = None,
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Set custom limits for a user.
    
    SECURITY: This endpoint is intended for UI use only.
    Custom limits override the subscription tier limits.
    """
    try:
        success = await set_custom_user_limits(
            session,
            str(user_id),
            custom_limits,
            reason,
            str(admin_user.id)
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to set custom limits")

        logger.warning(f"SECURITY: Admin {admin_user.email} (ID: {admin_user.id}) set custom limits for user {user_id}")
        
        # Log the activity
        await activity_logger.log_admin_action(
            session=session,
            admin_id=admin_user.id,
            action="Set custom user limits",
            target_user_id=user_id,
            activity_type="admin_set_custom_limits",
            description=f"Admin set custom limits for user",
            reason=reason,
            changes={"custom_limits": custom_limits},
            request=request
        )

        return {
            "success": True,
            "message": "Custom limits applied successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting custom limits: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set custom limits: {str(e)}")


@router.delete("/users/{user_id}/custom-limits")
async def remove_user_custom_limits(
    user_id: UUID,
    request: Request = None,
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Remove custom limits from a user, reverting to tier-based limits.
    
    SECURITY: This endpoint is intended for UI use only.
    """
    try:
        success = await remove_custom_user_limits(
            session,
            str(user_id),
            str(admin_user.id)
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to remove custom limits")
        
        logger.warning(f"SECURITY: Admin {admin_user.email} (ID: {admin_user.id}) removed custom limits from user {user_id}")
        
        # Log the activity
        await activity_logger.log_admin_action(
            session=session,
            admin_id=admin_user.id,
            action="Removed custom user limits",
            target_user_id=user_id,
            activity_type="admin_remove_custom_limits",
            description=f"Admin removed custom limits for user",
            request=request
        )
        
        return {
            "success": True,
            "message": "Custom limits removed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing custom limits: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove custom limits: {str(e)}")


@router.post("/users/{user_id}/apply-template")
async def apply_limit_template(
    user_id: UUID,
    template_name: str = Query(..., description="Template name to apply"),
    reason: Optional[str] = Query(None),
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Apply a predefined custom limit template to a user.
    
    SECURITY: This endpoint is intended for UI use only.
    Available templates: enterprise_trial, vvip_client, beta_tester, support_team
    """
    try:
        if template_name not in CUSTOM_LIMIT_TEMPLATES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown template. Available: {', '.join(CUSTOM_LIMIT_TEMPLATES.keys())}"
            )
        
        success = await apply_custom_limit_template(
            session,
            str(user_id),
            template_name,
            reason,
            str(admin_user.id)
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to apply template")
        
        logger.warning(f"SECURITY: Admin {admin_user.email} (ID: {admin_user.id}) applied template {template_name} to user {user_id}")
        
        return {
            "success": True,
            "message": f"Template '{template_name}' applied successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to apply template: {str(e)}")


@router.patch("/users/{user_id}/credits")
async def update_user_credits(
    user_id: UUID,
    credits_data: dict,
    request: Request = None,
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Update a user's credit balances (for testing/debugging).
    
    SECURITY: This endpoint is intended for UI use only. Consider adding
    IP whitelisting or origin checking in production.
    """
    try:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Track changes for logging
        changes = {}
        old_values = {}
        
        # Update credit fields if provided
        credit_fields = [
            'credits_remaining',
            'credits_rollover',
            'credits_used_this_month',
            'credits_used_total',
            'total_pdf_runs'
        ]
        
        for field in credit_fields:
            if field in credits_data:
                old_value = getattr(user, field)
                new_value = int(credits_data[field])
                if old_value != new_value:
                    old_values[field] = old_value
                    changes[field] = {"old": old_value, "new": new_value}
                    setattr(user, field, new_value)
        
        await session.commit()
        await session.refresh(user)
        
        logger.warning(f"SECURITY: Admin {admin_user.email} (ID: {admin_user.id}) updated credits for user {user.email} (ID: {user_id})")
        
        # Log the activity
        await activity_logger.log_admin_action(
            session=session,
            admin_id=admin_user.id,
            action="Updated user credits",
            target_user_id=user_id,
            activity_type="admin_user_credits_updated",
            description=f"Admin updated credit balances for user",
            changes=changes,
            request=request
        )
        
        return {
            "success": True,
            "message": "Credits updated successfully",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "credits_remaining": user.credits_remaining,
                "credits_rollover": user.credits_rollover,
                "credits_used_this_month": user.credits_used_this_month,
                "credits_used_total": user.credits_used_total,
                "total_pdf_runs": user.total_pdf_runs
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating user credits: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update credits: {str(e)}")


@router.patch("/users/{user_id}/activate")
async def toggle_user_active(
    user_id: UUID,
    is_active: bool = Query(..., description="Active status (true/false)"),
    request: Request = None,
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Activate or deactivate a user account.
    
    SECURITY: This endpoint is intended for UI use only. Consider adding
    IP whitelisting or origin checking in production.
    """
    try:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        old_status = user.is_active
        user.is_active = is_active
        await session.commit()
        await session.refresh(user)

        action = "activated" if is_active else "deactivated"
        logger.warning(f"SECURITY: Admin {admin_user.email} (ID: {admin_user.id}) {action} user {user.email} (ID: {user_id})")
        
        # Log the activity
        await activity_logger.log_admin_action(
            session=session,
            admin_id=admin_user.id,
            action=f"User {action}",
            target_user_id=user_id,
            activity_type="admin_user_status_changed",
            description=f"Admin {action} user account",
            changes={"old_status": old_status, "new_status": is_active},
            request=request
        )

        return {
            "success": True,
            "message": f"User {action} successfully",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "is_active": user.is_active
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error toggling user active status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update user status: {str(e)}")


@router.get("/templates/available")
async def get_available_templates(
    admin_user: User = Depends(get_current_admin)
):
    """
    Get list of available custom limit templates (read-only).
    
    Note: Applying templates must be done through the admin UI.
    """
    return {
        "templates": {
            name: {
                "description": f"Template: {name}",
                "limits": {
                    k: (format_file_size(v) if "size" in k.lower() else v)
                    for k, v in template.items()
                    if isinstance(v, (int, bool))
                }
            }
            for name, template in CUSTOM_LIMIT_TEMPLATES.items()
        }
    }


# Subscription Tier Management Endpoints

@router.get("/tiers")
async def list_subscription_tiers(
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    List all subscription tiers with their limits.
    """
    try:
        result = await session.execute(
            select(SubscriptionTier)
            .order_by(SubscriptionTier.display_order)
        )
        tiers = result.scalars().all()
        
        return {
            "tiers": [
                {
                    "id": str(tier.id),
                    "tier_key": tier.tier_key,
                    "display_name": tier.display_name,
                    "description": tier.description,
                    "max_pdf_size": format_file_size(tier.max_pdf_size),
                    "max_csv_size": format_file_size(tier.max_csv_size),
                    "max_pdfs_per_run": tier.max_pdfs_per_run,
                    "can_save_templates": tier.can_save_templates,
                    "can_use_api": tier.can_use_api,
                    "priority_processing": tier.priority_processing,
                    "max_saved_templates": tier.max_saved_templates,
                    "max_total_storage_mb": tier.max_total_storage_mb,
                    "monthly_pdf_credits": tier.monthly_pdf_credits,
                    "display_order": tier.display_order,
                    "is_active": tier.is_active,
                    "created_at": tier.created_at.isoformat(),
                    "updated_at": tier.updated_at.isoformat(),
                }
                for tier in tiers
            ]
        }
    except Exception as e:
        logger.error(f"Error listing tiers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tiers: {str(e)}")


@router.get("/tiers/{tier_id}")
async def get_subscription_tier(
    tier_id: UUID,
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """Get details of a specific subscription tier."""
    try:
        result = await session.execute(
            select(SubscriptionTier).where(SubscriptionTier.id == tier_id)
        )
        tier = result.scalar_one_or_none()
        
        if not tier:
            raise HTTPException(status_code=404, detail="Tier not found")
        
        return {
            "id": str(tier.id),
            "tier_key": tier.tier_key,
            "display_name": tier.display_name,
            "description": tier.description,
            "max_pdf_size": tier.max_pdf_size,  # Return in bytes for editing
            "max_csv_size": tier.max_csv_size,
            "max_pdfs_per_run": tier.max_pdfs_per_run,
            "can_save_templates": tier.can_save_templates,
            "can_use_api": tier.can_use_api,
            "priority_processing": tier.priority_processing,
            "max_saved_templates": tier.max_saved_templates,
            "max_total_storage_mb": tier.max_total_storage_mb,
            "monthly_pdf_credits": tier.monthly_pdf_credits,
            "display_order": tier.display_order,
            "is_active": tier.is_active,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tier: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tier: {str(e)}")


@router.post("/tiers")
async def create_subscription_tier(
    tier_data: dict,
    request: Request = None,
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Create a new subscription tier.
    
    SECURITY: This endpoint is intended for UI use only.
    """
    try:
        # Validate required fields
        required_fields = ["tier_key", "display_name", "max_pdf_size", "max_csv_size"]
        for field in required_fields:
            if field not in tier_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Check if tier_key already exists
        existing = await session.execute(
            select(SubscriptionTier).where(SubscriptionTier.tier_key == tier_data["tier_key"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Tier key '{tier_data['tier_key']}' already exists")
        
        # Create new tier
        new_tier = SubscriptionTier(
            tier_key=tier_data["tier_key"],
            display_name=tier_data["display_name"],
            description=tier_data.get("description"),
            max_pdf_size=tier_data["max_pdf_size"],
            max_csv_size=tier_data["max_csv_size"],
            max_pdfs_per_run=tier_data.get("max_pdfs_per_run", 100),
            can_save_templates=tier_data.get("can_save_templates", False),
            can_use_api=tier_data.get("can_use_api", False),
            priority_processing=tier_data.get("priority_processing", False),
            max_saved_templates=tier_data.get("max_saved_templates", 0),
            max_total_storage_mb=tier_data.get("max_total_storage_mb", 0),
            monthly_pdf_credits=tier_data.get("monthly_pdf_credits", 0),
            display_order=tier_data.get("display_order", 999),
            is_active=tier_data.get("is_active", True),
        )
        
        session.add(new_tier)
        await session.commit()
        await session.refresh(new_tier)
        
        # Refresh cache
        await refresh_tier_cache(session)
        
        logger.warning(f"SECURITY: Admin {admin_user.email} (ID: {admin_user.id}) created tier {new_tier.tier_key}")
        
        # Log the activity
        await activity_logger.log_tier_updated(
            session=session,
            admin_id=admin_user.id,
            tier_id=new_tier.id,
            action=f"Created tier '{new_tier.display_name}'",
            changes={"created": tier_data},
            request=request
        )
        
        return {
            "success": True,
            "message": f"Tier '{new_tier.display_name}' created successfully",
            "tier": {
                "id": str(new_tier.id),
                "tier_key": new_tier.tier_key,
                "display_name": new_tier.display_name,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating tier: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create tier: {str(e)}")


@router.patch("/tiers/{tier_id}")
async def update_subscription_tier(
    tier_id: UUID,
    tier_data: dict,
    request: Request = None,
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Update an existing subscription tier.
    
    SECURITY: This endpoint is intended for UI use only.
    """
    try:
        result = await session.execute(
            select(SubscriptionTier).where(SubscriptionTier.id == tier_id)
        )
        tier = result.scalar_one_or_none()
        
        if not tier:
            raise HTTPException(status_code=404, detail="Tier not found")
        
        # Capture original values for logging
        original_values = {}
        updatable_fields = [
            "display_name", "description", "max_pdf_size", "max_csv_size",
            "max_pdfs_per_run",
            "can_save_templates", "can_use_api", "priority_processing",
            "max_saved_templates", "max_total_storage_mb", "monthly_pdf_credits",
            "display_order", "is_active"
        ]
        
        # Track changes for logging
        changes = {}
        for field in updatable_fields:
            if field in tier_data:
                original_value = getattr(tier, field)
                new_value = tier_data[field]
                if original_value != new_value:
                    original_values[field] = original_value
                    changes[field] = {"old": original_value, "new": new_value}
                setattr(tier, field, new_value)
        
        await session.commit()
        await session.refresh(tier)
        
        # Refresh cache
        await refresh_tier_cache(session)
        
        logger.warning(f"SECURITY: Admin {admin_user.email} (ID: {admin_user.id}) updated tier {tier.tier_key}")
        
        # Log the activity if there were any changes
        if changes:
            await activity_logger.log_tier_updated(
                session=session,
                admin_id=admin_user.id,
                tier_id=tier.id,
                action=f"Updated tier '{tier.display_name}'",
                changes=changes,
                request=request
            )
        
        return {
            "success": True,
            "message": f"Tier '{tier.display_name}' updated successfully",
            "tier": {
                "id": str(tier.id),
                "tier_key": tier.tier_key,
                "display_name": tier.display_name,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating tier: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update tier: {str(e)}")


@router.delete("/tiers/{tier_id}")
async def delete_subscription_tier(
    tier_id: UUID,
    request: Request = None,
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Delete a subscription tier.
    
    SECURITY: This endpoint is intended for UI use only.
    Note: Tiers cannot be deleted if users are assigned to them. Use is_active=false instead.
    """
    try:
        result = await session.execute(
            select(SubscriptionTier).where(SubscriptionTier.id == tier_id)
        )
        tier = result.scalar_one_or_none()
        
        if not tier:
            raise HTTPException(status_code=404, detail="Tier not found")
        
        # Check if any users are using this tier
        users_result = await session.execute(
            select(func.count(User.id)).where(User.subscription_tier == tier.tier_key)
        )
        user_count = users_result.scalar() or 0
        
        if user_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete tier '{tier.display_name}': {user_count} user(s) are assigned to this tier. Deactivate it instead (set is_active=false)."
            )
        
        tier_key = tier.tier_key
        tier_display_name = tier.display_name
        
        # Log the activity BEFORE deleting
        await activity_logger.log_tier_updated(
            session=session,
            admin_id=admin_user.id,
            tier_id=tier_id,
            action=f"Deleted tier '{tier_display_name}'",
            changes={"deleted": {"tier_key": tier_key, "display_name": tier_display_name}},
            request=request
        )
        
        await session.delete(tier)
        await session.commit()
        
        # Refresh cache
        await refresh_tier_cache(session)
        
        logger.warning(f"SECURITY: Admin {admin_user.email} (ID: {admin_user.id}) deleted tier {tier_key}")
        
        return {
            "success": True,
            "message": f"Tier '{tier_display_name}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting tier: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete tier: {str(e)}")


# Activity Log Endpoints

@router.get("/users/{user_id}/activity-logs")
async def get_user_activity_logs(
    user_id: UUID,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    skip: int = Query(0, ge=0, description="Number of logs to skip"),
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get activity logs for a specific user.
    
    Returns all activities related to the user including:
    - User actions (registrations, logins, PDF processing)
    - Admin actions performed on the user
    - System events related to the user
    """
    try:
        from ..models import ActivityLog
        from sqlalchemy import or_
        
        # Get logs where user is the actor, target, or subject
        result = await session.execute(
            select(ActivityLog)
            .where(
                or_(
                    ActivityLog.user_id == user_id,
                    ActivityLog.target_user_id == user_id,
                    ActivityLog.actor_id == user_id
                )
            )
            .order_by(desc(ActivityLog.created_at))
            .limit(limit)
            .offset(skip)
        )
        logs = result.scalars().all()
        
        # Get total count
        count_result = await session.execute(
            select(func.count(ActivityLog.id))
            .where(
                or_(
                    ActivityLog.user_id == user_id,
                    ActivityLog.target_user_id == user_id,
                    ActivityLog.actor_id == user_id
                )
            )
        )
        total = count_result.scalar()
        
        return {
            "logs": [
                {
                    "id": str(log.id),
                    "activity_type": log.activity_type,
                    "category": log.category,
                    "action": log.action,
                    "description": log.description,
                    "reason": log.reason,
                    "metadata": json.loads(log.additional_metadata) if log.additional_metadata else None,
                    "changes": json.loads(log.changes) if log.changes else None,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "country": log.country,
                    "actor_type": log.actor_type,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting activity logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get activity logs: {str(e)}")


@router.get("/activity-logs")
async def get_system_activity_logs(
    category: Optional[str] = Query(None, description="Filter by category (e.g., 'admin', 'system')"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type (e.g., 'tier_updated')"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    skip: int = Query(0, ge=0, description="Number of logs to skip"),
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get system-wide activity logs for non-user-specific changes.
    
    Returns activities such as:
    - Subscription tier changes (created, updated, deleted)
    - System configuration changes
    - Other admin actions not tied to specific users
    
    By default, shows admin category logs and tier-related activities.
    """
    try:
        from ..models import ActivityLog
        
        # Build base query
        query = select(ActivityLog)
        count_query = select(func.count(ActivityLog.id))
        
        # Build where clause conditions
        where_clauses = []
        
        # Filter by category if provided, otherwise use default filter
        if category:
            where_clauses.append(ActivityLog.category == category)
        else:
            # Default: show admin/system categories or tier-related activities
            # Use is_not() method for SQLAlchemy 2.0+ null check
            where_clauses.append(
                or_(
                    ActivityLog.category == "admin",
                    ActivityLog.activity_type == "tier_updated",
                    ActivityLog.related_tier_id.is_not(None)
                )
            )
        
        # Filter by activity_type if provided
        if activity_type:
            where_clauses.append(ActivityLog.activity_type == activity_type)
        
        # Apply where clauses to both queries
        if where_clauses:
            if len(where_clauses) == 1:
                query = query.where(where_clauses[0])
                count_query = count_query.where(where_clauses[0])
            else:
                query = query.where(and_(*where_clauses))
                count_query = count_query.where(and_(*where_clauses))
        
        # Execute main query with ordering and pagination
        result = await session.execute(
            query
            .order_by(desc(ActivityLog.created_at))
            .limit(limit)
            .offset(skip)
        )
        logs = result.scalars().all()
        
        # Execute count query
        count_result = await session.execute(count_query)
        total = count_result.scalar()
        
        # Get actor user info for display
        actor_ids = {log.actor_id for log in logs if log.actor_id}
        actor_users = {}
        if actor_ids:
            users_result = await session.execute(
                select(User).where(User.id.in_(actor_ids))
            )
            for user in users_result.scalars().all():
                actor_users[str(user.id)] = {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                }
        
        return {
            "logs": [
                {
                    "id": str(log.id),
                    "activity_type": log.activity_type,
                    "category": log.category,
                    "action": log.action,
                    "description": log.description,
                    "reason": log.reason,
                    "metadata": json.loads(log.additional_metadata) if log.additional_metadata else None,
                    "changes": json.loads(log.changes) if log.changes else None,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "country": log.country,
                    "actor_type": log.actor_type,
                    "actor": actor_users.get(str(log.actor_id)) if log.actor_id else None,
                    "related_tier_id": str(log.related_tier_id) if log.related_tier_id else None,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting system activity logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system activity logs: {str(e)}")


@router.get("/jobs")
async def list_all_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    user_tier: Optional[str] = Query(None, description="Filter by user subscription tier"),
    admin_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get paginated processing jobs for all users with filtering options.
    
    Args:
        page: Page number (1-indexed)
        limit: Number of jobs per page (max 100)
        user_email: Filter by user email (partial match)
        user_tier: Filter by user subscription tier
    """
    try:
        # Calculate offset
        offset = (page - 1) * limit
        
        # Build where clauses for filtering
        where_clauses = []
        
        # Apply filters
        if user_email:
            email_lower = user_email.lower().strip()
            if email_lower == "anonymous" or email_lower == "anon":
                # Filter for anonymous jobs (user_id IS NULL)
                where_clauses.append(ProcessingJob.user_id.is_(None))
            else:
                # Filter by user email (for registered users)
                search_term = f"%{user_email}%"
                user_email_subquery = select(User.id).where(
                    and_(
                        User.id == ProcessingJob.user_id,
                        User.email.ilike(search_term)
                    )
                ).exists()
                where_clauses.append(user_email_subquery)
        
        if user_tier:
            tier_lower = user_tier.lower().strip()
            if tier_lower == "anonymous" or tier_lower == "anon":
                # Filter for anonymous jobs (user_id IS NULL)
                where_clauses.append(ProcessingJob.user_id.is_(None))
            else:
                # Filter by subscription tier (for registered users)
                user_tier_subquery = select(User.id).where(
                    and_(
                        User.id == ProcessingJob.user_id,
                        User.subscription_tier == user_tier
                    )
                ).exists()
                where_clauses.append(user_tier_subquery)
        
        # Build base query for count
        count_query = select(func.count(ProcessingJob.id))
        if where_clauses:
            if len(where_clauses) == 1:
                count_query = count_query.where(where_clauses[0])
            else:
                count_query = count_query.where(and_(*where_clauses))
        
        total_count_result = await session.execute(count_query)
        total_count = total_count_result.scalar() or 0
        
        # Build main query with relationships
        query = select(ProcessingJob).options(
            selectinload(ProcessingJob.template_file),
            selectinload(ProcessingJob.csv_file),
            selectinload(ProcessingJob.user)
        )
        
        # Apply filters to main query
        if where_clauses:
            if len(where_clauses) == 1:
                query = query.where(where_clauses[0])
            else:
                query = query.where(and_(*where_clauses))
        
        # Apply ordering and pagination
        query = query.order_by(desc(ProcessingJob.created_at)).limit(limit).offset(offset)
        
        jobs_result = await session.execute(query)
        jobs = jobs_result.scalars().all()
        
        # Build response with file information and user info
        jobs_list = []
        for job in jobs:
            job_data = {
                "id": str(job.id),
                "template_filename": job.template_filename,
                "csv_filename": job.csv_filename,
                "pdf_count": job.pdf_count,
                "successful_count": job.successful_count,
                "failed_count": job.failed_count,
                "status": job.status,
                "total_credits_consumed": job.total_credits_consumed,
                "subscription_credits_used": job.subscription_credits_used,
                "rollover_credits_used": job.rollover_credits_used,
                "topup_credits_used": job.topup_credits_used,
                "processing_time_seconds": float(job.processing_time_seconds) if job.processing_time_seconds else None,
                "file_size_mb": float(job.file_size_mb) if job.file_size_mb else None,
                "zip_filename": job.zip_filename,
                "session_id": job.session_id,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message,
                "template_file": None,
                "csv_file": None,
                "zip_file_path": job.zip_file_path,
                "user": None
            }
            
            # Add user info if available
            if job.user:
                job_data["user"] = {
                    "id": str(job.user.id),
                    "email": job.user.email,
                    "first_name": job.user.first_name,
                    "last_name": job.user.last_name,
                    "subscription_tier": job.user.subscription_tier
                }
            
            # Add template file info if available
            if job.template_file:
                job_data["template_file"] = {
                    "id": str(job.template_file.id),
                    "stored_filename": job.template_file.stored_filename,
                    "original_filename": job.template_file.original_filename,
                    "file_path": job.template_file.file_path
                }
            
            # Add CSV file info if available
            if job.csv_file:
                job_data["csv_file"] = {
                    "id": str(job.csv_file.id),
                    "stored_filename": job.csv_file.stored_filename,
                    "original_filename": job.csv_file.original_filename,
                    "file_path": job.csv_file.file_path
                }
            
            jobs_list.append(job_data)
        
        return {
            "jobs": jobs_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting all jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get jobs: {str(e)}")


