"""
Migration script to update subscription_tiers table:
1. Add monthly_pdf_credits column if missing
2. Remove max_daily_jobs and max_monthly_jobs columns (redundant - using credits now)
3. Rename max_files_per_job to max_pdfs_per_run

Run this from the backend container:
docker-compose exec backend python migrate_subscription_tiers.py

NOTE: This script will:
- Add monthly_pdf_credits column (defaults to 0)
- Rename max_files_per_job to max_pdfs_per_run (preserves data)
- Remove max_daily_jobs and max_monthly_jobs columns (data will be lost)
"""
import asyncio
import sys
from sqlalchemy import text
from app.database import get_async_session


async def migrate_subscription_tiers():
    """Migrate subscription_tiers table to new schema."""
    
    async for session in get_async_session():
        try:
            print("🔄 Starting subscription_tiers migration...\n")
            
            # Step 1: Add monthly_pdf_credits if it doesn't exist
            print("1. Adding monthly_pdf_credits column (if missing)...")
            try:
                await session.execute(text("""
                    ALTER TABLE subscription_tiers 
                    ADD COLUMN IF NOT EXISTS monthly_pdf_credits INTEGER NOT NULL DEFAULT 0;
                """))
                await session.commit()
                print("   ✅ monthly_pdf_credits column added/skipped\n")
            except Exception as e:
                print(f"   ⚠️  Error adding monthly_pdf_credits (may already exist): {e}\n")
                await session.rollback()
            
            # Step 2: Rename max_files_per_job to max_pdfs_per_run
            print("2. Renaming max_files_per_job to max_pdfs_per_run...")
            try:
                # Check if old column exists
                check_result = await session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='subscription_tiers' 
                    AND column_name='max_files_per_job';
                """))
                old_exists = check_result.fetchone() is not None
                
                # Check if new column exists
                check_result = await session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='subscription_tiers' 
                    AND column_name='max_pdfs_per_run';
                """))
                new_exists = check_result.fetchone() is not None
                
                if old_exists and not new_exists:
                    # Rename the column
                    await session.execute(text("""
                        ALTER TABLE subscription_tiers 
                        RENAME COLUMN max_files_per_job TO max_pdfs_per_run;
                    """))
                    await session.commit()
                    print("   ✅ Column renamed successfully\n")
                elif new_exists:
                    print("   ⚠️  max_pdfs_per_run already exists, skipping rename\n")
                    if old_exists:
                        # Drop old column if new one exists
                        print("   Removing old max_files_per_job column...")
                        await session.execute(text("""
                            ALTER TABLE subscription_tiers 
                            DROP COLUMN IF EXISTS max_files_per_job;
                        """))
                        await session.commit()
                        print("   ✅ Old column removed\n")
                else:
                    print("   ⚠️  max_files_per_job column not found, skipping rename\n")
            except Exception as e:
                print(f"   ⚠️  Error renaming column: {e}\n")
                await session.rollback()
            
            # Step 3: Remove max_daily_jobs and max_monthly_jobs columns
            print("3. Removing max_daily_jobs and max_monthly_jobs columns...")
            try:
                await session.execute(text("""
                    ALTER TABLE subscription_tiers 
                    DROP COLUMN IF EXISTS max_daily_jobs;
                """))
                await session.execute(text("""
                    ALTER TABLE subscription_tiers 
                    DROP COLUMN IF EXISTS max_monthly_jobs;
                """))
                await session.commit()
                print("   ✅ Redundant columns removed\n")
            except Exception as e:
                print(f"   ⚠️  Error removing columns: {e}\n")
                await session.rollback()
            
            print("✅ Migration completed successfully!")
            print("\n📝 Note: You may need to update existing tier records to set monthly_pdf_credits values.")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Migration failed: {e}")
            sys.exit(1)
        finally:
            break  # Exit the async generator after first iteration


if __name__ == "__main__":
    asyncio.run(migrate_subscription_tiers())
