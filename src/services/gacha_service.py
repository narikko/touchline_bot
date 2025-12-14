import random
from sqlalchemy.sql.expression import func
from src.database.models import User, PlayerBase, Card

class GachaService:
    def __init__(self, session):
        self.session = session
        self.BOARD_MULTIPLIERS = [0, 0.05, 0.10, 0.15, 0.20, 0.25] 

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
        return user

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
            return {"success": False, "message": "You have no rolls remaining."}

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
        """
        Called when user reacts to the message
        """
        user = self.get_or_create_user(discord_id, guild_id, "Unknown")
        
        # Double check it wasn't claimed in the last 2 seconds by someone else
        existing = self.session.query(Card).join(User).filter(
            User.guild_id == guild_id, 
            Card.player_base_id == player_id
        ).first()
        
        if existing:
            return {"success": False, "message": f"Too slow! Claimed by {existing.owner.username}"}

        new_card = Card(
            user_id=user.id,
            player_base_id=player_id,
            is_main_xi=False
        )
        self.session.add(new_card)
        self.session.commit()
        
        return {"success": True, "card": new_card}