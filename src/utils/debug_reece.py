import cloudscraper
from bs4 import BeautifulSoup
import re

# 1. Setup exact same environment as your main scraper
BASE_URL = "https://sofifa.com/players?type=all&r=260013&set=true&gender=0&units=mks&currency=EUR&col=oa&sort=desc"
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def clean_name_from_slug(url):
    try:
        parts = [p for p in url.split('/') if p]
        slug = parts[-1] if not parts[-1].isdigit() else parts[-2]
        return slug.replace('-', ' ').title()
    except:
        return None

def calculate_value(current, potential):
    # Your NEW piecewise formula
    raw_rating = (0.85 * current) + (0.15 * potential)
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

def test_reece_parsing():
    print("🧪 Testing Reece James Parsing Logic (Page 3)...")
    
    # Go straight to Page 3 (Offset 120)
    url = f"{BASE_URL}&offset=120"
    response = scraper.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    rows = soup.select('tbody tr')

    for row in rows:
        # Find Reece James by ID 238074
        if "238074" in str(row):
            print("\n🎯 Found Row for ID 238074! Attempting to parse...")
            
            try:
                # 1. NAME LOGIC
                name_link = row.select_one('a[href^="/player/"]')
                short_name = name_link.get_text(strip=True)
                full_name = name_link.get('data-tooltip')
                
                # Mimic your script's logic
                if not full_name:
                    full_name = clean_name_from_slug(name_link['href'])
                
                if "." in short_name:
                    final_name = full_name if full_name else short_name
                else:
                    final_name = short_name
                
                print(f"   Name: {final_name}")

                # 2. RATING LOGIC
                ovr_td = row.select_one('td[data-col="oa"]')
                pot_td = row.select_one('td[data-col="pt"]')
                current_ovr = int(ovr_td.get_text(strip=True))
                potential_ovr = int(pot_td.get_text(strip=True))
                
                print(f"   Rating: {current_ovr}")
                print(f"   Potential: {potential_ovr}")

                # 3. VALUE CALCULATION
                val, cat = calculate_value(current_ovr, potential_ovr)
                print(f"   Calculated: {val} ({cat})")

                print("\n✅ SUCCESS! Logic is perfect.")
                return

            except Exception as e:
                print(f"\n❌ FAILED to parse him: {e}")
                return

    print("⚠️ Could not find him on Page 3 (Did he move pages?)")

if __name__ == "__main__":
    test_reece_parsing()