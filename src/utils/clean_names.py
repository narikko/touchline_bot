import re
import os

def clean_player_names(file_path):
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found at {file_path}")
        return

    print(f"Processing {file_path}...")
    
    cleaned_lines = []
    changes_made = 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line in lines:
            parts = line.split(',')
            
            if len(parts) > 0:
                original_name = parts[0]
                # Regex explanation: ^ means start of string, \d+ means one or more digits
                new_name = re.sub(r'^\d+', '', original_name)
                
                if original_name != new_name:
                    parts[0] = new_name
                    changes_made += 1
                    print(f"🔹 Fixed: '{original_name}' -> '{new_name}'")
                
                # Reconstruct the line
                cleaned_lines.append(','.join(parts))
            else:
                cleaned_lines.append(line)

        # Write back to the file (overwrite)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(cleaned_lines)

        print(f"✅ Finished! Fixed {changes_made} names.")

    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    # You can call this multiple times for different files if needed
    clean_player_names("src/data/ultra_rare_players_list.txt")
    clean_player_names("src/data/rare_players.txt")
    clean_player_names("src/data/common_players.txt")