import os

# --- PATH CONFIGURATION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
DATA_DIR = os.path.join(project_root, "data")
LEGENDS_FILE = os.path.join(DATA_DIR, "legends_list.txt")

def update_ids():
    if not os.path.exists(LEGENDS_FILE):
        print(f"❌ Error: Could not find file at {LEGENDS_FILE}")
        return

    print(f"Reading from: {LEGENDS_FILE}")
    
    with open(LEGENDS_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    current_id = 999000  # Start ID
    
    for line in lines:
        line = line.strip()
        if not line: continue

        # Split by comma-space
        parts = line.split(", ")
        
        # Check if the line has enough parts (Name, Pos, Club, Nation, Value, Image, ID)
        if len(parts) >= 7:
            # Replace the last element (the old ID) with the new ID
            parts[-1] = str(current_id)
            
            # Reconstruct the line
            new_line = ", ".join(parts) + "\n"
            new_lines.append(new_line)
            
            current_id += 1
        else:
            print(f"⚠️ Skipping malformed line: {line}")
            new_lines.append(line + "\n")

    # Overwrite the file with new data
    with open(LEGENDS_FILE, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"✅ Successfully updated {len(new_lines)} legends.")
    print(f"   IDs now range from 999000 to {current_id - 1}")

if __name__ == "__main__":
    update_ids()