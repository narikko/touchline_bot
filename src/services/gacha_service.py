import random
from datetime import datetime, timedelta
from sqlalchemy.sql.expression import func
from src.database.models import User, PlayerBase, Card

class GachaService:
    def __init__(self, session):
        self.session = session
        self.BOARD_MULTIPLIERS = [0, 0.05, 0.10, 0.15, 0.20, 0.25] 

        self.MAX_ROLLS = 10
        self.ROLL_RESET_MINUTES = 60
        
        self.MAX_CLAIMS = 1
        self.CLAIM_RESET_MINUTES = 180

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

        if user.rolls_remaining <= 0:
            reset_in = self.get_next_reset_time(user.last_roll_reset, self.ROLL_RESET_MINUTES)
            return {"success": False, "message": f"⏳ You are out of rolls! Reset in: **{reset_in}**"}

        # 1. Pick a Player
        rarity = self.determine_rarity()
        player = self.session.query(PlayerBase)\
            .filter_by(rarity=rarity)\
            .order_by(func.random())\
            .first()

        if not player:
            return {"success": False, "message": "Database error: No players found."}

        # 2. Pay the Roll Cost
        user.rolls_remaining -= 1
        
        # 3. CHECK DUPLICATE LOGIC (The fix)
        # Check if ANY user in this guild already owns this card
        existing_card = self.session.query(Card).join(User).filter(
            User.guild_id == guild_id,
            Card.player_base_id == player.id
        ).first()

        if existing_card:
            # It's a duplicate. Give coins instead.
            base_value = player.value
            
            # Apply Board Upgrade Multiplier
            # user.upgrade_board is 0-5. 
            multiplier = self.BOARD_MULTIPLIERS[min(user.upgrade_board, 5)]
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

        # 4. Not a duplicate - Ready to Claim
        self.session.commit()
        
        return {
            "success": True,
            "is_duplicate": False,
            "player": player,
            "rolls_remaining": user.rolls_remaining
        }

    def claim_card(self, discord_id, guild_id, player_id):
        user = self.get_or_create_user(discord_id, guild_id, "Unknown")
        
        # 1. CHECK CLAIMS
        if user.claims_remaining <= 0:
            reset_in = self.get_next_reset_time(user.last_claim_reset, self.CLAIM_RESET_MINUTES)
            return {"success": False, "message": f"❌ You have no claims left! Reset in: **{reset_in}**"}

        existing = self.session.query(Card).join(User).filter(
            User.guild_id == guild_id, 
            Card.player_base_id == player_id
        ).first()
        
        if existing:
            return {"success": False, "message": f"Too slow! Claimed by {existing.owner.username}"}

        new_card = Card(user_id=user.id, player_base_id=player_id)
        
        # 2. DEDUCT CLAIM
        user.claims_remaining -= 1
        
        self.session.add(new_card)
        self.session.commit()
        
        return {"success": True, "card": new_card}
    
    def get_user_collection(self, discord_id, guild_id, page=1, per_page=10):
        """
        Fetches a paginated list of cards owned by the user.
        """
        user = self.get_or_create_user(discord_id, guild_id, "Unknown")

        # Calculate offset
        offset = (page - 1) * per_page

        # Query total count for pagination
        total_cards = self.session.query(Card).filter_by(user_id=user.id).count()

        # Fetch the actual cards for this page, joining with PlayerBase to get names
        cards = self.session.query(Card)\
            .join(PlayerBase)\
            .filter(Card.user_id == user.id)\
            .order_by(Card.obtained_at.desc())\
            .offset(offset)\
            .limit(per_page)\
            .all()
        
        return {
            "cards": cards,
            "total": total_cards,
            "current_page": page,
            "max_page": (total_cards + per_page - 1) // per_page
        }