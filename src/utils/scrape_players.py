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
BASE_URL = "https://sofifa.com/players?gender=0&units=mks&currency=EUR"
TOTAL_PAGES = 600 

def calculate_value(current, potential):
    raw_value = int(((0.8 * current) + (0.2 * potential)) * 10)
    if raw_value >= 850: return raw_value, "ultra_rare"
    elif 820 <= raw_value < 850: return raw_value - 120, "rare"
    elif 790 <= raw_value < 820: return raw_value - 280, "semi_rare"
    elif 750 <= raw_value < 790: return raw_value - 375, "uncommon"
    elif 590 <= raw_value < 750: return raw_value - 580, "common"
    else: return 10, "trash"

def clean_name_from_slug(url):
    try:
        parts = [p for p in url.split('/') if p]
        # SoFIFA URLs are usually /player/ID/SLUG/VERSION
        # We want the slug (text part)
        slug = parts[-1] if not parts[-1].isdigit() else parts[-2]
        return slug.replace('-', ' ').title()
    except:
        return None

def scrape_sofifa():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created data directory at: {OUTPUT_DIR}")

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
                    
                    # ID Check (Deduplication)
                    player_id = name_link['href'].split('/')[2]
                    if player_id in seen_ids:
                        continue 
                    seen_ids.add(player_id)

                    # --- UPDATED NAME LOGIC ---
                    # 1. Get the short name displayed on the card (e.g., "Raphinha" or "C. Palmer")
                    short_name = name_link.get_text(strip=True)

                    # 2. Get the full name from tooltip or URL slug (e.g., "Raphael Dias Belloli")
                    full_name = name_link.get('data-tooltip')
                    if not full_name:
                        full_name = clean_name_from_slug(name_link['href'])
                    
                    # 3. Apply the Logic: Only use full name if short name has a dot "."
                    if "." in short_name:
                        # Case: "C. Palmer" -> Use "Cole Palmer" (Full Name)
                        # Fallback: if full_name is somehow missing, keep short_name
                        name = full_name if full_name else short_name
                    else:
                        # Case: "Raphinha" -> Keep "Raphinha"
                        name = short_name
                    # ---------------------------

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

                    # 5. RATINGS
                    ovr_td = row.select_one('td[data-col="oa"]')
                    pot_td = row.select_one('td[data-col="pt"]')
                    current_ovr = int(ovr_td.get_text(strip=True)) if ovr_td else 0
                    potential_ovr = int(pot_td.get_text(strip=True)) if pot_td else 0

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