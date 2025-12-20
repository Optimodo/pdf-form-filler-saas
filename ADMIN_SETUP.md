# Admin System Setup Guide

## Overview

The admin system has been implemented with the following features:

- **Admin Dashboard** - System statistics and overview
- **User Management** - View, search, and manage users
- **User Details** - Detailed user information and limits
- **Subscription Management** - Update user subscription tiers
- **Custom Limits** - Apply custom limits to users
- **User Activation** - Activate/deactivate user accounts

## Creating the First Admin User

To create your first admin user, you have a few options:

### Option 1: Using Python/Database Directly

1. Start your Docker containers:
   ```bash
   docker-compose up -d
   ```

2. Access the backend container:
   ```bash
   docker-compose exec backend python
   ```

3. Run the following Python code:
   ```python
   from app.database import get_async_session
   from app.models import User
   from sqlalchemy import select
   import asyncio
   import uuid

   async def create_admin():
       async for session in get_async_session():
           # Find your user by email
           result = await session.execute(
               select(User).where(User.email == "your-email@example.com")
           )
           user = result.scalar_one_or_none()
           
           if user:
               user.is_superuser = True
               await session.commit()
               print(f"User {user.email} is now an admin!")
           else:
               print("User not found")

   asyncio.run(create_admin())
   ```

### Option 2: Using pgAdmin

1. Access pgAdmin at http://localhost:5050
2. Login with credentials from your `.env` file
3. Connect to the database
4. Run this SQL query:
   ```sql
   UPDATE users 
   SET is_superuser = true 
   WHERE email = 'your-email@example.com';
   ```

### Option 3: Using a Database Client

Connect to your PostgreSQL database and run:
```sql
UPDATE users 
SET is_superuser = true 
WHERE email = 'your-email@example.com';
```

## Accessing the Admin Panel

Once you have an admin account:

1. Log in to the application with your admin account
2. Navigate to: `http://localhost:3000/admin`
3. You should see the admin dashboard

## Admin Features

### Dashboard (`/admin`)
- System statistics
- User counts by tier
- Processing job statistics
- Storage usage

### User Management (`/admin/users`)
- List all users with pagination
- Search users by email/name
- Filter by subscription tier
- View user details

### User Details (`/admin/users/{userId}`)
- View complete user information
- Update subscription tier
- View current limits
- See usage statistics
- View recent processing jobs
- Activate/deactivate accounts

## API Endpoints

All admin endpoints require superuser authentication (`is_superuser = true`):

### Read-Only Endpoints (Safe for API access):
- `GET /api/admin/dashboard/stats` - Dashboard statistics
- `GET /api/admin/users` - List users (with pagination/filtering)
- `GET /api/admin/users/{userId}` - Get user details
- `GET /api/admin/templates/available` - Get available limit templates

### Write Endpoints (UI-Only, consider adding security restrictions):
- `PATCH /api/admin/users/{userId}/subscription` - Update subscription tier
  - **Security Note:** Intended for UI use only. Consider IP whitelisting in production.
- `POST /api/admin/users/{userId}/custom-limits` - Set custom limits
  - **Security Note:** Intended for UI use only. All operations are logged.
- `DELETE /api/admin/users/{userId}/custom-limits` - Remove custom limits
  - **Security Note:** Intended for UI use only. All operations are logged.
- `POST /api/admin/users/{userId}/apply-template` - Apply limit template
  - **Security Note:** Intended for UI use only. All operations are logged.
- `PATCH /api/admin/users/{userId}/activate` - Toggle user active status
  - **Security Note:** Intended for UI use only. All operations are logged.

**Note:** Write endpoints are exposed via API because the frontend needs them to function. In production, consider adding IP whitelisting, rate limiting, or other security measures as documented in the Security Notes section above.

## Security Notes

### Current Security Model

- All admin endpoints are protected by the `current_superuser` dependency
- Only users with `is_superuser = true` can access admin features
- Admin actions are logged with WARNING level for audit purposes
- Frontend checks `is_superuser` before showing admin links

### Important Security Consideration

**Admin write operations (PATCH, POST, DELETE) are exposed via REST API** for the frontend to function, but should be considered **UI-only operations**.

**Security Risk:** If a superuser's JWT token is compromised, an attacker could potentially:
- Modify user subscriptions via API
- Change user limits via API
- Activate/deactivate accounts via API
- Access sensitive user data

**Current Protection:**
- Requires `is_superuser = true` authentication
- All admin write operations are logged with admin user ID and action details
- Security warnings documented in code

### Production Security Recommendations

Before deploying to production, consider adding:

1. **IP Whitelisting** - Restrict admin write endpoints to specific IP addresses
2. **Origin Checking** - Verify requests come from your UI domain
3. **Rate Limiting** - Strict rate limits on admin endpoints (e.g., 10 requests/minute)
4. **2FA Requirement** - Require two-factor authentication for superuser accounts
5. **Enhanced Audit Logging** - Log IP addresses, timestamps, and full request details
6. **Separate Admin API Keys** - Different authentication mechanism for admin operations

### Alternative Approach (Future)

If you want maximum security, you could:
- Remove write endpoints from REST API
- Have frontend call internal Python functions directly
- This would require architectural changes but provides the highest security

**For now, the current setup is functional and documented.** The endpoints are needed for the UI to work, and you can add stricter security controls before production deployment.

## Future Enhancements

The admin system is designed to be extensible. Future features can include:

- Subscription management UI
- Payment/billing management
- System configuration
- Analytics and reporting
- Email notification management
- API key management
- Audit logs viewer

