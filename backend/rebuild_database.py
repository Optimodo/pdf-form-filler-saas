"""
Script to completely rebuild the database from scratch.

This will:
1. Drop all existing tables (WARNING: This deletes all data!)
2. Recreate all tables with proper field ordering from the models

Run this from the backend container:
docker-compose exec backend python rebuild_database.py

WARNING: This will delete ALL data in the database!
"""
import asyncio
import sys
from sqlalchemy import text
from app.database import get_async_session, engine, create_db_and_tables
# Import models to ensure they're registered with Base.metadata
from app.models import (
    SubscriptionTier,
    User,
    UserTemplate,
    UploadedFile,
    ProcessingJob,
    OAuthAccount,
    ActivityLog
)


async def rebuild_database():
    """Drop all tables and recreate them from scratch."""
    
    print("⚠️  WARNING: This will delete ALL data in the database!")
    print("⚠️  Press Ctrl+C within 5 seconds to cancel...\n")
    
    try:
        await asyncio.sleep(5)
    except asyncio.CancelledError:
        print("\n❌ Cancelled by user")
        sys.exit(0)
    
    async for session in get_async_session():
        try:
            print("🗑️  Dropping all existing tables...\n")
            
            # Drop all tables in reverse dependency order
            # (drop tables that reference others first)
            drop_order = [
                "activity_logs",           # References users, processing_jobs, subscription_tiers
                "processing_jobs",         # References users, uploaded_files
                "user_templates",          # References users
                "oauth_accounts",          # References users
                "uploaded_files",          # References users
                "users",                   # References subscription_tiers (via foreign key constraint)
                "subscription_tiers",
            ]
            
            for table in drop_order:
                try:
                    await session.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
                    print(f"   ✅ Dropped {table}")
                except Exception as e:
                    print(f"   ⚠️  Error dropping {table}: {e}")
            
            await session.commit()
            print("\n✅ All tables dropped\n")
            
            print("🔨 Creating all tables from models...\n")
            
            # Recreate all tables using SQLAlchemy metadata
            # This will create them with fields in the order defined in the models
            await create_db_and_tables()
            
            print("✅ All tables created successfully!")
            print("\n📝 Next steps:")
            print("   1. Create subscription tiers via admin panel or manually")
            print("   2. Run: docker-compose exec backend python create_test_users.py")
            print("   3. Create your admin account manually or set superuser flag")
            print("\n✨ Database rebuild complete!")
            
            break  # Exit the async generator after first iteration
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Database rebuild failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(rebuild_database())
