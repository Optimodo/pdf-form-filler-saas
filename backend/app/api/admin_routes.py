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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

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
        user.custom_max_daily_jobs = None
        user.custom_max_monthly_jobs = None
        user.custom_max_files_per_job = None
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
                    "max_daily_jobs": tier.max_daily_jobs,
                    "max_monthly_jobs": tier.max_monthly_jobs,
                    "max_files_per_job": tier.max_files_per_job,
                    "can_save_templates": tier.can_save_templates,
                    "can_use_api": tier.can_use_api,
                    "priority_processing": tier.priority_processing,
                    "max_saved_templates": tier.max_saved_templates,
                    "max_total_storage_mb": tier.max_total_storage_mb,
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
            "max_daily_jobs": tier.max_daily_jobs,
            "max_monthly_jobs": tier.max_monthly_jobs,
            "max_files_per_job": tier.max_files_per_job,
            "can_save_templates": tier.can_save_templates,
            "can_use_api": tier.can_use_api,
            "priority_processing": tier.priority_processing,
            "max_saved_templates": tier.max_saved_templates,
            "max_total_storage_mb": tier.max_total_storage_mb,
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
            max_daily_jobs=tier_data.get("max_daily_jobs", 10),
            max_monthly_jobs=tier_data.get("max_monthly_jobs", 100),
            max_files_per_job=tier_data.get("max_files_per_job", 100),
            can_save_templates=tier_data.get("can_save_templates", False),
            can_use_api=tier_data.get("can_use_api", False),
            priority_processing=tier_data.get("priority_processing", False),
            max_saved_templates=tier_data.get("max_saved_templates", 0),
            max_total_storage_mb=tier_data.get("max_total_storage_mb", 0),
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
        
        # Update fields if provided
        updatable_fields = [
            "display_name", "description", "max_pdf_size", "max_csv_size",
            "max_daily_jobs", "max_monthly_jobs", "max_files_per_job",
            "can_save_templates", "can_use_api", "priority_processing",
            "max_saved_templates", "max_total_storage_mb", "display_order", "is_active"
        ]
        
        for field in updatable_fields:
            if field in tier_data:
                setattr(tier, field, tier_data[field])
        
        await session.commit()
        await session.refresh(tier)
        
        # Refresh cache
        await refresh_tier_cache(session)
        
        logger.warning(f"SECURITY: Admin {admin_user.email} (ID: {admin_user.id}) updated tier {tier.tier_key}")
        
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
        await session.delete(tier)
        await session.commit()
        
        # Refresh cache
        await refresh_tier_cache(session)
        
        logger.warning(f"SECURITY: Admin {admin_user.email} (ID: {admin_user.id}) deleted tier {tier_key}")
        
        return {
            "success": True,
            "message": f"Tier '{tier.display_name}' deleted successfully"
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

