import os
import requests
import time

# --- PATH CONFIGURATION ---
# This matches your scrape_players.py logic exactly
current_dir = os.path.dirname(os.path.abspath(__file__))  # src/utils
project_root = os.path.dirname(current_dir)             # src/ (or project root depending on depth)
DATA_DIR = os.path.join(project_root, "data")           # Path to /data folder

# The specific file to check
FILE_PATH = os.path.join(DATA_DIR, "legends_list.txt")

def check_images():
    # 1. Verify file existence using the absolute path
    if not os.path.exists(FILE_PATH):
        print(f"❌ Error: Could not find file at: {FILE_PATH}")
        print(f"   Current working dir: {os.getcwd()}")
        return

    print(f"🕵️  Scanning image URLs in: {FILE_PATH}\n")
    
    valid_count = 0
    broken_count = 0
    total_count = 0
    
    # Headers to look like a real browser (prevents 403 Forbidden on some CDNs)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # 2. Read the file
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 3. Process every line
    for line in lines:
        parts = line.strip().split(', ')
        
        # Skip empty lines or headers
        if len(parts) < 7:
            continue
            
        total_count += 1
        name = parts[0]
        url = parts[5] # Index 5 is the Image URL
        
        status_msg = ""
        
        try:
            # We attempt a 'HEAD' request first (faster, doesn't download the image)
            response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
            
            # If HEAD fails (some servers block it), fallback to GET
            if response.status_code >= 400:
                 response = requests.get(url, headers=headers, timeout=5, stream=True)
            
            if response.status_code == 200:
                # Extra check: ensure it is actually an image (optional but good)
                content_type = response.headers.get('Content-Type', '')
                if 'image' in content_type or url.endswith(('.jpg', '.png', '.webp')):
                    status_msg = "✅ OK"
                    valid_count += 1
                else:
                    status_msg = f"⚠️  Not Image? ({content_type})"
                    # We count this as valid for now, just a warning
                    valid_count += 1
            else:
                status_msg = f"❌ Broken ({response.status_code})"
                broken_count += 1
                
        except requests.exceptions.RequestException as e:
            status_msg = f"❌ Error"
            broken_count += 1

        print(f"{status_msg} | {name}")
        
        # Sleep briefly to be polite to servers
        time.sleep(0.1)

    # 4. Final Summary
    print("\n" + "="*30)
    print(f"📊 SUMMARY")
    print(f"Total Checked: {total_count}")
    print(f"✅ Valid:      {valid_count}")
    print(f"❌ Broken:     {broken_count}")
    print("="*30)

    if broken_count > 0:
        print("\n💡 Action Required: Open 'data/legends_list.txt', fix the broken URLs, then run 'update_legends.py'.")

if __name__ == "__main__":
    check_images()