"""
Database models for the PDF Form Filler application.
"""
from datetime import datetime
from typing import Optional

from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyBaseOAuthAccountTableUUID
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .database import Base


class SubscriptionTier(Base):
    """
    Subscription tier configuration stored in database.
    Allows admin to manage tier names, limits, and add/remove tiers.
    """
    __tablename__ = "subscription_tiers"
    
    id: UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tier identification
    tier_key: str = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "free", "member", "pro", "enterprise"
    display_name: str = Column(String(100), nullable=False)  # e.g., "Free", "Member", "Pro", "Enterprise"
    description: Optional[str] = Column(Text, nullable=True)
    
    # File size limits (in bytes)
    max_pdf_size: int = Column(Integer, nullable=False)
    max_csv_size: int = Column(Integer, nullable=False)
    
    # Processing limits
    max_pdfs_per_run: int = Column(Integer, nullable=False)  # Maximum PDFs allowed in a single processing run
    
    # Feature access
    can_save_templates: bool = Column(Boolean, default=False, nullable=False)
    can_use_api: bool = Column(Boolean, default=False, nullable=False)
    priority_processing: bool = Column(Boolean, default=False, nullable=False)
    
    # Storage limits
    max_saved_templates: int = Column(Integer, default=0, nullable=False)
    max_total_storage_mb: int = Column(Integer, default=0, nullable=False)
    
    # Monthly credit allowance
    monthly_pdf_credits: int = Column(Integer, default=0, nullable=False)  # Monthly PDF credits for this tier
    
    # Tier ordering and visibility
    display_order: int = Column(Integer, default=0, nullable=False)  # For sorting in UI
    is_active: bool = Column(Boolean, default=True, nullable=False)  # Can disable tiers without deleting
    
    # Timestamps
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class User(SQLAlchemyBaseUserTableUUID, Base):
    """
    User model extending FastAPI-Users base model.
    
    Includes fields for subscription management and PDF processing.
    """
    __tablename__ = "users"
    
    # Basic user information
    first_name: Optional[str] = Column(String(100), nullable=True)
    last_name: Optional[str] = Column(String(100), nullable=True)
    
    # Subscription and billing
    subscription_tier: str = Column(String(50), default="standard", nullable=False)
    credits_remaining: int = Column(Integer, default=0, nullable=False)  # Top-up credits (never expire, standalone purchases) - Standard tier starts with 0
    credits_used_this_month: int = Column(Integer, default=0, nullable=False)  # Monthly subscription credits used
    credits_rollover: int = Column(Integer, default=0, nullable=False)  # Rollover credits from previous months
    credits_used_total: int = Column(Integer, default=0, nullable=False)  # Total credits used (lifetime)
    total_pdf_runs: int = Column(Integer, default=0, nullable=False)  # Total PDF processing runs (job count)
    subscription_start_date: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    subscription_end_date: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    
    # Custom limits override system (for VVIPs, enterprise clients, etc.)
    custom_limits_enabled: bool = Column(Boolean, default=False, nullable=False)
    custom_max_pdf_size: Optional[int] = Column(Integer, nullable=True)      # Override PDF size limit
    custom_max_csv_size: Optional[int] = Column(Integer, nullable=True)      # Override CSV size limit  
    custom_max_pdfs_per_run: Optional[int] = Column(Integer, nullable=True)  # Override max PDFs per run limit
    custom_can_save_templates: Optional[bool] = Column(Boolean, nullable=True) # Override template saving
    custom_can_use_api: Optional[bool] = Column(Boolean, nullable=True)      # Override API access
    custom_limits_reason: Optional[str] = Column(String(500), nullable=True) # Why custom limits were applied
    
    # Account status
    is_premium: bool = Column(Boolean, default=False, nullable=False)
    last_login: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    templates = relationship("UserTemplate", back_populates="user", cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="user", cascade="all, delete-orphan")
    uploaded_files = relationship("UploadedFile", back_populates="user", cascade="all, delete-orphan")
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")


class UserTemplate(Base):
    """
    User-uploaded PDF templates for reuse.
    """
    __tablename__ = "user_templates"
    
    id: UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: UUID = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Template information
    name: str = Column(String(255), nullable=False)
    filename: str = Column(String(255), nullable=False)
    file_path: str = Column(String(500), nullable=False)
    file_size: int = Column(Integer, nullable=False)
    
    # Metadata
    description: Optional[str] = Column(Text, nullable=True)
    tags: Optional[str] = Column(String(500), nullable=True)  # JSON or comma-separated
    is_favorite: bool = Column(Boolean, default=False, nullable=False)
    usage_count: int = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_used: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="templates")


class UploadedFile(Base):
    """
    Track uploaded template and CSV files.
    """
    __tablename__ = "uploaded_files"
    
    id: UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Optional[UUID] = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # NULL for anonymous uploads
    
    # File information
    original_filename: str = Column(String(255), nullable=False)
    stored_filename: str = Column(String(255), nullable=False)  # Our internal filename with date/user reference
    file_path: str = Column(String(500), nullable=False)  # Full path to stored file
    file_type: str = Column(String(10), nullable=False)  # 'pdf' or 'csv'
    file_size_bytes: int = Column(Integer, nullable=False)
    
    # File hash for deduplication (optional)
    file_hash: Optional[str] = Column(String(64), nullable=True)  # SHA-256 hash
    
    # Metadata
    upload_ip: Optional[str] = Column(String(45), nullable=True)  # For anonymous tracking
    mime_type: Optional[str] = Column(String(100), nullable=True)
    
    # Timestamps with ddmmyyyy format preference
    uploaded_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking
    usage_count: int = Column(Integer, default=0, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="uploaded_files")
    processing_jobs_as_template = relationship("ProcessingJob", foreign_keys="ProcessingJob.template_file_id", back_populates="template_file")
    processing_jobs_as_csv = relationship("ProcessingJob", foreign_keys="ProcessingJob.csv_file_id", back_populates="csv_file")


