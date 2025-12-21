import os
import time
import re
from src.database.db import SessionLocal, init_db
from src.database.models import PlayerBase

# Map your filenames to the Rarity string
DATA_FILES = {
    "src/data/ultra_rare_players_list.txt": "Ultra Rare",
    "src/data/rare_players.txt": "Rare",
    "src/data/common_players.txt": "Common",
    "src/data/legends_list.txt": "Legend"
}

def parse_value(raw_value):
    clean = raw_value.replace("Value:", "").strip()
    clean = re.sub(r'[^\d]', '', clean)
    return int(clean) if clean else 0

def seed_database():
    print("--- Starting Sustainable Database Seeding ---")
    
    # Initialize DB (creates tables if missing, doesn't hurt existing ones)
    init_db()
    
    session = SessionLocal()
    start_time = time.time()
    total_processed = 0

    try:
        for filename, rarity in DATA_FILES.items():
            if not os.path.exists(filename):
                print(f"Skipping {filename} (Not found)")
                continue
            
            print(f"📖 Processing {filename}...")
            
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Process in batches to be faster, but safer than bulk_save
            for line in lines:
                line = line.strip()
                if not line: continue

                parts = line.split(", ")
                
                # Check for malformed lines
                if len(parts) < 7:
                    parts = line.split(",") # Fallback
                    if len(parts) < 7: continue

                try:
                    # 1. EXTRACT DATA
                    name = parts[0].strip()
                    positions = parts[1].strip()
                    club = parts[2].strip()
                    nationality = parts[3].strip()
                    value = parse_value(parts[4])
                    image_url = parts[5].strip()
                    
                    # CRITICAL: Read the ID from the file!
                    # This ensures "Messi" is always ID 158023
                    sofifa_id = int(parts[6].strip()) 

                    # 2. CREATE OBJECT (With explicit ID)
                    player = PlayerBase(
                        id=sofifa_id,  # Lock the ID
                        name=name,
                        positions=positions,
                        club=club,
                        nationality=nationality,
                        image_url=image_url,
                        rarity=rarity,
                        rating=value
                    )
                    
                    # 3. THE MAGIC FIX: MERGE
                    # This checks the DB. If ID exists -> Update. If not -> Insert.
                    session.merge(player)
                    total_processed += 1
                    
                except Exception as e:
                    print(f"Error on line: {line[:20]}... {e}")

            # Commit after every file to save progress
            session.commit()
            print(f"   ✅ Merged {rarity} players.")

    except Exception as e:
        session.rollback()
        print(f"Critical Error: {e}")
    finally:
        session.close()

    end_time = time.time()
    print(f"--- Complete! Processed {total_processed} players in {end_time - start_time:.2f}s ---")

if __name__ == "__main__":
    seed_database()