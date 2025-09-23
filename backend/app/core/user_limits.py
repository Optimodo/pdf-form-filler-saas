"""
User limits and restrictions based on subscription tiers.

This module defines file size limits, processing limits, and other restrictions
that vary based on user subscription levels.
"""
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class UserLimits:
    """User limits configuration for different subscription tiers."""
    
    # File size limits (in bytes)
    max_pdf_size: int
    max_csv_size: int
    
    # Processing limits
    max_daily_jobs: int
    max_monthly_jobs: int
    max_files_per_job: int
    
    # Feature access
    can_save_templates: bool
    can_use_api: bool
    priority_processing: bool
    
    # Storage limits
    max_saved_templates: int
    max_total_storage_mb: int


# Define limits for each subscription tier
SUBSCRIPTION_LIMITS: Dict[str, UserLimits] = {
    "free": UserLimits(
        max_pdf_size=1 * 1024 * 1024,      # 1 MB
        max_csv_size=250 * 1024,           # 250 KB
        max_daily_jobs=3,
        max_monthly_jobs=10,
        max_files_per_job=50,              # Limit bulk processing
        can_save_templates=False,
        can_use_api=False,
        priority_processing=False,
        max_saved_templates=0,
        max_total_storage_mb=0,
    ),
    
    "basic": UserLimits(
        max_pdf_size=5 * 1024 * 1024,      # 5 MB
        max_csv_size=1 * 1024 * 1024,      # 1 MB
        max_daily_jobs=20,
        max_monthly_jobs=100,
        max_files_per_job=200,
        can_save_templates=True,
        can_use_api=False,
        priority_processing=False,
        max_saved_templates=5,
        max_total_storage_mb=50,
    ),
    
    "pro": UserLimits(
        max_pdf_size=20 * 1024 * 1024,     # 20 MB
        max_csv_size=5 * 1024 * 1024,      # 5 MB
        max_daily_jobs=100,
        max_monthly_jobs=1000,
        max_files_per_job=1000,
        can_save_templates=True,
        can_use_api=True,
        priority_processing=True,
        max_saved_templates=50,
        max_total_storage_mb=500,
    ),
    
    "enterprise": UserLimits(
        max_pdf_size=100 * 1024 * 1024,    # 100 MB
        max_csv_size=25 * 1024 * 1024,     # 25 MB
        max_daily_jobs=1000,
        max_monthly_jobs=10000,
        max_files_per_job=10000,
        can_save_templates=True,
        can_use_api=True,
        priority_processing=True,
        max_saved_templates=500,
        max_total_storage_mb=5000,
    )
}


def get_user_limits(subscription_tier: str, custom_overrides=None) -> UserLimits:
    """
    Get user limits for a specific subscription tier with optional custom overrides.
    
    Args:
        subscription_tier: The user's subscription tier (free, basic, pro, enterprise)
        custom_overrides: Optional dict or User object with custom limit overrides
        
    Returns:
        UserLimits object with the appropriate limits (including any custom overrides)
        
    Raises:
        ValueError: If the subscription tier is not recognized
    """
    if subscription_tier not in SUBSCRIPTION_LIMITS:
        # Default to free tier if unknown
        subscription_tier = "free"
    
    # Start with base tier limits
    base_limits = SUBSCRIPTION_LIMITS[subscription_tier]
    
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
            max_daily_jobs=custom_overrides.custom_max_daily_jobs or base_limits.max_daily_jobs,
            max_monthly_jobs=custom_overrides.custom_max_monthly_jobs or base_limits.max_monthly_jobs,
            max_files_per_job=custom_overrides.custom_max_files_per_job or base_limits.max_files_per_job,
            can_save_templates=custom_overrides.custom_can_save_templates if custom_overrides.custom_can_save_templates is not None else base_limits.can_save_templates,
            can_use_api=custom_overrides.custom_can_use_api if custom_overrides.custom_can_use_api is not None else base_limits.can_use_api,
            priority_processing=base_limits.priority_processing,  # This remains tier-based for now
            max_saved_templates=base_limits.max_saved_templates,  # This remains tier-based for now
            max_total_storage_mb=base_limits.max_total_storage_mb,  # This remains tier-based for now
        )
    
    # Handle dict-style overrides (for future admin interfaces)
    elif isinstance(custom_overrides, dict):
        return UserLimits(
            max_pdf_size=custom_overrides.get('max_pdf_size', base_limits.max_pdf_size),
            max_csv_size=custom_overrides.get('max_csv_size', base_limits.max_csv_size),
            max_daily_jobs=custom_overrides.get('max_daily_jobs', base_limits.max_daily_jobs),
            max_monthly_jobs=custom_overrides.get('max_monthly_jobs', base_limits.max_monthly_jobs),
            max_files_per_job=custom_overrides.get('max_files_per_job', base_limits.max_files_per_job),
            can_save_templates=custom_overrides.get('can_save_templates', base_limits.can_save_templates),
            can_use_api=custom_overrides.get('can_use_api', base_limits.can_use_api),
            priority_processing=custom_overrides.get('priority_processing', base_limits.priority_processing),
            max_saved_templates=custom_overrides.get('max_saved_templates', base_limits.max_saved_templates),
            max_total_storage_mb=custom_overrides.get('max_total_storage_mb', base_limits.max_total_storage_mb),
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
        max_daily_jobs=1,                  # Very limited
        max_monthly_jobs=3,
        max_files_per_job=10,              # Small batches only
        can_save_templates=False,
        can_use_api=False,
        priority_processing=False,
        max_saved_templates=0,
        max_total_storage_mb=0,
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
