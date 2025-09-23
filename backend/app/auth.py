"""
Authentication setup using FastAPI-Users with social login support.
"""
import os
import uuid
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyAccessTokenDatabase
from httpx_oauth.clients.google import GoogleOAuth2

from .database import get_async_session
from .models import User, OAuthAccount

# OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
# Apple OAuth configuration (to be added later)
# APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID", "")
# APPLE_CLIENT_SECRET = os.getenv("APPLE_CLIENT_SECRET", "")

# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# OAuth clients
google_oauth_client = GoogleOAuth2(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
)

# Apple OAuth client will be added later


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """
    User manager for handling user operations.
    """
    reset_password_token_secret = SECRET_KEY
    verification_token_secret = SECRET_KEY

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Actions to perform after user registration."""
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Actions to perform after forgot password request."""
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Actions to perform after verification request."""
        print(f"Verification requested for user {user.id}. Verification token: {token}")


async def get_user_db(session=Depends(get_async_session)):
    """Get user database dependency."""
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)


async def get_user_manager(user_db=Depends(get_user_db)):
    """Get user manager dependency."""
    yield UserManager(user_db)


# JWT authentication setup
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    """Get JWT strategy."""
    return JWTStrategy(secret=SECRET_KEY, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# Get current user dependencies
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
