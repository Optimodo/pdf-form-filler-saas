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
            
            # Create the tiers: Anon (internal), Standard, Pro, Enterprise
            tiers_data = [
                {
                    "tier_key": "anon",
                    "display_name": "Anonymous",
                    "description": "Internal tier for anonymous users (not displayed)",
                    "max_pdf_size": 1 * 1024 * 1024,  # 1 MB
                    "max_csv_size": 250 * 1024,  # 250 KB
                    "max_pdfs_per_run": 10,
                    "monthly_pdf_credits": 0,
                    "can_save_templates": False,
                    "can_use_api": False,
                    "priority_processing": False,
                    "max_saved_templates": 0,
                    "max_total_storage_mb": 0,
                    "display_order": 0,  # Hidden, not displayed
                    "is_active": False,  # Not active (internal only)
                },
                {
                    "tier_key": "standard",
                    "display_name": "Standard",
                    "description": "Standard tier - pay-as-you-go credits",
                    "max_pdf_size": 5 * 1024 * 1024,  # 5 MB
                    "max_csv_size": 1 * 1024 * 1024,  # 1 MB
                    "max_pdfs_per_run": 100,
                    "monthly_pdf_credits": 0,  # Standard users buy credits
                    "can_save_templates": True,
                    "can_use_api": False,
                    "priority_processing": False,
                    "max_saved_templates": 5,
                    "max_total_storage_mb": 50,
                    "display_order": 1,
                    "is_active": True,
                },
                {
                    "tier_key": "pro",
                    "display_name": "Pro",
                    "description": "Professional subscription tier with monthly credit allowance",
                    "max_pdf_size": 20 * 1024 * 1024,  # 20 MB
                    "max_csv_size": 5 * 1024 * 1024,  # 5 MB
                    "max_pdfs_per_run": 500,
                    "monthly_pdf_credits": 1000,  # Monthly subscription credits
                    "can_save_templates": True,
                    "can_use_api": True,
                    "priority_processing": True,
                    "max_saved_templates": 50,
                    "max_total_storage_mb": 500,
                    "display_order": 2,
                    "is_active": True,
                },
                {
                    "tier_key": "enterprise",
                    "display_name": "Enterprise",
                    "description": "Enterprise subscription tier with maximum features",
                    "max_pdf_size": 100 * 1024 * 1024,  # 100 MB
                    "max_csv_size": 25 * 1024 * 1024,  # 25 MB
                    "max_pdfs_per_run": 5000,
                    "monthly_pdf_credits": 10000,  # Monthly subscription credits
                    "can_save_templates": True,
                    "can_use_api": True,
                    "priority_processing": True,
                    "max_saved_templates": 500,
                    "max_total_storage_mb": 5000,
                    "display_order": 3,
                    "is_active": True,
                },
            ]
            
            # Create tier records
            for tier_data in tiers_data:
                tier = SubscriptionTier(**tier_data)
                session.add(tier)
                print(f"✅ Created tier: {tier_data['display_name']} ({tier_data['tier_key']})")
            
            await session.commit()
            
            # Migrate existing old tier users to "standard"
            old_tiers = ["basic", "free", "member"]  # Old tier names that should map to "standard"
            migrated_count = 0
            
            for old_tier in old_tiers:
                result = await session.execute(
                    select(User).where(User.subscription_tier == old_tier)
                )
                old_tier_users = result.scalars().all()
                
                if old_tier_users:
                    await session.execute(
                        update(User)
                        .where(User.subscription_tier == old_tier)
                        .values(subscription_tier="standard")
                    )
                    migrated_count += len(old_tier_users)
                    print(f"   Migrated {len(old_tier_users)} users from '{old_tier}' to 'standard' tier")
            
            if migrated_count > 0:
                await session.commit()
                print(f"\n✅ Migrated {migrated_count} total users to 'standard' tier")
            else:
                print("\n✅ No users with old tier names found (nothing to migrate)")
            
            print("\n✨ Subscription tiers initialized successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error initializing tiers: {e}")
            raise


if __name__ == "__main__":
    print("🚀 Initializing subscription tiers...\n")
    asyncio.run(init_subscription_tiers())

