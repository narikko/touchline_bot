from src.database.db import get_session
from sqlalchemy import text

def clear_all_data():
    session = get_session()
    try:
        print("🗑️  Clearing all tables...")
        
        # This command deletes data from all tables listed.
        # CASCADE ensures that if Table A depends on Table B, both are cleared safely.
        # RESTART IDENTITY resets the ID counters back to 1.
        sql_cmd = text("""
            TRUNCATE TABLE 
                users, 
                cards, 
                player_base, 
                shortlists, 
                market_listings, 
                global_tutorials 
            RESTART IDENTITY CASCADE;
        """)
        
        session.execute(sql_cmd)
        session.commit()
        
        print("✅ Database completely wiped.")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error clearing database: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    confirm = input("⚠️  WARNING: This will delete ALL users, players, and items. Type 'yes' to confirm: ")
    if confirm.lower() == "yes":
        clear_all_data()
    else:
        print("Cancelled.")