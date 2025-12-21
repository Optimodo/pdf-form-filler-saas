"""
Script to wipe all non-admin users and recreate test users with known passwords.

Run this from the backend container:
docker-compose exec backend python reset_test_users.py

WARNING: This will delete ALL users except those with is_superuser=True
"""
import asyncio
import uuid
from datetime import datetime
from app.database import get_async_session
from app.models import User
from sqlalchemy import select, delete
import bcrypt


async def reset_test_users():
    """Delete all non-admin users and create fresh test users."""
    
    # Hash password once for all test users using bcrypt directly
    test_password = "password"
    # Encode password to bytes and hash using bcrypt
    password_bytes = test_password.encode('utf-8')
    hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
    
    test_users = [
        {
            "email": "standard.user@test.com",
            "first_name": "Standard",
            "last_name": "User",
            "subscription_tier": "standard",
            "credits_remaining": 50,  # Purchased credits
            "credits_rollover": 0,
            "credits_used_total": 10,
            "is_active": True,
        },
        {
            "email": "standard.user2@test.com",
            "first_name": "Standard",
            "last_name": "User2",
            "subscription_tier": "standard",
            "credits_remaining": 100,  # Purchased credits
            "credits_rollover": 20,  # Rollover from previous month
            "credits_used_total": 5,
            "is_active": True,
        },
        {
            "email": "pro.user@test.com",
            "first_name": "Pro",
            "last_name": "User",
            "subscription_tier": "pro",
            "credits_remaining": 50,  # Additional purchased credits
            "credits_rollover": 0,
            "credits_used_total": 150,
            "is_active": True,
        },
        {
            "email": "enterprise.user@test.com",
            "first_name": "Enterprise",
            "last_name": "User",
            "subscription_tier": "enterprise",
            "credits_remaining": 200,  # Additional purchased credits
            "credits_rollover": 100,  # Rollover from previous month
            "credits_used_total": 500,
            "is_active": True,
        },
        {
            "email": "inactive.user@test.com",
            "first_name": "Inactive",
            "last_name": "User",
            "subscription_tier": "standard",
            "credits_remaining": 0,
            "credits_rollover": 0,
            "credits_used_total": 0,
            "is_active": False,
        },
        {
            "email": "custom.limits@test.com",
            "first_name": "Custom",
            "last_name": "Limits",
            "subscription_tier": "pro",
            "credits_remaining": 500,
            "credits_rollover": 0,
            "credits_used_total": 200,
            "is_active": True,
            "custom_limits_enabled": True,
            "custom_max_pdf_size": 50 * 1024 * 1024,  # 50MB
            "custom_max_csv_size": 10 * 1024 * 1024,  # 10MB
            "custom_max_pdfs_per_run": 500,  # Custom limit for PDFs per run
            "custom_limits_reason": "VIP client - special contract",
        },
        {
            "email": "john.doe@test.com",
            "first_name": "John",
            "last_name": "Doe",
            "subscription_tier": "standard",
            "credits_remaining": 25,
            "credits_rollover": 0,
            "credits_used_total": 3,
            "is_active": True,
        },
        {
            "email": "jane.smith@test.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "subscription_tier": "pro",
            "credits_remaining": 150,
            "credits_rollover": 50,
            "credits_used_total": 75,
            "is_active": True,
        },
        {
            "email": "test.user1@test.com",
            "first_name": "Test",
            "last_name": "User1",
            "subscription_tier": "standard",
            "credits_remaining": 0,  # Standard tier, no purchased credits
            "credits_rollover": 0,
            "credits_used_total": 0,
            "is_active": True,
        },
        {
            "email": "test.user2@test.com",
            "first_name": "Test",
            "last_name": "User2",
            "subscription_tier": "standard",
            "credits_remaining": 10,  # Standard tier with some purchased credits
            "credits_rollover": 0,
            "credits_used_total": 2,
            "is_active": True,
        },
    ]
    
    async for session in get_async_session():
        # Step 1: Delete all non-admin users
        print("🗑️  Deleting all non-admin users...")
        result = await session.execute(
            select(User).where(User.is_superuser == False)
        )
        users_to_delete = result.scalars().all()
        deleted_count = len(users_to_delete)
        
        for user in users_to_delete:
            await session.delete(user)
            print(f"   Deleted: {user.email}")
        
        await session.commit()
        print(f"✅ Deleted {deleted_count} non-admin users\n")
        
        # Step 2: Create new test users
        print("👥 Creating test users...")
        created_count = 0
        
        for user_data in test_users:
            # Create new user
            new_user = User(
                id=uuid.uuid4(),
                email=user_data["email"],
                hashed_password=hashed_password,
                is_active=user_data.get("is_active", True),
                is_superuser=False,
                is_verified=True,
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                subscription_tier=user_data.get("subscription_tier", "standard"),
                credits_remaining=user_data.get("credits_remaining", 0),  # Standard tier starts with 0
                credits_used_this_month=0,
                credits_rollover=user_data.get("credits_rollover", 0),
                credits_used_total=user_data.get("credits_used_total", 0),
                is_premium=user_data.get("subscription_tier") in ["pro", "enterprise"],
                custom_limits_enabled=user_data.get("custom_limits_enabled", False),
                custom_max_pdf_size=user_data.get("custom_max_pdf_size"),
                custom_max_csv_size=user_data.get("custom_max_csv_size"),
                custom_max_pdfs_per_run=user_data.get("custom_max_pdfs_per_run"),
                custom_can_save_templates=user_data.get("custom_can_save_templates"),
                custom_can_use_api=user_data.get("custom_can_use_api"),
                custom_limits_reason=user_data.get("custom_limits_reason"),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            session.add(new_user)
            created_count += 1
            tier = user_data.get("subscription_tier", "standard")
            print(f"✅ Created user: {user_data['email']} ({tier} tier)")
        
        await session.commit()
        
        print(f"\n📊 Summary:")
        print(f"   Deleted: {deleted_count} non-admin users")
        print(f"   Created: {created_count} test users")
        print(f"\n💡 All test users have password set to: {test_password}")
        print(f"   You can log in with any test user email and password '{test_password}'")
        print(f"\n📋 Test users created:")
        print(f"   - Standard tier users: 5 (standard.user@test.com, standard.user2@test.com, etc.)")
        print(f"   - Pro tier users: 3 (pro.user@test.com, jane.smith@test.com, custom.limits@test.com)")
        print(f"   - Enterprise tier users: 1 (enterprise.user@test.com)")
        print(f"   - Inactive user: 1 (inactive.user@test.com)")


if __name__ == "__main__":
    print("🚀 Resetting test users (deleting non-admin users and creating fresh test users)...\n")
    asyncio.run(reset_test_users())
    print("\n✨ Done!")
