import random
from datetime import datetime, timedelta
from sqlalchemy.sql.expression import func
from src.database.models import User, PlayerBase, Card
from sqlalchemy import func, desc
import time
import unicodedata

def normalize_text(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn').lower()

class GachaService:
    def __init__(self, session):
        self.session = session
        self.BOARD_MULTIPLIERS = [0, 0.05, 0.10, 0.15, 0.20, 0.25]
        self.STADIUM_MULTIPLIERS = [0, 0.5, 1, 2, 3, 5] 

        self.MAX_ROLLS = 100
        self.ROLL_RESET_MINUTES = 0
        
        self.MAX_CLAIMS = 1
        self.CLAIM_RESET_MINUTES = 180

        self.DAILY_RESET_HOURS = 24

    def get_or_create_user(self, discord_id, guild_id, username):
        user = self.session.query(User).filter_by(discord_id=discord_id, guild_id=guild_id).first()
        if not user:
            user = User(
                discord_id=discord_id,
                guild_id=guild_id,
                username=username
            )
            self.session.add(user)
            self.session.commit()
        self.check_refills(user)
        return user
    
    def check_refills(self, user):
        """Checks if enough time has passed to reset rolls or claims."""
        now = datetime.utcnow()
        commit = False 

        # Refresh Rolls
        time_since_roll = (now - user.last_roll_reset).total_seconds() / 60
        if time_since_roll >= self.ROLL_RESET_MINUTES:
            user.rolls_remaining = self.MAX_ROLLS
            user.last_roll_reset = now
            commit = True

        # Refresh Claims
        time_since_claim = (now - user.last_claim_reset).total_seconds() / 60
        if time_since_claim >= self.CLAIM_RESET_MINUTES:
            user.claims_remaining = self.MAX_CLAIMS
            user.last_claim_reset = now
            commit = True
            
        if commit:
            self.session.commit()

    def get_next_reset_time(self, last_reset, minutes):
        """Helper to calculate when the next reset happens."""
        next_reset = last_reset + timedelta(minutes=minutes)
        diff = next_reset - datetime.utcnow()
        
        total_seconds = int(diff.total_seconds())
        if total_seconds <= 0: return "Now"
        
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def determine_rarity(self):
        # 1 in 2000 for Legend
        if random.randint(0, 2000) == 0:
            return "Legend"
        
        roll = random.randint(0, 100)
        if roll == 0: return "Ultra Rare"
        elif 1 <= roll < 3: return "Rare"
        else: return "Common"

    def roll_card(self, discord_id, guild_id, username):
        user = self.get_or_create_user(discord_id, guild_id, username)

        # 0. Check Rolls
        if user.rolls_remaining <= 0:
            reset_in = self.get_next_reset_time(user.last_roll_reset, self.ROLL_RESET_MINUTES)
            return {"success": False, "message": f"⏳ You are out of rolls! Reset in: **{reset_in}**"}

        # 1. Determine Rarity
        rarity = self.determine_rarity()
        
        # --- STADIUM UPGRADE LOGIC ---
        # "Increases chances of rolling a player from your Favorite Club (excluding Legends)."
        force_fav_club = False
        
        # Only apply if they have a favorite club AND it's not a Legend roll
        if user.favorite_club and rarity != "Legend":
            
            # Safely get level (cap at 5)
            level = min(getattr(user, "upgrade_stadium", 0), 5)
            
            if level > 0:
                chance = self.STADIUM_MULTIPLIERS[level]
                # Roll a 100-sided float die
                if random.uniform(0, 100) < chance:
                    force_fav_club = True

        # 2. Pick the Player
        query = self.session.query(PlayerBase).filter_by(rarity=rarity)
        player = None

        if force_fav_club:
            # Try to find a player from their club
            # We use ilike for case-insensitive matching
            fav_matches = query.filter(PlayerBase.club.ilike(f"%{user.favorite_club}%"))
            
            # Only proceed if such players actually exist (e.g. if they favor a club with no 'Ultra Rare' cards, fall back)
            if fav_matches.count() > 0:
                player = fav_matches.order_by(func.random()).first()

        # Fallback: Normal random roll if stadium failed OR no players found in club
        if not player:
            player = query.order_by(func.random()).first()

        if not player:
            return {"success": False, "message": "Database error: No players found."}

        # 3. Pay the Roll Cost
        if user.rolls_remaining >= self.MAX_ROLLS:
            user.last_roll_reset = datetime.utcnow()

        user.rolls_remaining -= 1
        
        # 4. Duplicate Check
        existing_card = self.session.query(Card).join(User).filter(
            User.guild_id == guild_id,
            Card.player_base_id == player.id
        ).first()

        if existing_card:
            # It's a duplicate. Give coins.
            base_value = player.value
            
            # --- BOARD UPGRADE LOGIC ---
            # "Boosts overall income... getting duplicates"
            board_level = min(getattr(user, "upgrade_board", 0), 5)
            # Bonuses: 0%, 5%, 10%, 15%, 20%, 25%
            multiplier = self.BOARD_MULTIPLIERS[board_level]
            
            coin_reward = int(base_value * (1 + multiplier))
            
            user.coins += coin_reward
            self.session.commit()
            
            return {
                "success": True,
                "is_duplicate": True,
                "player": player,
                "rolls_remaining": user.rolls_remaining,
                "coins_gained": coin_reward,
                "owner_name": existing_card.owner.username
            }

        # 5. Not a duplicate: Ready to Claim
        self.session.commit()
        
        return {
            "success": True,
            "is_duplicate": False,
            "player": player,
            "rolls_remaining": user.rolls_remaining
        }

    def claim_card(self, discord_id, guild_id, player_id):
        user = self.get_or_create_user(discord_id, guild_id, "Unknown")
        
        # Check claims
        if user.claims_remaining <= 0:
            reset_in = self.get_next_reset_time(user.last_claim_reset, self.CLAIM_RESET_MINUTES)
            return {"success": False, "message": f"❌ You have no claims left! Reset in: **{reset_in}**"}

        existing = self.session.query(Card).join(User).filter(
            User.guild_id == guild_id, 
            Card.player_base_id == player_id
        ).first()
        
        if existing:
            return {"success": False, "message": f"Too slow! Claimed by {existing.owner.username}"}
        
        current_time = int(time.time())
        new_card = Card(user_id=user.id, player_base_id=player_id, sort_priority=current_time)
        
        # Deduct claim
        if user.claims_remaining >= self.MAX_CLAIMS:
            user.last_claim_reset = datetime.utcnow()
            
        user.claims_remaining -= 1
        
        self.session.add(new_card)
        self.session.commit()
        
        return {"success": True, "card": new_card}
    
    def get_user_collection(self, discord_id, guild_id, page=1, per_page=10, target_user_id=None):
        """
        Fetches a paginated list of cards owned by the user.
        """
        lookup_id = target_user_id if target_user_id else discord_id
        user = self.get_or_create_user(lookup_id, guild_id, "Unknown")

        # Calculate offset
        offset = (page - 1) * per_page

        # Query total count for pagination
        total_cards = self.session.query(Card).filter_by(user_id=user.id).count()

        # Fetch the actual cards for this page, joining with PlayerBase to get names
        cards = self.session.query(Card)\
            .join(PlayerBase)\
            .filter(Card.user_id == user.id)\
            .order_by(Card.sort_priority.desc())\
            .offset(offset)\
            .limit(per_page)\
            .all()
        
        return {
            "cards": cards,
            "total": total_cards,
            "current_page": page,
            "max_page": (total_cards + per_page - 1) // per_page
        }
    
    def sell_player(self, discord_id, guild_id, player_name):
        """
        Finds a player by name, deletes it, and refunds coins with Board Multiplier.
        """
        user = self.get_or_create_user(discord_id, guild_id, "Unknown")
        card_to_sell = self.session.query(Card)\
            .join(PlayerBase)\
            .filter(Card.user_id == user.id)\
            .filter(PlayerBase.name.ilike(f"%{player_name}%"))\
            .first()
        
        if not card_to_sell:
            return {"success": False, "message": f"Could not find a player named '{player_name}' in your collection."}

        # 1. Calculate Base Refund
        base_value = card_to_sell.details.value
        player_name = card_to_sell.details.name
        
        # 2. Apply Board Upgrade Multiplier
        # Safely get the level (default 0) and cap it at 5 to prevent index errors
        board_level = min(getattr(user, "upgrade_board", 0), 5)
        
        # self.BOARD_MULTIPLIERS is like [0, 0.05, 0.10, ...]
        multiplier = self.BOARD_MULTIPLIERS[board_level]
        
        bonus_amount = int(base_value * multiplier)
        total_refund = base_value + bonus_amount

        # 3. Update User Balance
        user.coins += total_refund
        
        # 4. Delete Card
        self.session.delete(card_to_sell)
        self.session.commit()
        
        return {
            "success": True, 
            "player_name": player_name, 
            "coins": total_refund,      # Total given
            "base_value": base_value,   # Original value (for display)
            "bonus": bonus_amount,      # Extra from board (for display)
            "new_balance": user.coins
        }
    
    def sort_collection(self, discord_id, guild_id):
        user = self.get_or_create_user(discord_id, guild_id, "Unknown")
        
        # Fetch all cards
        cards = self.session.query(Card).join(PlayerBase).filter(Card.user_id == user.id).all()
        
        if not cards:
            return {"success": False, "message": "No cards to sort."}
            
        # Sort 
        cards.sort(key=lambda c: (c.details.value, c.details.name), reverse=True)
        
        current_time = int(time.time())
        
        for i, card in enumerate(cards):
            card.sort_priority = current_time - i
            
        self.session.commit()
        return {"success": True, "count": len(cards)}
    
    def move_player(self, discord_id, guild_id, player_name_query, target_page):
        """
        Moves a player to a specific page index.
        """
        user = self.get_or_create_user(discord_id, guild_id, "Unknown")

        cards = self.session.query(Card)\
            .join(PlayerBase)\
            .filter(Card.user_id == user.id)\
            .order_by(Card.sort_priority.desc())\
            .all()
            
        if not cards:
            return {"success": False, "message": "You have no cards."}
        
        if target_page < 1 or target_page > len(cards):
            return {"success": False, "message": f"Please choose a page number between 1 and {len(cards)}."}
        
        # Find the card
        card_to_move = None
        current_index = -1
        
        for i, card in enumerate(cards):
            if player_name_query.lower() in card.details.name.lower():
                card_to_move = card
                current_index = i
                break
        
        if not card_to_move:
            return {"success": False, "message": f"Player '{player_name_query}' not found."}

        # Remove from old position
        cards.pop(current_index)
        new_index = max(0, min(target_page - 1, len(cards)))
        
        # Insert at new position
        cards.insert(new_index, card_to_move)

        import time
        current_ts = int(time.time())
        
        for i, card in enumerate(cards):
            card.sort_priority = current_ts - i
            
        self.session.commit()
        
        return {
            "success": True, 
            "player": card_to_move.details.name, 
            "page": new_index + 1
        }
    
    def claim_daily(self, discord_id, guild_id, username):
        """
        Gives the user their daily coin reward with RNG and Board Multipliers.
        """
        user = self.get_or_create_user(discord_id, guild_id, username)
        now = datetime.utcnow()

        # Check Time Logic
        if user.last_daily_claim:
            time_since = (now - user.last_daily_claim).total_seconds() / 3600
            if time_since < self.DAILY_RESET_HOURS:
                next_reset = user.last_daily_claim + timedelta(hours=self.DAILY_RESET_HOURS)
                diff = next_reset - now
                hours, remainder = divmod(int(diff.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                return {"success": False, "message": f"Daily not ready! Wait **{hours}h {minutes}m**."}
            
        # Calculate Base Reward
        chance = random.randint(0, 100)

        if chance < 7:
            base_reward = random.randint(700, 900)
            bonus_type = "🌟 **Lucky Day!** Big Prize!"
        else:
            base_reward = random.randint(300, 550)
            bonus_type = "✅ Daily Reward"
        
        # Board Multiplier
        board_level = min(user.upgrade_board, 5)
        multiplier_percent = self.BOARD_MULTIPLIERS[board_level]

        bonus_amount = int(base_reward * multiplier_percent)
        total_reward = base_reward + bonus_amount

        # Save to DB
        user.coins += total_reward
        user.last_daily_claim = now
        self.session.commit()

        return {
            "success": True, 
            "total_reward": total_reward,
            "base_reward": base_reward,
            "bonus_amount": bonus_amount,
            "bonus_type": bonus_type,
            "multiplier_percent": int(multiplier_percent * 100),
            "new_balance": user.coins
        }
    
    def set_favorite_club(self, discord_id, guild_id, club_input):
        """
        Sets the user's favorite club with validation.
        """
        user = self.get_or_create_user(discord_id, guild_id, "Unknown")

        # Search for club in DB
        search_term = f"%{club_input}%"
        matches = self.session.query(PlayerBase.club)\
            .filter(PlayerBase.club.ilike(search_term))\
            .distinct()\
            .limit(15)\
            .all()
        
        found_clubs = [m[0] for m in matches if m[0] != "N/A"]

        # Exact Match
        exact_match = next((c for c in found_clubs if c.lower() == club_input.lower()), None)
        
        if exact_match:
            target_club = exact_match
        elif len(found_clubs) == 1:
            target_club = found_clubs[0]
        else:
            target_club = None

        if target_club:
            user.favorite_club = target_club
            self.session.commit()
            return {"success": True, "club": target_club}
            
        # Multiple Matches Found
        if len(found_clubs) > 1:
            return {"success": False, "reason": "multiple", "matches": found_clubs}
            
        # No Matches
        return {"success": False, "reason": "none", "matches": []}
    
    def view_player(self, discord_id, guild_id, player_name):
        """
        Finds a player and checks if anyone in the guild owns it.
        """
        player_name = normalize_text(player_name)
        # 1. Fuzzy Search
        search_term = f"%{player_name}%"
        matches = self.session.query(PlayerBase)\
            .filter(PlayerBase.name.ilike(search_term))\
            .limit(15)\
            .all()
            
        if not matches:
            return {"success": False, "reason": "none"}
            
        # 2. Exact Match Logic
        exact = next((p for p in matches if p.name.lower() == player_name.lower()), None)
        target_player = exact if exact else (matches[0] if len(matches) == 1 else None)

        if not target_player:
            return {"success": False, "reason": "multiple", "matches": [p.name for p in matches]}

        # 3. OWNERSHIP CHECK (The new logic)
        # Check if a card exists for this player in this guild
        card = self.session.query(Card).join(User).filter(
            User.guild_id == guild_id,
            Card.player_base_id == target_player.id
        ).first()

        owner_name = card.owner.username if card else None

        return {
            "success": True, 
            "player": target_player, 
            "owner": owner_name  # <--- Return the owner's name (or None)
        }
    
    def get_club_checklist(self, discord_id, guild_id, club_query):
        """
        Returns ALL players in a club and flags which ones the user owns.
        Handles multi-club strings (e.g., 'Ajax/FC Barcelona').
        """
        user = self.get_or_create_user(discord_id, guild_id, "Unknown")
        
        # 1. Broad Search: Find any club string containing the query
        # We assume the query is close to the real name.
        club_match_rows = self.session.query(PlayerBase.club)\
            .filter(PlayerBase.club.ilike(f"%{club_query}%"))\
            .distinct()\
            .all()
            
        if not club_match_rows:
            return {"success": False, "message": "Club not found."}
        
        # 2. Parse and Split Multi-Club Strings
        # We extract individual teams (e.g., "Ajax/FC Barcelona" -> "Ajax", "FC Barcelona")
        found_clubs = set()
        
        for row in club_match_rows:
            raw_club_str = row[0]
            # Split by '/' and strip whitespace
            individual_teams = [t.strip() for t in raw_club_str.split('/')]
            
            # Only add teams that match the user's query
            for team in individual_teams:
                if club_query.lower() in team.lower():
                    found_clubs.add(team)
        
        sorted_clubs = sorted(list(found_clubs))
        
        if not sorted_clubs:
             return {"success": False, "message": "Club not found."}

        # 3. Determine Target Club (Exact Match Priority)
        target_club = None
        exact = next((c for c in sorted_clubs if c.lower() == club_query.lower()), None)
        
        if exact:
            target_club = exact
        elif len(sorted_clubs) == 1:
            target_club = sorted_clubs[0]
        else:
            # If we still have multiple distinct CLUBS (e.g. "FC Barcelona" and "Barcelona SC")
            return {"success": False, "reason": "multiple", "matches": sorted_clubs}

        # 4. Fetch Players (Robust Filtering)
        # First, get all players who have the target club string anywhere in their club column
        candidates = self.session.query(PlayerBase)\
            .filter(PlayerBase.club.ilike(f"%{target_club}%"))\
            .all()

        # 5. Filter in Python to ensure they belong to the specific target club
        # This correctly handles "Ajax/FC Barcelona" when we want "FC Barcelona"
        all_players = []
        for p in candidates:
            # Split player's club string into parts
            p_teams = [t.strip().lower() for t in p.club.split('/')]
            
            # Check if our target club is in that list
            if target_club.lower() in p_teams:
                all_players.append(p)

        # Sort by rating manually since we are in Python now
        all_players.sort(key=lambda x: x.rating, reverse=True)

        # 6. Check Ownership (Standard Logic)
        owned_rows = self.session.query(Card.player_base_id)\
            .filter(Card.user_id == user.id)\
            .all()
        
        owned_ids = {row[0] for row in owned_rows}
        
        checklist = []
        owned_count = 0
        
        for p in all_players:
            is_owned = p.id in owned_ids
            if is_owned:
                owned_count += 1
            
            checklist.append({
                "name": p.name,
                "rating": p.rating,
                "rarity": p.rarity,
                "owned": is_owned 
            })
            
        return {
            "success": True,
            "club_name": target_club,
            "checklist": checklist,
            "owned_count": owned_count,
            "total_count": len(all_players)
        }
    
    def use_free_claim(self, discord_id, guild_id):
        # This will auto-run check_refills first. 
        # If the natural timer just finished, their claims will refill to MAX here.
        user = self.get_or_create_user(discord_id, guild_id, "Unknown")

        # 1. Validation: Don't let them waste a ticket if they can already claim
        if user.claims_remaining > 0:
            return {
                "success": False, 
                "message": f"Your claim is already ready ({user.claims_remaining} left)! No need to use a Free Claim."
            }

        # 2. Validation: Do they have tickets?
        if user.free_claims <= 0:
            return {
                "success": False, 
                "message": "You don't have any Free Claim tickets! Earn them through rewards."
            }

        # 3. Apply the Free Claim
        user.free_claims -= 1
        user.claims_remaining += 1
        
        # Note: We do NOT touch last_claim_reset. 
        # This allows their natural timer to keep ticking in the background 
        # towards the next natural refill, which is player-friendly.
        
        self.session.commit()

        return {
            "success": True,
            "claims_remaining": user.claims_remaining,
            "free_claims_left": user.free_claims
        }
            
        
