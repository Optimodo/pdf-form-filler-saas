"""
Authentication routes using FastAPI-Users.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi_users import fastapi_users
from httpx_oauth.clients.google import GoogleOAuth2

from ..auth import auth_backend, fastapi_users, google_oauth_client, current_active_user, SECRET_KEY, get_user_manager, UserManager
from ..schemas import UserRead, UserCreate, UserUpdate
from ..models import User, OAuthAccount
from ..database import get_async_session
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

# Include authentication routes
# These automatically create endpoints like:
# POST /auth/register - Register new user
# POST /auth/jwt/login - Login with email/password
# POST /auth/jwt/logout - Logout
# POST /auth/forgot-password - Request password reset
# POST /auth/reset-password - Reset password with token
router.include_router(
    fastapi_users.get_auth_router(auth_backend), 
    prefix="/auth/jwt", 
    tags=["auth"]
)

router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# Custom OAuth implementation for better frontend integration
import httpx_oauth.errors
import jwt
import time

def generate_state_token(secret: str, lifetime_seconds: int = 3600):
    """Generate a state token for OAuth flow."""
    data = {
        "aud": "fastapi-users:oauth-state",
        "exp": time.time() + lifetime_seconds,
    }
    return jwt.encode(data, secret, algorithm="HS256")

@router.get("/auth/google/authorize")
async def google_oauth_authorize():
    """Start Google OAuth flow."""
    try:
        # Use simple OAuth flow without PKCE
        authorization_url = await google_oauth_client.get_authorization_url(
            redirect_uri="http://localhost:8000/api/auth/google/callback",
            state=generate_state_token(SECRET_KEY),
            scope=["openid", "email", "profile"]  # Explicitly set scopes
        )
        return {"authorization_url": authorization_url}
    except Exception as e:
        print(f"OAuth authorize error: {e}")
        return {"error": str(e)}

@router.get("/auth/google/callback")
async def google_oauth_callback(request: Request, session: AsyncSession = Depends(get_async_session)):
    """Handle Google OAuth callback and redirect to frontend."""
    try:
        # Debug: Print all query parameters
        print(f"OAuth callback received parameters: {dict(request.query_params)}")
        
        # Get the authorization code and state from the URL
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")
        
        if error:
            print(f"OAuth error from Google: {error}")
            return RedirectResponse(url=f"http://localhost:3000/auth/google/callback?error=google_{error}")
        
        if not code:
            print("No authorization code received from Google")
            return RedirectResponse(url="http://localhost:3000/auth/google/callback?error=no_code")
        
        # Manual token exchange to avoid PKCE issues
        import httpx
        
        token_data = {
            "code": code,
            "client_id": google_oauth_client.client_id,
            "client_secret": google_oauth_client.client_secret,
            "redirect_uri": "http://localhost:8000/api/auth/google/callback",
            "grant_type": "authorization_code",
        }
        
        async with httpx.AsyncClient() as client:
            # Get access token
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_data,
                headers={"Accept": "application/json"}
            )
            
            if token_response.status_code != 200:
                raise Exception(f"Token exchange failed: {token_response.text}")
                
            access_token = token_response.json()
            
            # Get user info from Google (including profile data)
            user_id, user_email = await google_oauth_client.get_id_email(access_token["access_token"])
            
            # Get additional profile info (name, etc.) - within the same client context
            profile_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token['access_token']}"}
            )
            profile_data = profile_response.json() if profile_response.status_code == 200 else {}
        
        # Extract profile information (outside client context)
        first_name = profile_data.get("given_name")
        last_name = profile_data.get("family_name")
        picture_url = profile_data.get("picture")
        
        # Manual user creation/lookup to avoid async context issues
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        import uuid
        from datetime import datetime
        
        # Check if user already exists by email
        stmt = select(User).where(User.email == user_email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            print("Creating new user...")
            # Create new user with Google profile data
            user = User(
                id=uuid.uuid4(),
                email=user_email,
                hashed_password="",  # OAuth users don't have passwords
                is_active=True,
                is_superuser=False,
                is_verified=True,  # OAuth users are pre-verified
                first_name=first_name,  # From Google profile
                last_name=last_name,   # From Google profile
                subscription_tier="free",
                credits_remaining=10,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"Created new user with ID: {user.id}")
            
            # Create OAuth account record for new user
            oauth_account = OAuthAccount(
                oauth_name="google",
                account_id=user_id,
                account_email=user_email,
                access_token=access_token["access_token"],
                expires_at=access_token.get("expires_in"),
                refresh_token=access_token.get("refresh_token"),
                user_id=user.id
            )
            session.add(oauth_account)
            await session.commit()
            print("Created OAuth account record")
        else:
            print(f"Found existing user: {user.id} - {user.email}")
            
            # Check if OAuth account already exists for this user
            oauth_stmt = select(OAuthAccount).where(
                OAuthAccount.user_id == user.id,
                OAuthAccount.oauth_name == "google"
            )
            oauth_result = await session.execute(oauth_stmt)
            existing_oauth = oauth_result.scalar_one_or_none()
            
            if not existing_oauth:
                print("Creating OAuth account record for existing user...")
                oauth_account = OAuthAccount(
                    oauth_name="google",
                    account_id=user_id,
                    account_email=user_email,
                    access_token=access_token["access_token"],
                    expires_at=access_token.get("expires_in"),
                    refresh_token=access_token.get("refresh_token"),
                    user_id=user.id
                )
                session.add(oauth_account)
                await session.commit()
                print("Created OAuth account record for existing user")
            else:
                print("OAuth account already exists")
                
            # Update profile data if missing and we have it from Google
            if (not user.first_name and first_name) or (not user.last_name and last_name):
                print("Updating user profile with Google data...")
                if not user.first_name and first_name:
                    user.first_name = first_name
                if not user.last_name and last_name:
                    user.last_name = last_name
                await session.commit()
                print("Updated user profile")
        
        print("Generating JWT token...")
        # Generate JWT token for the user
        strategy = auth_backend.get_strategy()
        token = await strategy.write_token(user)
        print(f"Generated token (first 20 chars): {token[:20]}...")
        
        # Commit the session to ensure no rollback
        await session.commit()
        print("Session committed successfully")
        
        # Redirect to frontend with the token
        redirect_url = f"http://localhost:3000/auth/google/callback?token={token}"
        print(f"Redirecting to: {redirect_url[:80]}...")
        return RedirectResponse(url=redirect_url)
            
    except Exception as e:
        print(f"OAuth callback error: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        # Include the error message in the redirect for better debugging
        error_msg = str(e).replace(" ", "_").replace(":", "_")[:100]  # Sanitize for URL
        return RedirectResponse(url=f"http://localhost:3000/auth/google/callback?error={error_msg}")

# Apple OAuth will be added later - need proper Apple client setup


@router.get("/auth/me", response_model=UserRead)
async def get_current_user(user: User = Depends(current_active_user)):
    """Get current authenticated user."""
    return user


@router.get("/auth/protected")
async def protected_route(user: User = Depends(current_active_user)):
    """Example protected route."""
    return {"message": f"Hello {user.email}! This is a protected route."}
