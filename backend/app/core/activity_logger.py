"""
Activity Logging Service

Centralized service for recording all system activities including:
- User actions (registration, login, PDF processing)
- Admin actions (user modifications, tier changes)
- System events
- Payment/subscription events (future)
"""
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from ..models import ActivityLog, User
from ..database import get_async_session

logger = logging.getLogger(__name__)


class ActivityLogger:
    """
    Centralized activity logging service.
    
    Provides methods to log various types of activities with metadata
    including IP addresses, user agents, and other contextual information.
    """
    
    @staticmethod
    async def log_activity(
        session: AsyncSession,
        activity_type: str,
        category: str,
        action: str,
        user_id: Optional[UUID] = None,
        target_user_id: Optional[UUID] = None,
        actor_id: Optional[UUID] = None,
        actor_type: str = "user",
        description: Optional[str] = None,
        reason: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        country: Optional[str] = None,
        related_job_id: Optional[UUID] = None,
        related_tier_id: Optional[UUID] = None,
    ) -> ActivityLog:
        """
        Log an activity to the database.
        
        Args:
            session: Database session
            activity_type: Type of activity (e.g., "user_registered", "admin_updated_limits")
            category: Category (e.g., "user", "admin", "system", "payment", "pdf")
            action: Brief action description
            user_id: ID of user who the activity relates to
            target_user_id: ID of user being acted upon (for admin actions)
            actor_id: ID of user who performed the action (for admin actions)
            actor_type: Type of actor ("user", "admin", "system")
            description: Detailed description
            reason: Reason provided (e.g., admin reason for changes)
            metadata: Additional metadata as dictionary (will be JSON-encoded)
            changes: Before/after changes as dictionary (will be JSON-encoded)
            ip_address: IP address of requester
            user_agent: Browser/user agent string
            country: ISO country code
            related_job_id: Related processing job ID
            related_tier_id: Related subscription tier ID
            
        Returns:
            Created ActivityLog instance
        """
        try:
            log_entry = ActivityLog(
                activity_type=activity_type,
                category=category,
                action=action,
                user_id=user_id,
                target_user_id=target_user_id,
                actor_id=actor_id,
                actor_type=actor_type,
            description=description,
            reason=reason,
            additional_metadata=json.dumps(additional_metadata) if additional_metadata else None,
            changes=json.dumps(changes) if changes else None,
                ip_address=ip_address,
                user_agent=user_agent,
                country=country,
                related_job_id=related_job_id,
                related_tier_id=related_tier_id,
            )
            
            session.add(log_entry)
            await session.commit()
            await session.refresh(log_entry)
            
            return log_entry
        except Exception as e:
            logger.error(f"Failed to log activity: {e}", exc_info=True)
            await session.rollback()
            raise
    
    @staticmethod
    def extract_request_metadata(request: Optional[Request]) -> Dict[str, Optional[str]]:
        """
        Extract metadata from FastAPI request object.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            Dictionary with ip_address, user_agent, and other metadata
        """
        if not request:
            return {
                "ip_address": None,
                "user_agent": None,
            }
        
        # Get IP address (check for proxy headers)
        ip_address = None
        if request.client:
            ip_address = request.client.host
        
        # Check common proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            ip_address = real_ip
        
        # Get user agent
        user_agent = request.headers.get("User-Agent")
        
        return {
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
    
    # Convenience methods for common activity types
    
    @staticmethod
    async def log_user_registration(
        session: AsyncSession,
        user_id: UUID,
        request: Optional[Request] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> ActivityLog:
        """Log user registration."""
        req_meta = ActivityLogger.extract_request_metadata(request)
        return await ActivityLogger.log_activity(
            session=session,
            activity_type="user_registered",
            category="user",
            action="User registered",
            user_id=user_id,
        description=f"New user registered",
        additional_metadata=additional_metadata,
            ip_address=req_meta["ip_address"],
            user_agent=req_meta["user_agent"],
        )
    
    @staticmethod
    async def log_user_login(
        session: AsyncSession,
        user_id: UUID,
        request: Optional[Request] = None,
        method: str = "email",  # "email", "google", etc.
    ) -> ActivityLog:
        """Log user login."""
        req_meta = ActivityLogger.extract_request_metadata(request)
        return await ActivityLogger.log_activity(
            session=session,
            activity_type="user_logged_in",
            category="user",
            action=f"User logged in via {method}",
            user_id=user_id,
            additional_metadata={"method": method},
            ip_address=req_meta["ip_address"],
            user_agent=req_meta["user_agent"],
        )
    
    @staticmethod
    async def log_pdf_processed(
        session: AsyncSession,
        user_id: Optional[UUID],
        job_id: UUID,
        pdf_count: int,
        successful_count: int,
        request: Optional[Request] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> ActivityLog:
        """Log PDF processing completion."""
        req_meta = ActivityLogger.extract_request_metadata(request)
        user_type = "registered" if user_id else "anonymous"
        return await ActivityLogger.log_activity(
            session=session,
            activity_type="pdf_processed",
            category="pdf",
            action=f"Processed {pdf_count} PDFs ({successful_count} successful)",
            user_id=user_id,
            description=f"{user_type.capitalize()} user processed PDF batch",
            additional_metadata={
                "pdf_count": pdf_count,
                "successful_count": successful_count,
                "user_type": user_type,
                **(additional_metadata or {}),
            },
            related_job_id=job_id,
            ip_address=req_meta["ip_address"],
            user_agent=req_meta["user_agent"],
        )
    
    @staticmethod
    async def log_admin_action(
        session: AsyncSession,
        admin_id: UUID,
        action: str,
        target_user_id: Optional[UUID] = None,
        activity_type: str = "admin_action",
        description: Optional[str] = None,
        reason: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        additional_metadata: Optional[Dict[str, Any]] = None,
        related_tier_id: Optional[UUID] = None,
    ) -> ActivityLog:
        """Log admin action."""
        req_meta = ActivityLogger.extract_request_metadata(request)
        return await ActivityLogger.log_activity(
            session=session,
            activity_type=activity_type,
            category="admin",
            action=action,
            target_user_id=target_user_id,
            actor_id=admin_id,
            actor_type="admin",
            description=description,
            reason=reason,
            changes=changes,
            additional_metadata=additional_metadata,
            ip_address=req_meta["ip_address"],
            user_agent=req_meta["user_agent"],
            related_tier_id=related_tier_id,
        )
    
    @staticmethod
    async def log_tier_updated(
        session: AsyncSession,
        admin_id: UUID,
        tier_id: UUID,
        action: str,
        changes: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> ActivityLog:
        """Log subscription tier update."""
        req_meta = ActivityLogger.extract_request_metadata(request)
        return await ActivityLogger.log_activity(
            session=session,
            activity_type="tier_updated",
            category="admin",
            action=action,
            actor_id=admin_id,
            actor_type="admin",
            description=f"Subscription tier updated",
            changes=changes,
            related_tier_id=tier_id,
            ip_address=req_meta["ip_address"],
            user_agent=req_meta["user_agent"],
        )
    
    @staticmethod
    async def log_subscription_change(
        session: AsyncSession,
        user_id: UUID,
        old_tier: str,
        new_tier: str,
        reason: Optional[str] = None,
        actor_id: Optional[UUID] = None,
        request: Optional[Request] = None,
    ) -> ActivityLog:
        """Log subscription tier change for a user."""
        req_meta = ActivityLogger.extract_request_metadata(request)
        actor_type = "admin" if actor_id else "user"
        return await ActivityLogger.log_activity(
            session=session,
            activity_type="subscription_changed",
            category="user" if not actor_id else "admin",
            action=f"Subscription changed from {old_tier} to {new_tier}",
            user_id=user_id,
            actor_id=actor_id,
            actor_type=actor_type,
            description=f"User subscription tier changed",
            reason=reason,
            changes={"old_tier": old_tier, "new_tier": new_tier},
            ip_address=req_meta["ip_address"],
            user_agent=req_meta["user_agent"],
        )


# Singleton instance
activity_logger = ActivityLogger()
