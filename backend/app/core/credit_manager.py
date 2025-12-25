"""
Credit management system for PDF processing.

Handles credit checking, allocation, and tracking from multiple sources:
1. Monthly subscription allowance (monthly_pdf_credits - credits_used_this_month)
2. Rollover credits (credits_rollover)
3. Top-up credits (credits_remaining - never expire)
"""
import csv
import logging
from typing import Dict, Optional, Tuple
from io import StringIO
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import User, SubscriptionTier
from ..core.user_limits import get_user_limits_from_user

logger = logging.getLogger(__name__)


def count_csv_rows(csv_content: bytes) -> int:
    """
    Count the number of rows in a CSV file (excluding header).
    
    Args:
        csv_content: CSV file content as bytes
        
    Returns:
        Number of data rows (excluding header)
    """
    try:
        # Decode CSV content
        csv_text = csv_content.decode('utf-8-sig')  # Handle BOM if present
        csv_reader = csv.reader(StringIO(csv_text))
        
        # Skip header and count rows
        next(csv_reader, None)  # Skip header
        row_count = sum(1 for _ in csv_reader)
        
        return row_count
    except Exception as e:
        logger.error(f"Error counting CSV rows: {str(e)}")
        raise ValueError(f"Failed to parse CSV file: {str(e)}")


async def check_credits_available(
    session: AsyncSession,
    user: User,
    required_credits: int
) -> Tuple[bool, Dict[str, int], str]:
    """
    Check if user has enough credits for a job and calculate available credits.
    
    Args:
        session: Database session
        user: User object
        required_credits: Number of credits needed for the job
        
    Returns:
        Tuple of (has_enough_credits, available_credits_dict, error_message)
        available_credits_dict contains:
        - monthly_available: Available from monthly allowance
        - rollover_available: Available from rollover balance
        - topup_available: Available from top-up balance
        - total_available: Total available credits
    """
    # Get tier limits to determine monthly allowance
    tier_limits = get_user_limits_from_user(user)
    
    # Get tier from database to get monthly_pdf_credits
    tier_result = await session.execute(
        select(SubscriptionTier).where(
            SubscriptionTier.tier_key == user.subscription_tier,
            SubscriptionTier.is_active == True
        )
    )
    tier = tier_result.scalar_one_or_none()
    
    if not tier:
        return False, {}, f"Subscription tier '{user.subscription_tier}' not found"
    
    monthly_allowance = tier.monthly_pdf_credits
    monthly_used = user.credits_used_this_month
    
    # Calculate available monthly credits (can be negative if user exceeded monthly limit)
    monthly_available = max(0, monthly_allowance - monthly_used)
    
    # Check if monthly would be exhausted/exceeded by this job
    monthly_exhausted = monthly_used >= monthly_allowance
    would_exceed_monthly = (monthly_used + required_credits) > monthly_allowance
    
    rollover_available = user.credits_rollover
    topup_available = user.credits_remaining
    
    # Total available includes monthly (if not exhausted), rollover, and topup
    if monthly_exhausted or would_exceed_monthly:
        # Monthly not available, only count rollover and topup
        total_available = rollover_available + topup_available
    else:
        # Monthly available, count all sources
        total_available = monthly_available + rollover_available + topup_available
    
    available_credits = {
        'monthly_available': monthly_available,
        'rollover_available': rollover_available,
        'topup_available': topup_available,
        'total_available': total_available,
    }
    
    has_enough = total_available >= required_credits
    
    if not has_enough:
        error_msg = (
            f"Insufficient credits. Required: {required_credits}, "
            f"Available: {total_available} "
            f"(Monthly: {monthly_available}, Rollover: {rollover_available}, Top-up: {topup_available})"
        )
    else:
        error_msg = ""
    
    return has_enough, available_credits, error_msg


