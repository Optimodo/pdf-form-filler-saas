#!/usr/bin/env python3
"""
Script to fix the database schema by dropping and recreating tables with new structure.
"""
import asyncio
from app.database import engine
from sqlalchemy import text

async def fix_database():
    async with engine.begin() as conn:
        print("Dropping old tables...")
        await conn.execute(text("DROP TABLE IF EXISTS processing_jobs CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS uploaded_files CASCADE"))
        print("Tables dropped successfully")
        
        print("Creating new tables...")
        from app.database import create_db_and_tables
        await create_db_and_tables()
        print("New tables created successfully")

if __name__ == "__main__":
    asyncio.run(fix_database())