class ProcessingJob(Base):
    """
    Track PDF processing jobs for analytics and user history.
    """
    __tablename__ = "processing_jobs"
    
    id: UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Optional[UUID] = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # NULL for anonymous
    template_file_id: Optional[UUID] = Column(UUID(as_uuid=True), ForeignKey("uploaded_files.id", ondelete="SET NULL"), nullable=True)
    csv_file_id: Optional[UUID] = Column(UUID(as_uuid=True), ForeignKey("uploaded_files.id", ondelete="SET NULL"), nullable=True)
    
    # Job details
    template_filename: str = Column(String(255), nullable=False)  # Original template name
    csv_filename: str = Column(String(255), nullable=False)  # Original CSV name
    pdf_count: int = Column(Integer, nullable=False)
    successful_count: int = Column(Integer, default=0, nullable=False)
    failed_count: int = Column(Integer, default=0, nullable=False)
    
    # Processing details
    processing_time_seconds: Optional[float] = Column(String(20), nullable=True)  # Store as string to avoid precision issues
    file_size_mb: Optional[float] = Column(String(20), nullable=True)
    zip_filename: Optional[str] = Column(String(255), nullable=True)
    zip_file_path: Optional[str] = Column(String(500), nullable=True)
    
    # Status tracking
    status: str = Column(String(50), default="completed", nullable=False)  # completed, failed, processing
    error_message: Optional[str] = Column(Text, nullable=True)
    
    # Credits - detailed tracking of credit sources
    total_credits_consumed: int = Column(Integer, default=0, nullable=False)  # Total credits used for this job
    subscription_credits_used: int = Column(Integer, default=0, nullable=False)  # Credits from monthly allowance
    rollover_credits_used: int = Column(Integer, default=0, nullable=False)  # Credits from rollover balance
    topup_credits_used: int = Column(Integer, default=0, nullable=False)  # Credits from top-up balance
    
    # Processing metadata
    session_id: Optional[str] = Column(String(100), nullable=True)  # For grouping related operations
    processing_ip: Optional[str] = Column(String(45), nullable=True)
    
    # Timestamps (using ddmmyyyy format in filename generation)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="processing_jobs")
    template_file = relationship("UploadedFile", foreign_keys=[template_file_id], back_populates="processing_jobs_as_template")
    csv_file = relationship("UploadedFile", foreign_keys=[csv_file_id], back_populates="processing_jobs_as_csv")


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    """
    OAuth account model for social login integration.
    """
    __tablename__ = "oauth_accounts"
    
    # Override the user_id foreign key to point to the correct table
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="oauth_accounts")


class ActivityLog(Base):
    """
    Comprehensive audit log for all system activities.
    
    Tracks user actions, admin changes, system events, PDF processing,
    subscriptions, payments, and any other significant activities.
    """
    __tablename__ = "activity_logs"
    
    id: UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Activity categorization
    activity_type: str = Column(String(50), nullable=False, index=True)  # e.g., "user_registered", "admin_updated_limits", "pdf_processed", "subscription_changed"
    category: str = Column(String(50), nullable=False, index=True)  # e.g., "user", "admin", "system", "payment", "pdf"
    
    # User identification (can be None for system/admin-only actions)
    user_id: Optional[UUID] = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    target_user_id: Optional[UUID] = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)  # For admin actions on other users
    
    # Actor identification (who performed the action)
    actor_id: Optional[UUID] = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Admin who made the change
    actor_type: str = Column(String(20), default="user", nullable=False)  # "user", "admin", "system"
    
    # Activity details
    action: str = Column(String(100), nullable=False)  # Brief description: "Updated subscription tier", "Processed PDF batch"
    description: Optional[str] = Column(Text, nullable=True)  # Detailed description
    reason: Optional[str] = Column(Text, nullable=True)  # Reason provided (e.g., admin reason for custom limits)
    
    # Metadata stored as JSON for flexibility
    additional_metadata: Optional[str] = Column(Text, nullable=True)  # JSON string with additional data
    
    # Request/network metadata
    ip_address: Optional[str] = Column(String(45), nullable=True, index=True)  # IPv4 or IPv6
    user_agent: Optional[str] = Column(String(500), nullable=True)  # Browser/user agent string
    country: Optional[str] = Column(String(2), nullable=True, index=True)  # ISO country code (can be derived from IP later)
    
    # Related entities (flexible foreign keys)
    related_job_id: Optional[UUID] = Column(UUID(as_uuid=True), ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True)
    related_tier_id: Optional[UUID] = Column(UUID(as_uuid=True), ForeignKey("subscription_tiers.id", ondelete="SET NULL"), nullable=True)
    
    # Changes tracking (for admin actions - what changed)
    changes: Optional[str] = Column(Text, nullable=True)  # JSON string with before/after values
    
    # Timestamp
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="activity_logs")
    target_user = relationship("User", foreign_keys=[target_user_id], backref="targeted_activity_logs")
    actor = relationship("User", foreign_keys=[actor_id], backref="actor_activity_logs")