async def calculate_credit_usage(
    session: AsyncSession,
    user: User,
    required_credits: int
) -> Dict[str, int]:
    """
    Calculate how to allocate credits from different sources for a job.
    
    Logic:
    - If monthly allowance is available and sufficient, use it first
    - If monthly is exhausted or job would exceed monthly limit, use rollover then topup
    - credits_used_this_month tracks total usage regardless of source (can exceed monthly limit)
    
    Args:
        session: Database session
        user: User object
        required_credits: Number of credits needed
        
    Returns:
        Dictionary with credit usage breakdown:
        - subscription_credits_used: From monthly allowance (0 if monthly exhausted)
        - rollover_credits_used: From rollover balance
        - topup_credits_used: From top-up balance
        - total_credits_consumed: Total credits used (should equal required_credits)
    """
    # Get tier to determine monthly allowance
    tier_result = await session.execute(
        select(SubscriptionTier).where(
            SubscriptionTier.tier_key == user.subscription_tier,
            SubscriptionTier.is_active == True
        )
    )
    tier = tier_result.scalar_one_or_none()
    
    monthly_allowance = tier.monthly_pdf_credits if tier else 0
    monthly_used = user.credits_used_this_month
    
    # Calculate available monthly credits
    monthly_available = max(0, monthly_allowance - monthly_used)
    
    # Check if monthly allowance is exhausted or if job would exceed monthly limit
    monthly_exhausted = monthly_used >= monthly_allowance
    would_exceed_monthly = (monthly_used + required_credits) > monthly_allowance
    
    rollover_available = user.credits_rollover
    topup_available = user.credits_remaining
    
    subscription_credits_used = 0
    rollover_credits_used = 0
    topup_credits_used = 0
    
    # Decision logic: use monthly if available and sufficient, otherwise use rollover/topup
    if monthly_exhausted or would_exceed_monthly:
        # Monthly is exhausted or job would exceed monthly limit - use rollover/topup only
        remaining_needed = required_credits
        
        # Try rollover first
        rollover_credits_used = min(remaining_needed, rollover_available)
        remaining_needed -= rollover_credits_used
        
        # Then use topup
        topup_credits_used = min(remaining_needed, topup_available)
    else:
        # Monthly is available and sufficient - use monthly only
        subscription_credits_used = required_credits
    
    total_consumed = subscription_credits_used + rollover_credits_used + topup_credits_used
    
    return {
        'subscription_credits_used': subscription_credits_used,
        'rollover_credits_used': rollover_credits_used,
        'topup_credits_used': topup_credits_used,
        'total_credits_consumed': total_consumed,
    }


async def apply_credit_usage(
    session: AsyncSession,
    user: User,
    credit_usage: Dict[str, int]
) -> None:
    """
    Update user's credit balances based on credit usage.
    
    Args:
        session: Database session
        user: User object to update (must be attached to session)
        credit_usage: Dictionary from calculate_credit_usage()
    """
    logger = logging.getLogger(__name__)
    
    # Log before changes
    logger.info(
        f"Applying credit usage for user {user.email}: "
        f"Before - remaining: {user.credits_remaining}, "
        f"rollover: {user.credits_rollover}, "
        f"used_this_month: {user.credits_used_this_month}, "
        f"used_total: {user.credits_used_total}"
    )
    
    # Update credits_used_this_month with TOTAL credits consumed (regardless of source)
    # This allows tracking that user exceeded monthly limit
    user.credits_used_this_month += credit_usage['total_credits_consumed']
    
    # Update rollover balance (deduct what was used)
    user.credits_rollover -= credit_usage['rollover_credits_used']
    if user.credits_rollover < 0:
        user.credits_rollover = 0  # Safety check
    
    # Update top-up balance (deduct what was used)
    user.credits_remaining -= credit_usage['topup_credits_used']
    if user.credits_remaining < 0:
        user.credits_remaining = 0  # Safety check
    
    # Update total credits used (lifetime)
    user.credits_used_total += credit_usage['total_credits_consumed']
    
    # Increment total PDF runs counter
    user.total_pdf_runs += 1
    
    # Commit changes to database
    await session.commit()
    
    # Refresh to verify changes were saved
    await session.refresh(user)
    
    # Log after changes
    logger.info(
        f"Credit usage applied for user {user.email}: "
        f"After - remaining: {user.credits_remaining}, "
        f"rollover: {user.credits_rollover}, "
        f"used_this_month: {user.credits_used_this_month}, "
        f"used_total: {user.credits_used_total}"
    )




