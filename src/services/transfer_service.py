from datetime import datetime, timedelta
from src.database.models import User, Card, PlayerBase, MarketListing
from sqlalchemy import func

class TransferService:
    def __init__(self, session):
        self.session = session
        
        # Duration in HOURS based on Transfer Upgrade Level (0-5)
        # Default (0) = 72h, 1=48h, 2=24h, 3=12h, 4=6h, 5=3h
        self.DURATION_HOURS = [36, 24, 18, 12, 6, 3]

    def _get_user(self, discord_id, guild_id):
        return self.session.query(User).filter_by(discord_id=discord_id, guild_id=guild_id).first()

    def add_to_market(self, discord_id, guild_id, player_name):
        user = self._get_user(discord_id, guild_id)
        if not user: return {"success": False, "message": "User not found."}

        # 1. Check if user already has a listing active
        # We query the MarketListing table
        existing = self.session.query(MarketListing).filter_by(user_id=user.id).first()
        if existing:
            return {"success": False, "message": "You already have a player on the Transfer List! Wait for it to sell or remove it."}

        # 2. Find the card
        card = self.session.query(Card).join(PlayerBase)\
            .filter(Card.user_id == user.id)\
            .filter(PlayerBase.name.ilike(f"%{player_name}%"))\
            .first()

        if not card:
            return {"success": False, "message": f"Card **{player_name}** not found in your collection."}
        
        if card.position_in_xi:
            return {"success": False, "message": f"**{card.details.name}** is in your team! Remove them from the lineup first."}

        # 3. Calculate Value & Time
        # Value = Base * 1.5 * Board_Multiplier
        base_val = card.details.value
        
        board_level = min(getattr(user, "upgrade_board", 0), 5)
        board_multipliers = [0, 0.05, 0.10, 0.15, 0.20, 0.25]
        board_bonus = board_multipliers[board_level]
        
        sell_value = int((base_val * 2) * (1 + board_bonus))

        # Time
        transfer_level = min(getattr(user, "upgrade_transfer", 0), 5)
        hours_wait = self.DURATION_HOURS[transfer_level]
        available_at = datetime.utcnow() + timedelta(hours=hours_wait)

        # 4. Create MarketListing Record
        new_listing = MarketListing(
            user_id=user.id,
            card_id=card.id,
            available_at=available_at,  # Using your model's column name
            listed_price=sell_value,    # Using your model's column name
            listed_at=datetime.utcnow()
        )
        self.session.add(new_listing)
        self.session.commit()

        return {
            "success": True,
            "player": card.details.name,
            "value": sell_value,
            "hours": hours_wait
        }

    def remove_from_market(self, discord_id, guild_id):
        user = self._get_user(discord_id, guild_id)
        listing = self.session.query(MarketListing).filter_by(user_id=user.id).first()

        if not listing:
            return {"success": False, "message": "You don't have any players on the Transfer List."}

        # Delete the listing. The card remains owned by the user.
        self.session.delete(listing)
        self.session.commit()
        return {"success": True, "message": "Player removed from Transfer List."}

    def check_transfer_status(self, discord_id, guild_id):
        """Checks if the transfer is done. If so, sells it."""
        user = self._get_user(discord_id, guild_id)
        listing = self.session.query(MarketListing).filter_by(user_id=user.id).first()

        if not listing:
            return {"status": "empty"}

        now = datetime.utcnow()
        # Join to get player name just for display
        card = self.session.query(Card).join(PlayerBase).filter(Card.id == listing.card_id).first()
        player_name = card.details.name if card else "Unknown Player"

        # CASE 1: Transfer Finished (Time passed)
        if now >= listing.available_at:
            sale_value = listing.listed_price
            
            # Transaction
            user.coins += sale_value
            
            # Delete both the Listing AND the Card (since it was sold)
            self.session.delete(card) 
            self.session.delete(listing) 
            self.session.commit()
            
            return {
                "status": "completed", 
                "player": player_name, 
                "value": sale_value
            }

        # CASE 2: Still Waiting
        diff = listing.available_at - now
        hours, remainder = divmod(int(diff.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)

        return {
            "status": "waiting",
            "player": player_name,
            "value": listing.listed_price,
            "time_left": f"{hours}h {minutes}m"
        }