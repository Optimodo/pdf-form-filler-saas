"""
Admin utility functions for managing user limits and special cases.

These functions are designed for admin interfaces and special user management.
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import User
from .user_limits import format_file_size, get_user_limits_from_user


async def set_custom_user_limits(
    session: AsyncSession,
    user_id: str,
    custom_limits: Dict[str, Any],
    reason: str,
    admin_user_id: Optional[str] = None
) -> bool:
    """
    Set custom limits for a specific user.
    
    Args:
        session: Database session
        user_id: UUID of the user to modify
        custom_limits: Dict of custom limits to apply
        reason: Reason for applying custom limits (for audit trail)
        admin_user_id: Optional UUID of admin applying the limits
        
    Returns:
        True if successful, False otherwise
        
    Example:
        await set_custom_user_limits(
            session,
            "user-uuid-here",
            {
                "max_pdf_size": 50 * 1024 * 1024,  # 50MB
                "max_daily_jobs": 100,
                "can_use_api": True
            },
            "Enterprise client - special contract",
            "admin-uuid-here"
        )
    """
    try:
        # Get the user
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # Enable custom limits
        user.custom_limits_enabled = True
        user.custom_limits_reason = reason
        
        # Apply the custom limits
        if "max_pdf_size" in custom_limits:
            user.custom_max_pdf_size = custom_limits["max_pdf_size"]
        
        if "max_csv_size" in custom_limits:
            user.custom_max_csv_size = custom_limits["max_csv_size"]
        
        if "max_daily_jobs" in custom_limits:
            user.custom_max_daily_jobs = custom_limits["max_daily_jobs"]
        
        if "max_monthly_jobs" in custom_limits:
            user.custom_max_monthly_jobs = custom_limits["max_monthly_jobs"]
        
        if "max_files_per_job" in custom_limits:
            user.custom_max_files_per_job = custom_limits["max_files_per_job"]
        
        if "can_save_templates" in custom_limits:
            user.custom_can_save_templates = custom_limits["can_save_templates"]
        
        if "can_use_api" in custom_limits:
            user.custom_can_use_api = custom_limits["can_use_api"]
        
        await session.commit()
        
        # Log the change (you could add to a separate audit table in the future)
        print(f"Admin {admin_user_id or 'SYSTEM'} applied custom limits to user {user_id}: {reason}")
        
        return True
        
    except Exception as e:
        await session.rollback()
        print(f"Error setting custom limits for user {user_id}: {e}")
        return False


async def remove_custom_user_limits(
    session: AsyncSession,
    user_id: str,
    admin_user_id: Optional[str] = None
) -> bool:
    """
    Remove custom limits from a user, reverting to tier-based limits.
    
    Args:
        session: Database session
        user_id: UUID of the user to modify
        admin_user_id: Optional UUID of admin removing the limits
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get the user
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # Disable custom limits and clear all overrides
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
        
        # Log the change
        print(f"Admin {admin_user_id or 'SYSTEM'} removed custom limits from user {user_id}")
        
        return True
        
    except Exception as e:
        await session.rollback()
        print(f"Error removing custom limits for user {user_id}: {e}")
        return False


async def get_user_limits_summary(session: AsyncSession, user_id: str) -> Dict[str, Any]:
    """
    Get a comprehensive summary of a user's limits and account status.
    
    Args:
        session: Database session
        user_id: UUID of the user
        
    Returns:
        Dict with user limits summary
    """
    try:
        # Get the user
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return {"error": "User not found"}
        
        # Get current limits
        limits = get_user_limits_from_user(user)
        
        return {
            "user_id": str(user.id),
            "email": user.email,
            "subscription_tier": user.subscription_tier,
            "has_custom_limits": user.custom_limits_enabled,
            "custom_limits_reason": user.custom_limits_reason,
            "current_limits": {
                "max_pdf_size": f"{format_file_size(limits.max_pdf_size)}",
                "max_csv_size": f"{format_file_size(limits.max_csv_size)}",
                "max_daily_jobs": limits.max_daily_jobs,
                "max_monthly_jobs": limits.max_monthly_jobs,
                "max_files_per_job": limits.max_files_per_job,
                "can_save_templates": limits.can_save_templates,
                "can_use_api": limits.can_use_api,
                "priority_processing": limits.priority_processing,
            },
            "account_status": {
                "is_active": user.is_active,
                "is_premium": user.is_premium,
                "credits_remaining": user.credits_remaining,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
            }
        }
        
    except Exception as e:
        return {"error": f"Failed to get user summary: {e}"}


# Predefined custom limit templates for common cases
CUSTOM_LIMIT_TEMPLATES = {
    "enterprise_trial": {
        "max_pdf_size": 20 * 1024 * 1024,      # 20MB
        "max_csv_size": 5 * 1024 * 1024,       # 5MB
        "max_daily_jobs": 50,
        "max_monthly_jobs": 500,
        "can_save_templates": True,
        "can_use_api": True,
    },
    
    "vvip_client": {
        "max_pdf_size": 100 * 1024 * 1024,     # 100MB
        "max_csv_size": 25 * 1024 * 1024,      # 25MB
        "max_daily_jobs": 500,
        "max_monthly_jobs": 5000,
        "max_files_per_job": 5000,
        "can_save_templates": True,
        "can_use_api": True,
    },
    
    "beta_tester": {
        "max_daily_jobs": 20,                  # Higher than free tier
        "max_monthly_jobs": 100,
        "can_save_templates": True,            # Access to pro features
    },
    
    "support_team": {
        "max_pdf_size": 50 * 1024 * 1024,      # 50MB for testing
        "max_csv_size": 10 * 1024 * 1024,      # 10MB for testing
        "max_daily_jobs": 100,
        "can_save_templates": True,
        "can_use_api": True,
    }
}


async def apply_custom_limit_template(
    session: AsyncSession,
    user_id: str,
    template_name: str,
    reason: Optional[str] = None,
    admin_user_id: Optional[str] = None
) -> bool:
    """
    Apply a predefined custom limit template to a user.
    
    Args:
        session: Database session
        user_id: UUID of the user
        template_name: Name of the template to apply
        reason: Optional custom reason (will use template name if not provided)
        admin_user_id: Optional UUID of admin applying the template
        
    Returns:
        True if successful, False otherwise
    """
    if template_name not in CUSTOM_LIMIT_TEMPLATES:
        print(f"Unknown template: {template_name}")
        return False
    
    template = CUSTOM_LIMIT_TEMPLATES[template_name]
    final_reason = reason or f"Applied {template_name} template"
    
    return await set_custom_user_limits(
        session, user_id, template, final_reason, admin_user_id
    )
