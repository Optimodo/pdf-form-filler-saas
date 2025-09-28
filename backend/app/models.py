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
    subscription_tier: str = Column(String(50), default="free", nullable=False)
    credits_remaining: int = Column(Integer, default=10, nullable=False)  # Free tier starts with 10 credits
    credits_used_this_month: int = Column(Integer, default=0, nullable=False)
    subscription_start_date: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    subscription_end_date: Optional[datetime] = Column(DateTime(timezone=True), nullable=True)
    
    # Custom limits override system (for VVIPs, enterprise clients, etc.)
    custom_limits_enabled: bool = Column(Boolean, default=False, nullable=False)
    custom_max_pdf_size: Optional[int] = Column(Integer, nullable=True)      # Override PDF size limit
    custom_max_csv_size: Optional[int] = Column(Integer, nullable=True)      # Override CSV size limit  
    custom_max_daily_jobs: Optional[int] = Column(Integer, nullable=True)    # Override daily job limit
    custom_max_monthly_jobs: Optional[int] = Column(Integer, nullable=True)  # Override monthly job limit
    custom_max_files_per_job: Optional[int] = Column(Integer, nullable=True) # Override files per job limit
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
    
    # Credits
    credits_consumed: int = Column(Integer, default=0, nullable=False)  # 0 for anonymous
    
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
