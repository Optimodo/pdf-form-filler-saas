"""
Quick script to create test users for admin panel testing.

Run this from the backend container:
docker-compose exec backend python create_test_users.py
"""
import asyncio
import uuid
from datetime import datetime
from app.database import get_async_session
from app.models import User
from sqlalchemy import select


async def create_test_users():
    """Create a variety of test users for admin testing."""
    
    test_users = [
        {
            "email": "free.user@test.com",
            "first_name": "Free",
            "last_name": "User",
            "subscription_tier": "free",
            "credits_remaining": 5,
            "is_active": True,
        },
        {
            "email": "member.user@test.com",
            "first_name": "Member",
            "last_name": "User",
            "subscription_tier": "member",
            "credits_remaining": 50,
            "is_active": True,
        },
        {
            "email": "pro.user@test.com",
            "first_name": "Pro",
            "last_name": "User",
            "subscription_tier": "pro",
            "credits_remaining": 200,
            "is_active": True,
        },
        {
            "email": "enterprise.user@test.com",
            "first_name": "Enterprise",
            "last_name": "User",
            "subscription_tier": "enterprise",
            "credits_remaining": 1000,
            "is_active": True,
        },
        {
            "email": "inactive.user@test.com",
            "first_name": "Inactive",
            "last_name": "User",
            "subscription_tier": "free",
            "credits_remaining": 0,
            "is_active": False,
        },
        {
            "email": "custom.limits@test.com",
            "first_name": "Custom",
            "last_name": "Limits",
            "subscription_tier": "pro",
            "credits_remaining": 500,
            "is_active": True,
            "custom_limits_enabled": True,
            "custom_max_pdf_size": 50 * 1024 * 1024,  # 50MB
            "custom_max_csv_size": 10 * 1024 * 1024,  # 10MB
            "custom_max_daily_jobs": 200,
            "custom_limits_reason": "VIP client - special contract",
        },
        {
            "email": "john.doe@test.com",
            "first_name": "John",
            "last_name": "Doe",
            "subscription_tier": "member",
            "credits_remaining": 25,
            "is_active": True,
        },
        {
            "email": "jane.smith@test.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "subscription_tier": "pro",
            "credits_remaining": 150,
            "is_active": True,
        },
        {
            "email": "test.user1@test.com",
            "first_name": "Test",
            "last_name": "User1",
            "subscription_tier": "free",
            "credits_remaining": 8,
            "is_active": True,
        },
        {
            "email": "test.user2@test.com",
            "first_name": "Test",
            "last_name": "User2",
            "subscription_tier": "free",
            "credits_remaining": 2,
            "is_active": True,
        },
    ]
    
    async for session in get_async_session():
        created_count = 0
        skipped_count = 0
        
        for user_data in test_users:
            # Check if user already exists
            result = await session.execute(
                select(User).where(User.email == user_data["email"])
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"⏭️  User {user_data['email']} already exists, skipping...")
                skipped_count += 1
                continue
            
            # Create new user
            new_user = User(
                id=uuid.uuid4(),
                email=user_data["email"],
                hashed_password="",  # Test users don't need passwords (use OAuth or set later)
                is_active=user_data.get("is_active", True),
                is_superuser=False,
                is_verified=True,
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                subscription_tier=user_data.get("subscription_tier", "free"),
                credits_remaining=user_data.get("credits_remaining", 10),
                credits_used_this_month=0,
                is_premium=user_data.get("subscription_tier") in ["pro", "enterprise"],
                custom_limits_enabled=user_data.get("custom_limits_enabled", False),
                custom_max_pdf_size=user_data.get("custom_max_pdf_size"),
                custom_max_csv_size=user_data.get("custom_max_csv_size"),
                custom_max_daily_jobs=user_data.get("custom_max_daily_jobs"),
                custom_limits_reason=user_data.get("custom_limits_reason"),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            session.add(new_user)
            created_count += 1
            print(f"✅ Created user: {user_data['email']} ({user_data.get('subscription_tier', 'free')} tier)")
        
        await session.commit()
        
        print(f"\n📊 Summary:")
        print(f"   Created: {created_count} users")
        print(f"   Skipped: {skipped_count} users (already exist)")
        print(f"\n💡 Note: These test users don't have passwords set.")
        print(f"   They can only log in via OAuth or you can set passwords manually.")


if __name__ == "__main__":
    print("🚀 Creating test users...\n")
    asyncio.run(create_test_users())
    print("\n✨ Done!")

