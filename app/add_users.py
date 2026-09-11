# from sqlalchemy import create_engine, text

# # Replace with your actual database URL
# DATABASE_URL = "postgresql://postgres:Nandhini%40123@localhost:5432/dating_application"

# engine = create_engine(DATABASE_URL)

# with engine.begin() as conn:
#     try:
#         # Create gender enum if it doesn't exist
#         conn.execute(text("""
#         DO $$
#         BEGIN
#             IF NOT EXISTS (
#                 SELECT 1 FROM pg_type WHERE typname = 'gender_enum'
#             ) THEN
#                 CREATE TYPE gender_enum AS ENUM ('Male', 'Female', 'Other');
#             END IF;
#         END$$;
#         """))

#         # Create role enum if it doesn't exist
#         conn.execute(text("""
#         DO $$
#         BEGIN
#             IF NOT EXISTS (
#                 SELECT 1 FROM pg_type WHERE typname = 'role_enum'
#             ) THEN
#                 CREATE TYPE role_enum AS ENUM ('admin', 'creator', 'customer');
#             END IF;
#         END$$;
#         """))

#         # Add gender column
#         conn.execute(text("""
#         ALTER TABLE users
#         ADD COLUMN IF NOT EXISTS gender gender_enum
#         DEFAULT 'Other' NOT NULL;
#         """))

#         # Add role column
#         conn.execute(text("""
#         ALTER TABLE users
#         ADD COLUMN IF NOT EXISTS role role_enum
#         DEFAULT 'customer' NOT NULL;
#         """))

#         print("✅ Successfully added 'gender' and 'role' columns.")

#     except Exception as e:
#         print(f"❌ Error: {e}")

from sqlalchemy import create_engine, text

# Replace with your actual database URL
DATABASE_URL = "postgresql://postgres:Nandhini%40123@localhost:5432/dating_application"

engine = create_engine(DATABASE_URL)

with engine.begin() as conn:
    try:
        # Rename column user_id -> following_id
        conn.execute(text("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'follow_details'
                  AND column_name = 'user_id'
            ) THEN
                ALTER TABLE follow_details
                RENAME COLUMN user_id TO following_id;
            END IF;
        END$$;
        """))

        print("✅ Successfully renamed 'user_id' to 'following_id'.")

    except Exception as e:
        print(f"❌ Error: {e}")