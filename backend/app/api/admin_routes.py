"""
Admin API Routes

Provides endpoints for administrative functions including:
- User management
- Subscription management
- System analytics
- Custom limits management
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

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
from ..core.user_limits import format_file_size

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
        
        # Total storage used (approximate)
        storage_result = await session.execute(
            select(func.sum(UploadedFile.file_size_bytes))
        )
        total_storage_bytes = storage_result.scalar() or 0
        
        # Recent activity (last 24 hours)
        from datetime import datetime, timedelta
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_jobs_result = await session.execute(
            select(func.count(ProcessingJob.id))
            .where(ProcessingJob.created_at >= last_24h)
        )
        recent_jobs = recent_jobs_result.scalar() or 0
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "by_tier": users_by_tier
            },
            "jobs": {
                "total": total_jobs,
                "successful": successful_jobs,
                "recent_24h": recent_jobs
            },
            "processing": {
                "total_pdfs": total_pdfs or 0
            },
            "storage": {
                "total_bytes": total_storage_bytes or 0,
                "total_display": format_file_size(total_storage_bytes or 0)
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
    """
    try:
        query = select(User)
        
        # Apply filters
        if search:
            search_term = f"%{search}%"
            query = query.where(
                (User.email.ilike(search_term)) |
                (User.first_name.ilike(search_term)) |
                (User.last_name.ilike(search_term))
            )
        
        if tier:
            query = query.where(User.subscription_tier == tier)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination and ordering
        query = query.order_by(desc(User.created_at)).offset(skip).limit(limit)
        
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
                "credits_used_this_month": user.credits_used_this_month,
                "subscription_start_date": user.subscription_start_date.isoformat() if user.subscription_start_date else None,
                "subscription_end_date": user.subscription_end_date.isoformat() if user.subscription_end_date else None,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None
            },
            "limits": limits_summary,
            "statistics": {
                "total_jobs": jobs_count,
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
        valid_tiers = ["free", "basic", "pro", "enterprise"]
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
        
        user.subscription_tier = subscription_tier
        await session.commit()
        await session.refresh(user)
        
        logger.warning(f"SECURITY: Admin {admin_user.email} (ID: {admin_user.id}) updated user {user.email} subscription to {subscription_tier}")
        
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


@router.patch("/users/{user_id}/activate")
async def toggle_user_active(
    user_id: UUID,
    is_active: bool = Query(..., description="Active status (true/false)"),
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
        
        user.is_active = is_active
        await session.commit()
        await session.refresh(user)
        
        action = "activated" if is_active else "deactivated"
        logger.warning(f"SECURITY: Admin {admin_user.email} (ID: {admin_user.id}) {action} user {user.email} (ID: {user_id})")
        
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

