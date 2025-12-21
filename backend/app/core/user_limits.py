"""
User limits and restrictions based on subscription tiers.

This module provides functions to get user limits from database-stored tier configurations,
with fallback to cached values for backwards compatibility.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import SubscriptionTier


@dataclass
class UserLimits:
    """User limits configuration for different subscription tiers."""
    
    # File size limits (in bytes)
    max_pdf_size: int
    max_csv_size: int
    
    # Processing limits
    max_pdfs_per_run: int  # Maximum PDFs allowed in a single processing run
    
    # Feature access
    can_save_templates: bool
    can_use_api: bool
    priority_processing: bool
    
    # Storage limits
    max_saved_templates: int
    max_total_storage_mb: int
    
    # Monthly credit allowance
    monthly_pdf_credits: int  # Monthly PDF credits for this tier


# Fallback limits cache (populated from database on startup or tier updates)
_tier_cache: Dict[str, UserLimits] = {}


async def refresh_tier_cache(session: AsyncSession) -> None:
    """Refresh the in-memory tier cache from database."""
    global _tier_cache
    result = await session.execute(
        select(SubscriptionTier).where(SubscriptionTier.is_active == True)
    )
    tiers = result.scalars().all()
    
    _tier_cache.clear()
    for tier in tiers:
        _tier_cache[tier.tier_key] = UserLimits(
            max_pdf_size=tier.max_pdf_size,
            max_csv_size=tier.max_csv_size,
            max_pdfs_per_run=tier.max_pdfs_per_run,
            can_save_templates=tier.can_save_templates,
            can_use_api=tier.can_use_api,
            priority_processing=tier.priority_processing,
            max_saved_templates=tier.max_saved_templates,
            max_total_storage_mb=tier.max_total_storage_mb,
            monthly_pdf_credits=tier.monthly_pdf_credits,
        )


async def get_tier_limits_from_db(session: AsyncSession, tier_key: str) -> Optional[UserLimits]:
    """
    Get tier limits from database.
    
    Args:
        session: Database session
        tier_key: Tier key (e.g., "free", "member", "pro", "enterprise")
        
    Returns:
        UserLimits object or None if tier not found
    """
    result = await session.execute(
        select(SubscriptionTier).where(
            SubscriptionTier.tier_key == tier_key,
            SubscriptionTier.is_active == True
        )
    )
    tier = result.scalar_one_or_none()
    
    if not tier:
        return None
    
    return UserLimits(
        max_pdf_size=tier.max_pdf_size,
        max_csv_size=tier.max_csv_size,
        max_pdfs_per_run=tier.max_pdfs_per_run,
        can_save_templates=tier.can_save_templates,
        can_use_api=tier.can_use_api,
        priority_processing=tier.priority_processing,
        max_saved_templates=tier.max_saved_templates,
        max_total_storage_mb=tier.max_total_storage_mb,
        monthly_pdf_credits=tier.monthly_pdf_credits,
    )


# Fallback limits if database tier not found (used before cache is populated)
_FALLBACK_LIMITS = UserLimits(
    max_pdf_size=1 * 1024 * 1024,      # 1 MB (free tier defaults)
    max_csv_size=250 * 1024,           # 250 KB
    max_pdfs_per_run=50,
    can_save_templates=False,
    can_use_api=False,
    priority_processing=False,
    max_saved_templates=0,
    max_total_storage_mb=0,
    monthly_pdf_credits=0,  # Free tier typically has no monthly credits
)


def get_user_limits(subscription_tier: str, custom_overrides=None) -> UserLimits:
    """
    Get user limits for a specific subscription tier with optional custom overrides.
    Uses in-memory cache of tier limits (refreshed from database).
    
    Args:
        subscription_tier: The user's subscription tier (e.g., "free", "member", "pro", "enterprise")
        custom_overrides: Optional dict or User object with custom limit overrides
        
    Returns:
        UserLimits object with the appropriate limits (including any custom overrides)
    """
    # Get base limits from cache, or fallback if cache not populated
    if subscription_tier in _tier_cache:
        base_limits = _tier_cache[subscription_tier]
    else:
        # Fallback to free tier limits if tier not found
        base_limits = _tier_cache.get("free", _FALLBACK_LIMITS)
    
    # If no custom overrides, return base limits
    if not custom_overrides:
        return base_limits
    
    # Handle User object (has custom_limits_enabled attribute)
    if hasattr(custom_overrides, 'custom_limits_enabled'):
        if not custom_overrides.custom_limits_enabled:
            return base_limits
        
        # Apply custom overrides from User object
        return UserLimits(
            max_pdf_size=custom_overrides.custom_max_pdf_size or base_limits.max_pdf_size,
            max_csv_size=custom_overrides.custom_max_csv_size or base_limits.max_csv_size,
            max_pdfs_per_run=custom_overrides.custom_max_pdfs_per_run or base_limits.max_pdfs_per_run,
            can_save_templates=custom_overrides.custom_can_save_templates if custom_overrides.custom_can_save_templates is not None else base_limits.can_save_templates,
            can_use_api=custom_overrides.custom_can_use_api if custom_overrides.custom_can_use_api is not None else base_limits.can_use_api,
            priority_processing=base_limits.priority_processing,  # This remains tier-based for now
            max_saved_templates=base_limits.max_saved_templates,  # This remains tier-based for now
            max_total_storage_mb=base_limits.max_total_storage_mb,  # This remains tier-based for now
            monthly_pdf_credits=base_limits.monthly_pdf_credits,  # Monthly credits remain tier-based
        )
    
    # Handle dict-style overrides (for admin interfaces)
    elif isinstance(custom_overrides, dict):
        return UserLimits(
            max_pdf_size=custom_overrides.get('max_pdf_size', base_limits.max_pdf_size),
            max_csv_size=custom_overrides.get('max_csv_size', base_limits.max_csv_size),
            max_pdfs_per_run=custom_overrides.get('max_pdfs_per_run', base_limits.max_pdfs_per_run),
            can_save_templates=custom_overrides.get('can_save_templates', base_limits.can_save_templates),
            can_use_api=custom_overrides.get('can_use_api', base_limits.can_use_api),
            priority_processing=custom_overrides.get('priority_processing', base_limits.priority_processing),
            max_saved_templates=custom_overrides.get('max_saved_templates', base_limits.max_saved_templates),
            max_total_storage_mb=custom_overrides.get('max_total_storage_mb', base_limits.max_total_storage_mb),
            monthly_pdf_credits=custom_overrides.get('monthly_pdf_credits', base_limits.monthly_pdf_credits),
        )
    
    return base_limits


def get_user_limits_from_user(user) -> UserLimits:
    """
    Convenience function to get user limits directly from a User object.
    
    Args:
        user: User object with subscription_tier and optional custom overrides
        
    Returns:
        UserLimits object with appropriate limits
    """
    return get_user_limits(user.subscription_tier, user)


def get_anonymous_user_limits() -> UserLimits:
    """
    Get limits for anonymous (non-logged-in) users.
    These are more restrictive than free tier users.
    """
    return UserLimits(
        max_pdf_size=512 * 1024,           # 512 KB (smaller than free)
        max_csv_size=100 * 1024,           # 100 KB (smaller than free)
        max_pdfs_per_run=10,               # Small batches only
        can_save_templates=False,
        can_use_api=False,
        priority_processing=False,
        max_saved_templates=0,
        max_total_storage_mb=0,
        monthly_pdf_credits=0,  # Anonymous users have no monthly credits
    )


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string (e.g., "1.5 MB", "512 KB")
    """
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} KB"
    else:
        return f"{size_bytes} bytes"


def validate_file_size(file_size: int, max_size: int, file_type: str) -> tuple[bool, str]:
    """
    Validate if a file size is within limits.
    
    Args:
        file_size: Actual file size in bytes
        max_size: Maximum allowed size in bytes
        file_type: Type of file (for error message)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if file_size > max_size:
        return False, (
            f"{file_type} file size ({format_file_size(file_size)}) exceeds "
            f"the maximum allowed size of {format_file_size(max_size)} for your account tier. "
            f"Please upgrade your subscription for larger file limits."
        )
    
    return True, ""
