"""
Initialize subscription tiers in the database.

Run this script once after creating the subscription_tiers table to populate
initial tier data and migrate existing "basic" tier users to "member".

Usage:
    docker-compose exec backend python init_subscription_tiers.py
"""
import asyncio
from app.database import get_async_session
from app.models import SubscriptionTier, User
from sqlalchemy import select, update


async def init_subscription_tiers():
    """Initialize subscription tiers and migrate basic -> member."""
    
    async for session in get_async_session():
        try:
            # Check if tiers already exist
            result = await session.execute(select(SubscriptionTier))
            existing_tiers = result.scalars().all()
            
            if existing_tiers:
                print(f"⚠️  Found {len(existing_tiers)} existing tiers. Skipping initialization.")
                print("   If you want to reset tiers, delete them from the database first.")
                return
            
            # Create the four tiers with new naming: Free, Member, Pro, Enterprise
            tiers_data = [
                {
                    "tier_key": "free",
                    "display_name": "Free",
                    "description": "Free tier with basic functionality",
                    "max_pdf_size": 1 * 1024 * 1024,  # 1 MB
                    "max_csv_size": 250 * 1024,  # 250 KB
                    "max_daily_jobs": 3,
                    "max_monthly_jobs": 10,
                    "max_files_per_job": 50,
                    "can_save_templates": False,
                    "can_use_api": False,
                    "priority_processing": False,
                    "max_saved_templates": 0,
                    "max_total_storage_mb": 0,
                    "display_order": 1,
                },
                {
                    "tier_key": "member",
                    "display_name": "Member",
                    "description": "Member tier with enhanced features",
                    "max_pdf_size": 5 * 1024 * 1024,  # 5 MB
                    "max_csv_size": 1 * 1024 * 1024,  # 1 MB
                    "max_daily_jobs": 20,
                    "max_monthly_jobs": 100,
                    "max_files_per_job": 200,
                    "can_save_templates": True,
                    "can_use_api": False,
                    "priority_processing": False,
                    "max_saved_templates": 5,
                    "max_total_storage_mb": 50,
                    "display_order": 2,
                },
                {
                    "tier_key": "pro",
                    "display_name": "Pro",
                    "description": "Professional tier with advanced features",
                    "max_pdf_size": 20 * 1024 * 1024,  # 20 MB
                    "max_csv_size": 5 * 1024 * 1024,  # 5 MB
                    "max_daily_jobs": 100,
                    "max_monthly_jobs": 1000,
                    "max_files_per_job": 1000,
                    "can_save_templates": True,
                    "can_use_api": True,
                    "priority_processing": True,
                    "max_saved_templates": 50,
                    "max_total_storage_mb": 500,
                    "display_order": 3,
                },
                {
                    "tier_key": "enterprise",
                    "display_name": "Enterprise",
                    "description": "Enterprise tier with maximum features",
                    "max_pdf_size": 100 * 1024 * 1024,  # 100 MB
                    "max_csv_size": 25 * 1024 * 1024,  # 25 MB
                    "max_daily_jobs": 1000,
                    "max_monthly_jobs": 10000,
                    "max_files_per_job": 10000,
                    "can_save_templates": True,
                    "can_use_api": True,
                    "priority_processing": True,
                    "max_saved_templates": 500,
                    "max_total_storage_mb": 5000,
                    "display_order": 4,
                },
            ]
            
            # Create tier records
            for tier_data in tiers_data:
                tier = SubscriptionTier(**tier_data)
                session.add(tier)
                print(f"✅ Created tier: {tier_data['display_name']} ({tier_data['tier_key']})")
            
            await session.commit()
            
            # Migrate existing "basic" tier users to "member"
            result = await session.execute(
                select(User).where(User.subscription_tier == "basic")
            )
            basic_users = result.scalars().all()
            
            if basic_users:
                await session.execute(
                    update(User)
                    .where(User.subscription_tier == "basic")
                    .values(subscription_tier="member")
                )
                await session.commit()
                print(f"\n✅ Migrated {len(basic_users)} users from 'basic' to 'member' tier")
            else:
                print("\n✅ No users with 'basic' tier found (nothing to migrate)")
            
            print("\n✨ Subscription tiers initialized successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error initializing tiers: {e}")
            raise


if __name__ == "__main__":
    print("🚀 Initializing subscription tiers...\n")
    asyncio.run(init_subscription_tiers())
