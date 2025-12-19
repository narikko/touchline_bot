import os
import time
import re
from src.database.db import engine, SessionLocal, init_db
from src.database.models import Base, PlayerBase

# Map your filenames to the Rarity string in the database
DATA_FILES = {
    "src/data/ultra_rare_players_list.txt": "Ultra Rare",
    "src/data/rare_players.txt": "Rare",
    "src/data/common_players.txt": "Common",
    "src/data/legends_list.txt": "Legend"
}

def parse_value(raw_value):
    """Converts 'Value: 1500' or '1500' to integer 1500."""
    # Remove 'Value:', spaces, and emojis if present
    clean = raw_value.replace("Value:", "").strip()
    # Remove any non-numeric characters just in case
    clean = re.sub(r'[^\d]', '', clean)
    return int(clean) if clean else 0

def seed_database():
    print("--- Starting Database Seeding ---")
    
    # 1. Initialize Tables
    init_db()
    
    session = SessionLocal()
    start_time = time.time()
    total_added = 0

    try:
        # 3. Loop through files
        for filename, rarity in DATA_FILES.items():
            if not os.path.exists(filename):
                print(f"Skipping {filename} (File not found)")
                continue
            
            print(f"📖 Reading {filename}...")
            
            players_buffer = []
            
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                if not line: continue

                # Split by ", "
                parts = line.split(", ")
                
                # Validation: We need at least Name, Pos, Club, Nation, Value, URL, ID (7 parts)
                if len(parts) < 7:
                    # Try a fallback split by just comma if ", " fails (some messy files)
                    parts = line.split(",")
                    if len(parts) < 7:
                        print(f"   Skipping malformed line: {line[:50]}...")
                        continue
                
                try:
                    # Extract Data
                    name = parts[0].strip()
                    positions = parts[1].strip()
                    club = parts[2].strip()
                    nationality = parts[3].strip()
                    value = parse_value(parts[4])
                    image_url = parts[5].strip()
                    
                    # Create Object
                    player = PlayerBase(
                        name=name,
                        positions=positions,
                        club=club,
                        nationality=nationality,
                        # value=value, <--- REMOVED THIS LINE. Value is read-only.
                        image_url=image_url,
                        rarity=rarity,
                        # We use 'rating' to store the value score
                        rating=value 
                    )
                    players_buffer.append(player)
                    
                except Exception as e:
                    print(f"   Error parsing line: {line[:30]}... Error: {e}")

            # 4. Bulk Insert
            if players_buffer:
                print(f"   Inserting {len(players_buffer)} {rarity} players...")
                session.bulk_save_objects(players_buffer)
                total_added += len(players_buffer)
                session.commit() # Commit after each file

    except Exception as e:
        session.rollback()
        print(f"Critical Error during seeding: {e}")
    finally:
        session.close()

    end_time = time.time()
    print(f"--- Seeding Complete in {end_time - start_time:.2f}s ---")
    print(f"Total Players Added: {total_added}")

if __name__ == "__main__":
    seed_database()