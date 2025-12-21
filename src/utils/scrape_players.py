import cloudscraper
from bs4 import BeautifulSoup
import time
import os
import random
import re

# --- PATH CONFIGURATION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
OUTPUT_DIR = os.path.join(project_root, "data")

# --- CONFIGURATION ---
# Using the sorted URL to guarantee we find everyone
BASE_URL = "https://sofifa.com/players?type=all&r=260013&set=true&gender=0&units=mks&currency=EUR&col=oa&sort=desc"
TOTAL_PAGES = 900 

def calculate_value(current, potential):
    # 1. Effective Rating (85% Current, 15% Potential)
    raw_rating = (0.85 * current) + (0.15 * potential)
    
    # --- PIECEWISE LOGIC ---
    if raw_rating >= 85:
        final_value = int(raw_rating * 10)
        category = "ultra_rare"
    elif raw_rating >= 78:
        final_value = int(450 + (raw_rating - 78) * 57)
        category = "rare"
    else:
        final_value = int(450 - (78 - raw_rating) * 70)
        category = "common"

    return max(15, final_value), category

def clean_name_from_slug(url):
    try:
        parts = [p for p in url.split('/') if p]
        slug = parts[-1] if not parts[-1].isdigit() else parts[-2]
        return slug.replace('-', ' ').title()
    except:
        return None

# --- NEW HELPER FUNCTION TO FIX THE CRASH ---
def get_clean_rating(td_element):
    """Converts '83+1' or '83-2' into just integer 83."""
    if not td_element: return 0
    text = td_element.get_text(strip=True)
    
    # Split by '+' or '-' and take the first part
    if '+' in text:
        text = text.split('+')[0]
    if '-' in text:
        text = text.split('-')[0]
        
    try:
        return int(text)
    except ValueError:
        return 0
# ---------------------------------------------

def scrape_sofifa():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    f_ultra = open(os.path.join(OUTPUT_DIR, "ultra_rare_players_list.txt"), "w", encoding="utf-8")
    f_rare = open(os.path.join(OUTPUT_DIR, "rare_players.txt"), "w", encoding="utf-8")
    f_common = open(os.path.join(OUTPUT_DIR, "common_players.txt"), "w", encoding="utf-8")

    files = {
        "ultra_rare": f_ultra,
        "rare": f_rare,
        "semi_rare": f_common,
        "uncommon": f_common,
        "common": f_common,
        "trash": None
    }

    seen_ids = set()
    # Updated Scraper headers to match debug script success
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    print(f"Starting scrape (~{TOTAL_PAGES} pages)...")

    for page in range(TOTAL_PAGES):
        try:
            offset = page * 60
            url = f"{BASE_URL}&offset={offset}"
            
            response = scraper.get(url, timeout=15)
            if response.status_code != 200:
                print(f"❌ Failed to load page {page + 1} - Status: {response.status_code}")
                time.sleep(10)
                continue

            soup = BeautifulSoup(response.content, 'html.parser')
            rows = soup.select('tbody tr')

            if not rows:
                print(f"⚠️ Page {page + 1} loaded but no rows found. Reached end of database.")
                break 

            count = 0
            
            for row in rows:
                try:
                    # 1. NAME & ID
                    name_link = row.select_one('a[href^="/player/"]')
                    if not name_link: continue
                    
                    player_id = name_link['href'].split('/')[2]
                    if player_id in seen_ids:
                        continue 
                    seen_ids.add(player_id)

                    short_name = name_link.get_text(strip=True)
                    full_name = name_link.get('data-tooltip')
                    if not full_name:
                        full_name = clean_name_from_slug(name_link['href'])
                    
                    if "." in short_name:
                        name = full_name if full_name else short_name
                    else:
                        name = short_name

                    # 2. POSITIONS
                    name_col = row.select_one('td:nth-of-type(2)')
                    pos_list = []
                    if name_col:
                        candidates = name_col.find_all(['a', 'span'])
                        for tag in candidates:
                            text = tag.get_text(strip=True)
                            if re.match(r'^[A-Z]{2,3}$', text):
                                pos_list.append(text)
                    
                    positions = "/".join(list(dict.fromkeys(pos_list))) 
                    if not positions: positions = "N/A"

                    # 3. IMAGE
                    img_tag = row.select_one('img[data-src]') or row.select_one('img[src*="players"]')
                    image_url = "N/A"
                    if img_tag:
                        raw_url = img_tag.get('data-src') or img_tag.get('src')
                        image_url = raw_url.replace('60.png', '180.png') 

                    # 4. NATIONALITY
                    nation_img = row.select_one('img[src*="flags"], a[href^="/players?na"] img')
                    nationality = nation_img.get('title') if nation_img else "N/A"

                    # 5. RATINGS (FIXED WITH HELPER FUNCTION)
                    ovr_td = row.select_one('td[data-col="oa"]')
                    pot_td = row.select_one('td[data-col="pt"]')
                    
                    current_ovr = get_clean_rating(ovr_td)    # <--- FIXED
                    potential_ovr = get_clean_rating(pot_td)  # <--- FIXED

                    # 6. CLUB
                    team_link = row.select_one('a[href^="/team/"]')
                    club = "Free Agent"
                    if team_link:
                        club = team_link.get_text(strip=True)
                        club = re.sub(r'\d{4}$', '', club).strip()

                    # SAVE
                    final_value, category = calculate_value(current_ovr, potential_ovr)
                    
                    line = f"{name}, {positions}, {club}, {nationality}, Value: {final_value}, {image_url}, {player_id}\n"

                    if category != "trash" and files[category]:
                        files[category].write(line)
                        count += 1

                except Exception as e:
                    # Now we will see if something else breaks!
                    print(f"Skipping player error: {e}")
                    continue
            
            print(f"✅ Page {page + 1}: Saved {count} Players (Total Unique: {len(seen_ids)})")
            
            if count == 0 and len(rows) > 0:
                 print("⚠️ Zero new players found on this page. Stopping.")
                 break

            time.sleep(random.uniform(2, 4))

        except Exception as e:
            print(f"Page Error: {e}")

    f_ultra.close()
    f_rare.close()
    f_common.close()

    print(f"Scrape Complete. Total Unique Players: {len(seen_ids)}")

if __name__ == "__main__":
    scrape_sofifa()