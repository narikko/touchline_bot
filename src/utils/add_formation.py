from sqlalchemy import text
from src.database.db import get_session

def add_column():
    print("🔌 Connecting to database...")
    session = get_session()
    try:
        # This raw SQL command adds the column
        print("⚙️ Adding 'formation' column...")
        session.execute(text("ALTER TABLE users ADD COLUMN formation TEXT DEFAULT '4-3-3'"))
        session.commit()
        print("✅ Success! Column 'formation' added.")
    except Exception as e:
        print(f"❌ Error (Column might already exist): {e}")
    finally:
        session.close()

if __name__ == "__main__":
    add_column()