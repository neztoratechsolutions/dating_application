# scripts/fix_gift_master.py
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE gift_master 
        DROP COLUMN IF EXISTS creator_revenue,
        DROP COLUMN IF EXISTS platform_revenue;
    """))
    conn.commit()
    print("Done: dropped creator_revenue and platform_revenue from gift_master")