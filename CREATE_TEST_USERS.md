# Creating Test Users

Quick guide to create test users for admin panel testing.

## Option 1: Using Python Script (Recommended)

1. Run the script from the backend container:
   ```bash
   docker-compose exec backend python create_test_users.py
   ```

This will create 10 test users with different subscription tiers and properties.

## Option 2: Using SQL Directly

Connect to the database and run:

```sql
-- Free tier users
INSERT INTO users (id, email, hashed_password, is_active, is_superuser, is_verified, subscription_tier, credits_remaining, created_at, updated_at)
VALUES 
  (gen_random_uuid(), 'free.user@test.com', '', true, false, true, 'free', 5, now(), now()),
  (gen_random_uuid(), 'test.user1@test.com', '', true, false, true, 'free', 8, now(), now());

-- Basic tier users
INSERT INTO users (id, email, hashed_password, is_active, is_superuser, is_verified, subscription_tier, credits_remaining, created_at, updated_at)
VALUES 
  (gen_random_uuid(), 'basic.user@test.com', '', true, false, true, 'basic', 50, now(), now()),
  (gen_random_uuid(), 'john.doe@test.com', '', true, false, true, 'basic', 25, now(), now());

-- Pro tier users
INSERT INTO users (id, email, hashed_password, is_active, is_superuser, is_verified, subscription_tier, credits_remaining, is_premium, created_at, updated_at)
VALUES 
  (gen_random_uuid(), 'pro.user@test.com', '', true, false, true, 'pro', 200, true, now(), now()),
  (gen_random_uuid(), 'jane.smith@test.com', '', true, false, true, 'pro', 150, true, now(), now());

-- Enterprise tier user
INSERT INTO users (id, email, hashed_password, is_active, is_superuser, is_verified, subscription_tier, credits_remaining, is_premium, created_at, updated_at)
VALUES 
  (gen_random_uuid(), 'enterprise.user@test.com', '', true, false, true, 'enterprise', 1000, true, now(), now());

-- Inactive user
INSERT INTO users (id, email, hashed_password, is_active, is_superuser, is_verified, subscription_tier, credits_remaining, created_at, updated_at)
VALUES 
  (gen_random_uuid(), 'inactive.user@test.com', '', false, false, true, 'free', 0, now(), now());
```

## Test Users Created

The script creates users with these characteristics:

- **free.user@test.com** - Free tier, 5 credits
- **basic.user@test.com** - Basic tier, 50 credits
- **pro.user@test.com** - Pro tier, 200 credits
- **enterprise.user@test.com** - Enterprise tier, 1000 credits
- **inactive.user@test.com** - Inactive account
- **custom.limits@test.com** - Pro tier with custom limits enabled
- **john.doe@test.com** - Basic tier user
- **jane.smith@test.com** - Pro tier user
- **test.user1@test.com** - Free tier user
- **test.user2@test.com** - Free tier user (low credits)

## Notes

- Test users don't have passwords set (empty `hashed_password`)
- They can only log in via OAuth (Google) if their email matches
- You can set passwords manually if needed for testing
- Users are created with `is_verified = true` so they can log in immediately

## Setting Passwords for Test Users

If you want to set passwords for test users, you can use the registration endpoint or update directly:

```python
# In Python (from backend container)
from app.auth import get_user_manager
from app.database import get_async_session
import asyncio

async def set_password():
    async for session in get_async_session():
        async for user_db in get_user_db(session):
            async for user_manager in get_user_manager(user_db):
                user = await user_manager.get_by_email("free.user@test.com")
                if user:
                    await user_manager.update(user, {"password": "testpassword123"})
                    print("Password set!")

asyncio.run(set_password())
```

Or use the FastAPI-Users password reset flow.

