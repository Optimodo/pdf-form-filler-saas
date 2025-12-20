"""
Pydantic schemas for API requests and responses.
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi_users import schemas
from pydantic import BaseModel, EmailStr


class UserRead(schemas.BaseUser[uuid.UUID]):
    """User read schema - what we return to the client."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    subscription_tier: str = "free"
    credits_remaining: int = 10
    credits_used_this_month: int = 0
    is_premium: bool = False
    is_superuser: bool = False  # Explicitly include superuser status
    last_login: Optional[datetime] = None
    created_at: datetime


class UserCreate(schemas.BaseUserCreate):
    """User creation schema - what we accept when creating a user."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserUpdate(schemas.BaseUserUpdate):
    """User update schema - what we accept when updating a user."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None


# Template schemas
class UserTemplateBase(BaseModel):
    """Base template schema."""
    name: str
    description: Optional[str] = None
    tags: Optional[str] = None
    is_favorite: bool = False


class UserTemplateCreate(UserTemplateBase):
    """Template creation schema."""
    pass


class UserTemplateUpdate(BaseModel):
    """Template update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    is_favorite: Optional[bool] = None


class UserTemplateRead(UserTemplateBase):
    """Template read schema."""
    id: uuid.UUID
    filename: str
    file_size: int
    usage_count: int
    created_at: datetime
    updated_at: datetime
    last_used: Optional[datetime] = None

    class Config:
        from_attributes = True


# Processing job schemas
class ProcessingJobRead(BaseModel):
    """Processing job read schema."""
    id: uuid.UUID
    template_filename: str
    csv_filename: str
    pdf_count: int
    successful_count: int
    failed_count: int
    processing_time_seconds: Optional[float] = None
    status: str
    credits_consumed: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    zip_filename: Optional[str] = None

    class Config:
        from_attributes = True


# Dashboard/statistics schemas
class UserDashboard(BaseModel):
    """User dashboard data."""
    user: UserRead
    recent_jobs: list[ProcessingJobRead]
    total_jobs: int
    total_pdfs_processed: int
    templates_count: int
    credits_used_this_month: int


class SubscriptionInfo(BaseModel):
    """Subscription information."""
    tier: str
    credits_remaining: int
    credits_used_this_month: int
    is_premium: bool
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None
