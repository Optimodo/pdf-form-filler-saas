"""
Migration script to update users and processing_jobs tables:
1. Add credits_rollover and credits_used_total to users table
2. Rename custom_max_files_per_job to custom_max_pdfs_per_run in users table
3. Remove custom_max_daily_jobs and custom_max_monthly_jobs from users table
4. Add new credit tracking columns to processing_jobs table
5. Remove old credits_consumed column from processing_jobs table

Run this from the backend container:
docker-compose exec backend python migrate_users_and_jobs.py
"""
import asyncio
import sys
from sqlalchemy import text
from app.database import get_async_session


async def migrate_users_and_jobs():
    """Migrate users and processing_jobs tables to new schema."""
    
    async for session in get_async_session():
        try:
            print("🔄 Starting users and processing_jobs migration...\n")
            
            # ========== USERS TABLE MIGRATIONS ==========
            print("=== USERS TABLE ===")
            
            # Step 1: Add credits_rollover if it doesn't exist
            print("1. Adding credits_rollover column (if missing)...")
            try:
                await session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS credits_rollover INTEGER NOT NULL DEFAULT 0;
                """))
                await session.commit()
                print("   ✅ credits_rollover column added/skipped\n")
            except Exception as e:
                print(f"   ⚠️  Error adding credits_rollover: {e}\n")
                await session.rollback()
            
            # Step 2: Add credits_used_total if it doesn't exist
            print("2. Adding credits_used_total column (if missing)...")
            try:
                await session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN IF NOT EXISTS credits_used_total INTEGER NOT NULL DEFAULT 0;
                """))
                await session.commit()
                print("   ✅ credits_used_total column added/skipped\n")
            except Exception as e:
                print(f"   ⚠️  Error adding credits_used_total: {e}\n")
                await session.rollback()
            
            # Step 3: Rename custom_max_files_per_job to custom_max_pdfs_per_run
            print("3. Renaming custom_max_files_per_job to custom_max_pdfs_per_run...")
            try:
                # Check if old column exists
                check_result = await session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='users' 
                    AND column_name='custom_max_files_per_job';
                """))
                old_exists = check_result.fetchone() is not None
                
                # Check if new column exists
                check_result = await session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='users' 
                    AND column_name='custom_max_pdfs_per_run';
                """))
                new_exists = check_result.fetchone() is not None
                
                if old_exists and not new_exists:
                    # Rename the column
                    await session.execute(text("""
                        ALTER TABLE users 
                        RENAME COLUMN custom_max_files_per_job TO custom_max_pdfs_per_run;
                    """))
                    await session.commit()
                    print("   ✅ Column renamed successfully\n")
                elif new_exists:
                    print("   ⚠️  custom_max_pdfs_per_run already exists, skipping rename\n")
                    if old_exists:
                        # Drop old column if new one exists
                        print("   Removing old custom_max_files_per_job column...")
                        await session.execute(text("""
                            ALTER TABLE users 
                            DROP COLUMN IF EXISTS custom_max_files_per_job;
                        """))
                        await session.commit()
                        print("   ✅ Old column removed\n")
                else:
                    print("   ⚠️  custom_max_files_per_job column not found, skipping rename\n")
            except Exception as e:
                print(f"   ⚠️  Error renaming column: {e}\n")
                await session.rollback()
            
            # Step 4: Remove custom_max_daily_jobs and custom_max_monthly_jobs columns
            print("4. Removing custom_max_daily_jobs and custom_max_monthly_jobs columns...")
            try:
                await session.execute(text("""
                    ALTER TABLE users 
                    DROP COLUMN IF EXISTS custom_max_daily_jobs;
                """))
                await session.execute(text("""
                    ALTER TABLE users 
                    DROP COLUMN IF EXISTS custom_max_monthly_jobs;
                """))
                await session.commit()
                print("   ✅ Redundant columns removed\n")
            except Exception as e:
                print(f"   ⚠️  Error removing columns: {e}\n")
                await session.rollback()
            
            # ========== PROCESSING_JOBS TABLE MIGRATIONS ==========
            print("\n=== PROCESSING_JOBS TABLE ===")
            
            # Step 5: Add new credit tracking columns if they don't exist
            print("5. Adding new credit tracking columns...")
            try:
                await session.execute(text("""
                    ALTER TABLE processing_jobs 
                    ADD COLUMN IF NOT EXISTS total_credits_consumed INTEGER NOT NULL DEFAULT 0;
                """))
                await session.execute(text("""
                    ALTER TABLE processing_jobs 
                    ADD COLUMN IF NOT EXISTS subscription_credits_used INTEGER NOT NULL DEFAULT 0;
                """))
                await session.execute(text("""
                    ALTER TABLE processing_jobs 
                    ADD COLUMN IF NOT EXISTS rollover_credits_used INTEGER NOT NULL DEFAULT 0;
                """))
                await session.execute(text("""
                    ALTER TABLE processing_jobs 
                    ADD COLUMN IF NOT EXISTS topup_credits_used INTEGER NOT NULL DEFAULT 0;
                """))
                await session.commit()
                print("   ✅ New credit columns added/skipped\n")
            except Exception as e:
                print(f"   ⚠️  Error adding credit columns: {e}\n")
                await session.rollback()
            
            # Step 6: Migrate data from credits_consumed to total_credits_consumed if needed
            print("6. Migrating data from credits_consumed to total_credits_consumed...")
            try:
                # Check if credits_consumed exists and has data
                check_result = await session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='processing_jobs' 
                    AND column_name='credits_consumed';
                """))
                old_col_exists = check_result.fetchone() is not None
                
                if old_col_exists:
                    # Copy data from credits_consumed to total_credits_consumed where it's 0
                    await session.execute(text("""
                        UPDATE processing_jobs 
                        SET total_credits_consumed = credits_consumed 
                        WHERE total_credits_consumed = 0 AND credits_consumed > 0;
                    """))
                    await session.commit()
                    print("   ✅ Data migrated\n")
                else:
                    print("   ⚠️  credits_consumed column not found, skipping data migration\n")
            except Exception as e:
                print(f"   ⚠️  Error migrating data: {e}\n")
                await session.rollback()
            
            # Step 7: Remove old credits_consumed column
            print("7. Removing old credits_consumed column...")
            try:
                await session.execute(text("""
                    ALTER TABLE processing_jobs 
                    DROP COLUMN IF EXISTS credits_consumed;
                """))
                await session.commit()
                print("   ✅ Old credits_consumed column removed\n")
            except Exception as e:
                print(f"   ⚠️  Error removing credits_consumed column: {e}\n")
                await session.rollback()
            
            print("\n✅ Migration completed successfully!")
            break  # Exit the async generator after first iteration
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(migrate_users_and_jobs())
