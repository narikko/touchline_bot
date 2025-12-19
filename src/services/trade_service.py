from sqlalchemy.orm import joinedload
from src.database.models import User, Card, PlayerBase, MarketListing

class TradeService:
    def __init__(self, session):
        self.session = session

    def get_or_create_user(self, discord_id, guild_id, username):
        # We duplicate this helper or import it if you have a shared util
        user = self.session.query(User).filter_by(discord_id=str(discord_id), guild_id=str(guild_id)).first()
        if not user:
            user = User(discord_id=str(discord_id), guild_id=str(guild_id), username=username)
            self.session.add(user)
            self.session.commit()
        return user

    def find_card_for_trade(self, discord_id, guild_id, player_name):
        """
        Finds a card owned by the user that is VALID for trading.
        Checks: Exists, Not in Lineup, Not in Transfer Market.
        """
        user = self.get_or_create_user(discord_id, guild_id, "Unknown")
        
        # Eager load 'details' so we can access card.details.name after session closes
        card = self.session.query(Card).join(PlayerBase)\
            .options(joinedload(Card.details))\
            .outerjoin(MarketListing, Card.id == MarketListing.card_id)\
            .filter(Card.user_id == user.id)\
            .filter(PlayerBase.name.ilike(f"%{player_name}%"))\
            .filter(MarketListing.id == None)\
            .first()
            
        if not card:
            return None
        
        if card.position_in_xi:
            return None # Cannot trade active players
            
        return card

    def execute_trade(self, card_a_id, card_b_id):
        """
        Swaps ownership of two cards safely.
        """
        # Re-fetch strictly by ID to ensure atomicity
        card_a = self.session.query(Card).filter_by(id=card_a_id).first()
        card_b = self.session.query(Card).filter_by(id=card_b_id).first()

        if not card_a or not card_b:
            return {"success": False, "message": "Trade failed: One of the cards no longer exists."}

        # Double check they didn't equip them while waiting
        if card_a.position_in_xi or card_b.position_in_xi:
             return {"success": False, "message": "Trade failed: One of the players is currently in a Starting XI."}

        # SWAP OWNERS
        owner_a_id = card_a.user_id
        owner_b_id = card_b.user_id
        
        card_a.user_id = owner_b_id
        card_b.user_id = owner_a_id
        
        # Clear positions (redundant safety)
        card_a.position_in_xi = None
        card_b.position_in_xi = None

        self.session.commit()
        
        return {
            "success": True, 
            "message": f"Trade Complete! **{card_a.details.name}** ↔ **{card_b.details.name}**"
        }