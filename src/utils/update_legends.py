import os
from src.database.db import get_session
from src.database.models import PlayerBase

# --- CONFIGURATION ---
# Make sure this matches the filename where you fixed the URLs
LEGENDS_FILE = "data/legends.txt" 

def update_legend_images():
    session = get_session()
    
    # Check if file exists
    if not os.path.exists(LEGENDS_FILE):
        print(f"❌ Error: Could not find file {LEGENDS_FILE}")
        return

    print(f"🔄 Reading {LEGENDS_FILE} to update images...")
    
    updated_count = 0
    
    with open(LEGENDS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(', ')
            
            # Ensure the line has all parts (Name, Pos, Club, Nation, Value, URL, ID)
            if len(parts) < 7:
                continue

            # Extract Data based on your file format
            # Format: Name, Pos, Club, Nation, Value, URL, ID
            name = parts[0]
            new_image_url = parts[5]
            player_id = int(parts[6])

            # Find the player in the DB
            player = session.query(PlayerBase).filter_by(id=player_id).first()
            
            if player:
                # Check if URL is different
                if player.image_url != new_image_url:
                    print(f"   ✏️ Updating {name}: New URL applied.")
                    player.image_url = new_image_url
                    updated_count += 1
            else:
                print(f"   ⚠️ Warning: Legend {name} (ID: {player_id}) not found in DB.")

    session.commit()
    session.close()
    print(f"✅ Update Complete. {updated_count} players updated.")

if __name__ == "__main__":
    update_legend_images()