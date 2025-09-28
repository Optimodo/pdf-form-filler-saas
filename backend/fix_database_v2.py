#!/usr/bin/env python3
"""
Script to fix the database schema by updating column types.
"""
import asyncio
from app.database import engine
from sqlalchemy import text

async def fix_database():
    async with engine.begin() as conn:
        print("Updating processing_jobs table column types...")
        await conn.execute(text("ALTER TABLE processing_jobs ALTER COLUMN processing_time_seconds TYPE VARCHAR(20)"))
        await conn.execute(text("ALTER TABLE processing_jobs ALTER COLUMN file_size_mb TYPE VARCHAR(20)"))
        print("Column types updated successfully")

if __name__ == "__main__":
    asyncio.run(fix_database())
