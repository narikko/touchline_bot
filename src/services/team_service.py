import unicodedata
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database.models import User, Card, PlayerBase

# Helper function at the top, just like in gacha_service.py
def normalize_text(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn').lower()

class TeamService:
    def __init__(self, session):
        self.session = session
        self.TRAINING_MULTIPLIERS = [0.03, 0.05, 0.07, 0.1, 0.15]

        # Valid slots for the command
        self.VALID_SLOTS = {
            "GK": "Goalkeeper",
            "D1": "Defender 1", "D2": "Defender 2", "D3": "Defender 3", "D4": "Defender 4",
            "M1": "Midfielder 1", "M2": "Midfielder 2", "M3": "Midfielder 3",
            "F1": "Forward 1", "F2": "Forward 2", "F3": "Forward 3"
        }

        # Which real-life positions are allowed in which slot
        self.POSITION_COMPATIBILITY = {
            "GK": ["GK"],
            "D":  ["CB", "LB", "RB", "LWB", "RWB"],
            "M":  ["CM", "CDM", "CAM", "LM", "RM"],
            "F":  ["ST", "CF", "LW", "RW"]
        }

        self.MILESTONES = [
            {"desc": "Build a full team of 11 players", "reward_text": "1000 💠"},
            {"desc": "Starting XI value of 300", "reward_text": "2 free claims"},
            {"desc": "Starting XI value of 400", "reward_text": "2000 💠"},
            {"desc": "Starting XI value of 500", "reward_text": "+2 rolls/hour"},
            {"desc": "Starting XI value of 600", "reward_text": "+3 rolls/hour"},
            {"desc": "Starting XI value of 700", "reward_text": "Random 830+ card"},
            {"desc": "Starting XI value of 800", "reward_text": "Random Legend card"},
        ]

    def get_starting_xi(self, discord_id, guild_id):
        user = self.session.query(User).filter_by(discord_id=str(discord_id), guild_id=str(guild_id)).first()
        if not user:
            return {"success": False, "message": "User not found."}

        # Fetch cards in the starting XI
        lineup_cards = self.session.query(Card).join(PlayerBase)\
            .filter(Card.user_id == user.id, Card.position_in_xi.isnot(None))\
            .all()

        # Map Position -> Player Details
        lineup_dict = {card.position_in_xi: card.details for card in lineup_cards}
        
        return {
            "success": True, 
            "club_name": user.club_name if user.club_name else "Default FC",
            "lineup": lineup_dict
        }

    def set_lineup_player(self, discord_id, guild_id, slot_code, player_name_query):
        slot_code = slot_code.upper()
        
        # 1. Validate Slot
        if slot_code not in self.VALID_SLOTS:
            return {"success": False, "message": f"Invalid slot `{slot_code}`. Use GK, D1-D4, M1-M3, F1-F3."}

        user = self.session.query(User).filter_by(discord_id=str(discord_id), guild_id=str(guild_id)).first()
        if not user: 
            return {"success": False, "message": "Register first!"}

        # 2. Find the card using Python filtering (Safe for SQLite & Accents)
        # Fetch all user cards first
        user_cards = self.session.query(Card).join(PlayerBase).filter(Card.user_id == user.id).all()
        
        target_card = None
        query_norm = normalize_text(player_name_query)

        # Check for matches
        matches = []
        for card in user_cards:
            if query_norm in normalize_text(card.details.name):
                matches.append(card)
        
        if not matches:
            return {"success": False, "message": f"You don't own a player named `{player_name_query}`."}

        # Pick exact match if available, otherwise first result
        target_card = next((c for c in matches if normalize_text(c.details.name) == query_norm), matches[0])

        # 3. Position Compatibility Check
        player_pos_str = target_card.details.positions  # e.g. "CM, CAM"
        player_pos_list = [p.strip() for p in player_pos_str.split("/")]

        # Determine required role based on slot (GK, D, M, F)
        required_role = "GK" if slot_code == "GK" else slot_code[0]
        allowed_list = self.POSITION_COMPATIBILITY.get(required_role, [])

        # Check if ANY of the player's positions are in the allowed list
        is_valid_pos = any(pos in allowed_list for pos in player_pos_list)

        if not is_valid_pos:
            return {
                "success": False,
                "message": f"❌ **{target_card.details.name}** ({player_pos_str}) cannot play in **{slot_code}**.\nAllowed: {', '.join(allowed_list)}"
            }

        # 4. Check if already in this exact slot
        if target_card.position_in_xi == slot_code:
             return {"success": False, "message": f"**{target_card.details.name}** is already in {slot_code}."}

        # 5. Swap Logic: If someone is already in that slot, remove them
        existing_card = self.session.query(Card).filter_by(user_id=user.id, position_in_xi=slot_code).first()
        swapped_msg = ""
        if existing_card:
            existing_card.position_in_xi = None
            swapped_msg = f" (Swapped out {existing_card.details.name})"

        # 6. If the NEW player was elsewhere in the XI, remove them from old spot
        if target_card.position_in_xi:
            target_card.position_in_xi = None

        # 7. Assign new position
        target_card.position_in_xi = slot_code
        self.session.commit()

        reward_msg = self.process_milestone_check(user)
    
        final_msg = f"**{target_card.details.name}** set to **{slot_code}**{swapped_msg}!"
        
        # 3. If they unlocked something, append the congratulatory message
        if reward_msg:
            final_msg += f"\n\n🎉 **NEW MILESTONE UNLOCKED!**\n{reward_msg}"

        return {"success": True, "message": final_msg}

    def remove_from_lineup(self, discord_id, guild_id, player_name_query):
        user = self.session.query(User).filter_by(discord_id=str(discord_id), guild_id=str(guild_id)).first()
        
        # Search specifically among cards IN THE XI
        xi_cards = self.session.query(Card).join(PlayerBase)\
            .filter(Card.user_id == user.id, Card.position_in_xi.isnot(None))\
            .all()

        query_norm = normalize_text(player_name_query)
        target_card = next((c for c in xi_cards if query_norm in normalize_text(c.details.name)), None)

        if not target_card:
            return {"success": False, "message": f"Could not find `{player_name_query}` in your starting XI."}

        old_pos = target_card.position_in_xi
        target_card.position_in_xi = None
        self.session.commit()

        return {"success": True, "message": f"**{target_card.details.name}** removed from **{old_pos}**."}

    def rename_club(self, discord_id, guild_id, new_name):
        user = self.session.query(User).filter_by(discord_id=str(discord_id), guild_id=str(guild_id)).first()
        if not user: return {"success": False, "message": "Register first!"}
        
        user.club_name = new_name if new_name else "Default FC"
        self.session.commit()
        return {"success": True, "message": f"Club renamed to **{user.club_name}**."}
    
    def get_team_stats_and_rewards(self, discord_id, guild_id):
        user = self.session.query(User).filter_by(discord_id=str(discord_id), guild_id=str(guild_id)).first()
        if not user: return {"success": False, "message": "User not found"}
        
        # 1. Calculate Base Stats
        lineup_cards = self.session.query(Card).join(PlayerBase).filter(
            Card.user_id == user.id, 
            Card.position_in_xi.isnot(None)
        ).all()
        
        player_count = len(lineup_cards)
        base_ovl = int(sum(card.details.rating for card in lineup_cards) / player_count)
        
        # 2. Apply Training Facility Upgrade
        # "Boosts the overall value rating of your Starting XI."
        training_level = min(getattr(user, "upgrade_training", 0), 5)
        
        # --- FIX: Handle Level 0 and Percentages ---
        if training_level == 0:
            multiplier = 0
        else:
            # Level 1 is at index 0. Values are percents (3 = 0.03)
            multiplier = self.TRAINING_MULTIPLIERS[training_level - 1]
        
        # Calculate Final Boosted OVL
        ovl_value = int(base_ovl * (1 + multiplier))
        
        # Prepare Display
        flags = user.team_rewards_flags if user.team_rewards_flags else [False] * 7
        rewards_display = []
        
        for i, m in enumerate(self.MILESTONES):
            rewards_display.append({
                "desc": m["desc"],
                "reward": m["reward_text"],
                "claimed": flags[i] if i < len(flags) else False
            })

        return {
            "ovl_value": ovl_value,      # Now returns the boosted value
            "base_ovl": base_ovl,        # Optional: if you want to show "(Base: 400 + 20 Boost)"
            "training_bonus": int(base_ovl * multiplier),
            "player_count": player_count,
            "rewards": rewards_display
        }

    def process_milestone_check(self, user):
        """Checks milestones, grants rewards, and returns a message if unlocked."""
        # 1. Calculate Base Stats
        lineup_cards = self.session.query(Card).join(PlayerBase).filter(
            Card.user_id == user.id, 
            Card.position_in_xi.isnot(None)
        ).all()

        player_count = len(lineup_cards)
        base_ovl = int(sum(card.details.rating for card in lineup_cards) / player_count)
        
        # 2. Apply Training Facility Upgrade
        training_level = min(getattr(user, "upgrade_training", 0), 5)
        
        if training_level == 0:
            multiplier = 0
        else:
            # Level 1 is at index 0. Values are percents (3 = 0.03)
            multiplier = self.TRAINING_MULTIPLIERS[training_level - 1]
        
        # Final OVL Value used for checks
        ovl_value = int(base_ovl * (1 + multiplier))

        print(ovl_value)

        # --- Initialize Flags ---
        if not user.team_rewards_flags:
            user.team_rewards_flags = [False] * 7
        
        flags = list(user.team_rewards_flags) # Copy
        unlocked_msgs = []

        # Helper to grant card
        def grant_random_card(min_rating=0, rarity=None):
            query = self.session.query(PlayerBase)
            if rarity:
                query = query.filter(PlayerBase.rarity == rarity)
            if min_rating > 0:
                query = query.filter(PlayerBase.rating >= min_rating)
            
            player = query.order_by(func.random()).first()
            if player:
                new_card = Card(user_id=user.id, player_base_id=player.id)
                self.session.add(new_card)
                return player.name
            return "Unknown Player"

        # --- Check Milestones (Using boosted ovl_value) ---
        
        # 0: Full Team
        if player_count >= 11:
            if not flags[0]:
                flags[0] = True
                user.coins += 1000
                unlocked_msgs.append("• Full Team: **+1000 💠**")

            # 1: 300 OVL
            if ovl_value >= 300 and not flags[1]:
                flags[1] = True
                user.free_claims += 2
                unlocked_msgs.append("• 300 OVL: **+2 Free Claims**")

            # 2: 400 OVL
            if ovl_value >= 400 and not flags[2]:
                flags[2] = True
                user.coins += 2000
                unlocked_msgs.append("• 400 OVL: **+2000 💠**")

            # 3: 500 OVL
            if ovl_value >= 500 and not flags[3]:
                flags[3] = True
                user.max_rolls += 2
                unlocked_msgs.append("• 500 OVL: **+2 Rolls/Hour Boost Active!**")

            # 4: 600 OVL
            if ovl_value >= 600 and not flags[4]:
                flags[4] = True
                user.max_rolls += 3
                unlocked_msgs.append("• 600 OVL: **+3 Rolls/Hour Boost Active!**")

            # 5: 700 OVL
            if ovl_value >= 700 and not flags[5]:
                flags[5] = True
                p_name = grant_random_card(rarity="Ultra Rare")
                unlocked_msgs.append(f"• 700 OVL: **Unlocked {p_name}!**")

            # 6: 800 OVL
            if ovl_value >= 800 and not flags[6]:
                flags[6] = True
                p_name = grant_random_card(rarity="Legend")
                unlocked_msgs.append(f"• 800 OVL: **Unlocked Legend {p_name}!**")

        # Save if changes happened
        if unlocked_msgs:
            user.team_rewards_flags = flags
            self.session.commit()
            return "\n".join(unlocked_msgs)
        
        return None